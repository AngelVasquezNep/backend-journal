"""Initial-password change invalidates every old session under one account/version fence."""

from taskify_identity.application.authenticate import IdentityService, SessionResult
from taskify_identity.domain.errors import ApplicationError
from taskify_identity.domain.values import Password


def change_password(
    service: IdentityService, token: str, csrf: str, current_password: str, new_password: str
) -> SessionResult:
    """Verify current/different passwords, increment version and revoke all previous account sessions.

    All previous account sessions revoked; the one new login and account change commit atomically.
    A racing initial-password session fails its version check after obtaining the account lock.
    """
    current, replacement = Password(current_password), Password(new_password)
    if current.value == replacement.value:
        raise ApplicationError("validation_failed", "Choose a different new password.", 422)
    with service.store.transaction() as transaction:
        result = service.validated(transaction, token=token, csrf=csrf, require_csrf=True)
        if not service.passwords.verify(current.value, result.account.password_hash):
            raise ApplicationError("invalid_credentials", "The current password is incorrect.", 401)
        account = result.account.change_password(
            service.passwords.hash(replacement.value), service.clock.now()
        )
        transaction.save_account(account)
        transaction.revoke_sessions(account.id, service.clock.now())
        issued = service.issue(transaction, account)
        transaction.commit()
        return issued
