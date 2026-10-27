"""Identity-owned repository operations keep SQL and ORM sessions outside application use cases."""

from datetime import datetime
from types import TracebackType
from typing import Protocol, Self
from uuid import UUID

from taskify_identity.domain.account import Account
from taskify_identity.domain.company import Company
from taskify_identity.domain.login_attempt import LoginAttemptWindow
from taskify_identity.domain.session import LoginSession


class IdentityTransaction(Protocol):
    """One atomic provisioning/authentication transaction with narrow owned global lookups."""

    def __enter__(self) -> Self:
        """Begin a short transaction; global queries are restricted to owned auth functions."""
        ...

    def __exit__(
        self,
        kind: type[BaseException] | None,
        error: BaseException | None,
        trace: TracebackType | None,
    ) -> None:
        """Rollback every uncommitted change and release database resources."""
        ...

    def commit(self) -> None:
        """Atomically persist all changes or raise a safe storage/domain conflict."""
        ...

    def create_company(self, company: Company) -> None:
        """Create a validated company inside the same transaction as its first admin."""
        ...

    def company_exists(self, company_id: UUID) -> bool:
        """Check a CLI-selected company without exposing its metadata publicly."""
        ...

    def scope(self, company_id: UUID) -> None:
        """Install company authority obtained only from owned data or operator provisioning."""
        ...

    def save_account(self, account: Account) -> None:
        """Insert or update a canonical account; immutable ownership and email uniqueness apply."""
        ...

    def account(self, account_id: UUID) -> Account | None:
        """Lock and return an account for current credential-version fencing."""
        ...

    def account_by_email(self, normalized_email: str) -> Account | None:
        """Lock and return the unique account through narrow Identity-owned global lookup."""
        ...

    def session(
        self, *, digest: str | None = None, session_id: UUID | None = None
    ) -> LoginSession | None:
        """Resolve exactly one session selector; account authority must still be validated."""
        ...

    def save_session(self, session: LoginSession) -> None:
        """Insert/update a validated session under its account's trusted company context."""
        ...

    def revoke_sessions(self, account_id: UUID, now: datetime) -> None:
        """Revoke all previous account sessions in the password-change transaction."""
        ...

    def lock_login(self, email_key: str) -> None:
        """Serialize known/unknown-email failure accounting for the current short transaction."""
        ...

    def login_window(self, email_key: str) -> LoginAttemptWindow | None:
        """Return only the HMAC-keyed failure window, with no plaintext email record."""
        ...

    def save_window(self, window: LoginAttemptWindow) -> None:
        """Persist one atomic failure-accounting update under the login lock."""
        ...


class IdentityStore(Protocol):
    """Construct service-owned short transactions without handing core code a database session."""

    def transaction(self) -> IdentityTransaction:
        """Return a new transaction; no connection or authority crosses service boundaries."""
        ...
