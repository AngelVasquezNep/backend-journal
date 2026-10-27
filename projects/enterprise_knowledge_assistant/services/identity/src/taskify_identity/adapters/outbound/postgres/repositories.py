"""Identity persistence uses owned definer lookups and short credential-fenced transactions."""

from dataclasses import asdict
from datetime import datetime
from types import TracebackType
from typing import Self
from uuid import UUID

from sqlalchemy import Engine, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from taskify_identity.adapters.outbound.postgres.models import (
    AccountRow,
    LoginWindowRow,
    SessionRow,
)
from taskify_identity.domain.account import Account
from taskify_identity.domain.company import Company
from taskify_identity.domain.errors import ApplicationError
from taskify_identity.domain.login_attempt import LoginAttemptWindow
from taskify_identity.domain.session import LoginSession


def account_value(row: AccountRow) -> Account:
    """Map storage fields to a revalidated core account; never send this value directly to HTTP."""
    return Account(**{key: getattr(row, key) for key in Account.__dataclass_fields__})


def session_value(row: SessionRow) -> LoginSession:
    """Map owned login data; token/CSRF material stays inside the authentication application."""
    return LoginSession(**{key: getattr(row, key) for key in LoginSession.__dataclass_fields__})


class SqlIdentityTransaction:
    """Own one short transaction; no locks survive password/provider work outside this context."""

    def __init__(self, engine: Engine) -> None:
        """Create an unopened session; entry begins actual database access."""
        self.database = Session(engine, expire_on_commit=False)

    def __enter__(self) -> Self:
        """Install UTC session time; tenant context follows owned account/operator resolution."""
        self.database.execute(text("SET LOCAL TIME ZONE 'UTC'"))
        self.database.execute(text("SET LOCAL lock_timeout = '3s'"))
        self.database.execute(text("SET LOCAL statement_timeout = '5s'"))
        return self

    def __exit__(
        self,
        kind: type[BaseException] | None,
        error: BaseException | None,
        trace: TracebackType | None,
    ) -> None:
        """Rollback uncommitted work and release all locks even after an application exception."""
        self.database.rollback()
        self.database.close()

    def commit(self) -> None:
        """Flush and atomically commit; map uniqueness failures without disclosing another company."""
        try:
            self.database.commit()
        except IntegrityError:
            self.database.rollback()
            raise ApplicationError(
                "account_unavailable", "This account cannot be created with those details.", 409
            ) from None

    def scope(self, company_id: UUID) -> None:
        """Set company context locally from authoritative Identity-owned data or operator input."""
        self.database.execute(
            text("SELECT set_config('taskify.company_id', :company, true)"),
            {"company": str(company_id)},
        )

    def create_company(self, company: Company) -> None:
        """Create the company through a narrow function in the first-admin transaction."""
        self.database.execute(
            text("SELECT taskify_create_company(:id, :name, :created)"),
            {"id": company.id, "name": company.name, "created": company.created_at},
        )

    def company_exists(self, company_id: UUID) -> bool:
        """Check only existence for operator provisioning; no foreign-company metadata leaves CLI."""
        return bool(
            self.database.execute(
                text("SELECT taskify_company_exists(:id)"), {"id": company_id}
            ).scalar()
        )

    def account_by_email(self, normalized_email: str) -> Account | None:
        """Lookup and lock globally unique email using the authentication-only function."""
        row = self.database.scalars(
            select(AccountRow)
            .from_statement(text("SELECT * FROM taskify_account_by_email(:email)"))
            .execution_options(populate_existing=True),
            {"email": normalized_email},
        ).first()
        return account_value(row) if row else None

    def account(self, account_id: UUID) -> Account | None:
        """Lock the current account version before credential checks or session insertion."""
        row = self.database.scalars(
            select(AccountRow)
            .from_statement(text("SELECT * FROM taskify_account_by_id(:id)"))
            .execution_options(populate_existing=True),
            {"id": account_id},
        ).first()
        return account_value(row) if row else None

    def save_account(self, account: Account) -> None:
        """Stage a canonical account under trusted company context; database uniqueness stays atomic."""
        self.database.merge(AccountRow(**asdict(account)))

    def session(
        self, *, digest: str | None = None, session_id: UUID | None = None
    ) -> LoginSession | None:
        """Resolve exactly one unguessable token digest or authenticated internal session reference."""
        if (digest is None) == (session_id is None):
            raise ValueError("Exactly one session selector is required.")
        row = self.database.scalars(
            select(SessionRow)
            .from_statement(text("SELECT * FROM taskify_session(:digest, :id)"))
            .execution_options(populate_existing=True),
            {"digest": digest, "id": session_id},
        ).first()
        return session_value(row) if row else None

    def save_session(self, session: LoginSession) -> None:
        """Stage only a digest/version/CSRF material under its resolved account's company."""
        self.database.merge(SessionRow(**asdict(session)))

    def revoke_sessions(self, account_id: UUID, now: datetime) -> None:
        """Revoke every prior account login in the fenced password-change transaction."""
        self.database.execute(
            text("SELECT taskify_revoke_sessions(:account, :now)"),
            {"account": account_id, "now": now},
        )

    def lock_login(self, email_key: str) -> None:
        """Take a short HMAC-keyed advisory lock, including for an email with no account/window."""
        self.database.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": email_key}
        )

    def login_window(self, email_key: str) -> LoginAttemptWindow | None:
        """Read failure accounting after acquiring the logical email lock."""
        row = self.database.get(LoginWindowRow, email_key)
        return (
            LoginAttemptWindow(
                **{key: getattr(row, key) for key in LoginAttemptWindow.__dataclass_fields__}
            )
            if row
            else None
        )

    def save_window(self, window: LoginAttemptWindow) -> None:
        """Stage a failure window without persisting or logging a plaintext email."""
        self.database.merge(LoginWindowRow(**asdict(window)))


class SqlIdentityStore:
    """Identity-owned transaction factory; no provider or cross-service database dependency."""

    def __init__(self, engine: Engine) -> None:
        """Retain the resetting runtime-role pool; construction performs no query."""
        self.engine = engine

    def transaction(self) -> SqlIdentityTransaction:
        """Return an independent short transaction for one application use case."""
        return SqlIdentityTransaction(self.engine)
