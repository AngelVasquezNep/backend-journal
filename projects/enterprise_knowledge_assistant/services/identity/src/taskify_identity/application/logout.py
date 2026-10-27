"""Logout revokes one owned login and never touches persistent conversation history."""

from dataclasses import replace

from taskify_identity.application.authenticate import IdentityService


def logout(service: IdentityService, token: str, csrf: str) -> None:
    """Validate the current login/CSRF and atomically revoke only that session."""
    with service.store.transaction() as transaction:
        result = service.validated(transaction, token=token, csrf=csrf, require_csrf=True)
        transaction.save_session(replace(result.session, revoked_at=service.clock.now()))
        transaction.commit()
