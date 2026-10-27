"""First-party authentication policy depends only on Identity-owned values and ports."""

import hmac
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal
from uuid import UUID

from taskify_identity.application.ports.clock import Clock, IdGenerator
from taskify_identity.application.ports.identity_store import IdentityStore, IdentityTransaction
from taskify_identity.application.ports.security import PasswordHasher, TokenIssuer
from taskify_identity.domain.account import Account
from taskify_identity.domain.errors import ApplicationError, AuthenticationRequired
from taskify_identity.domain.login_attempt import LoginAttemptWindow
from taskify_identity.domain.session import LoginSession
from taskify_identity.domain.values import Email, Password


class LoginPaused(ApplicationError):
    """A generic known/unknown-email pause includes only a safe Retry-After duration."""

    def __init__(self, seconds: int) -> None:
        """Report the remaining login pause without an account-existence distinction."""
        super().__init__(
            "login_temporarily_unavailable",
            "Login is temporarily unavailable. Please try again later.",
            429,
        )
        self.retry_after = seconds


@dataclass(frozen=True)
class SessionResult:
    """Internal authentication result; HTTP explicitly selects public account/session fields."""

    account: Account
    session: LoginSession
    csrf_token: str = field(repr=False)
    token: str | None = field(default=None, repr=False)

    @property
    def idle_expires_at(self) -> datetime:
        """Return the exact inactivity boundary without creating a separate authentication grant."""
        return self.session.last_activity_at + timedelta(minutes=30)


class IdentityService:
    """Enforce login/password/session policy; browser or service inputs never choose authority."""

    def __init__(
        self,
        store: IdentityStore,
        passwords: PasswordHasher,
        tokens: TokenIssuer,
        clock: Clock,
        ids: IdGenerator,
    ) -> None:
        """Inject owned persistence/security/time ports without reading runtime environment."""
        self.store = store
        self.passwords = passwords
        self.tokens = tokens
        self.clock = clock
        self.ids = ids

    def issue(self, transaction: IdentityTransaction, account: Account) -> SessionResult:
        """Stage a fresh 256-bit session while holding the account's credential-version lock."""
        material = self.tokens.issue()
        now = self.clock.now()
        session = LoginSession(
            id=self.ids.new(),
            account_id=account.id,
            token_digest=material.digest,
            credential_version=account.credential_version,
            csrf_secret=material.csrf_secret,
            created_at=now,
            last_activity_at=now,
        )
        transaction.scope(account.company_id)
        transaction.save_session(session)
        return SessionResult(
            account, session, self.tokens.csrf(session.id, session.csrf_secret), material.token
        )

    def login(self, email: str, password: str) -> SessionResult:
        """Apply atomic failure accounting and lock the account before password verification/insertion."""
        address, supplied = Email(email), Password(password)
        key = self.tokens.email_key(address.normalized)
        with self.store.transaction() as transaction:
            transaction.lock_login(key)
            now = self.clock.now()
            window = transaction.login_window(key) or LoginAttemptWindow(key, now)
            if remaining := window.pause_seconds(now):
                raise LoginPaused(remaining)
            account = transaction.account_by_email(address.normalized)
            verified = self.passwords.verify(
                supplied.value, account.password_hash if account else None
            )
            if not verified or account is None:
                failed = window.failed(now)
                transaction.save_window(failed)
                transaction.commit()
                if remaining := failed.pause_seconds(now):
                    raise LoginPaused(remaining)
                raise ApplicationError(
                    "invalid_credentials", "The email or password is incorrect.", 401
                )
            result = self.issue(transaction, account)
            transaction.commit()
            return result

    def validated(
        self,
        transaction: IdentityTransaction,
        *,
        token: str | None = None,
        session_id: UUID | None = None,
        csrf: str | None = None,
        require_csrf: bool = False,
        require_password_changed: bool = False,
    ) -> SessionResult:
        """Lock current account state and reject revoked, expired or credential-mismatched sessions."""
        if (token is None) == (session_id is None):
            raise AuthenticationRequired()
        digest = self.tokens.digest(token) if token is not None else None
        session = transaction.session(digest=digest, session_id=session_id)
        if session is None:
            raise AuthenticationRequired()
        account = transaction.account(session.account_id)
        # Account locking fences a concurrent old-password login/change; refresh session state too.
        session = transaction.session(session_id=session.id)
        if account is None or session is None or not session.valid_for(account, self.clock.now()):
            raise AuthenticationRequired()
        transaction.scope(account.company_id)
        if require_password_changed and account.must_change_password:
            raise ApplicationError(
                "password_change_required", "Change your initial password first.", 403
            )
        expected = self.tokens.csrf(session.id, session.csrf_secret)
        if require_csrf and (
            csrf is None
            or not csrf.isascii()
            or len(csrf) > 256
            or not hmac.compare_digest(csrf, expected)
        ):
            raise ApplicationError("csrf_failed", "Refresh the session and retry.", 403)
        return SessionResult(account, session, expected)

    def resolve(
        self,
        *,
        token: str | None = None,
        session_id: UUID | None = None,
        csrf: str | None = None,
        require_csrf: bool = False,
        require_password_changed: bool = False,
        activity: Literal["user_activity", "poll", "background"] = "background",
    ) -> SessionResult:
        """Resolve online; polling/background validation never extends inactivity or caches identity."""
        if activity not in ("user_activity", "poll", "background"):
            raise ValueError("Invalid session activity.")
        with self.store.transaction() as transaction:
            result = self.validated(
                transaction,
                token=token,
                session_id=session_id,
                csrf=csrf,
                require_csrf=require_csrf,
                require_password_changed=require_password_changed,
            )
            if activity == "user_activity":
                session = result.session.touch(self.clock.now())
                transaction.save_session(session)
                result = SessionResult(result.account, session, result.csrf_token)
            transaction.commit()
            return result
