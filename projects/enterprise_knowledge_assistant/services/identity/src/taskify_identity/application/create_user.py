"""Admin-only company user creation never accepts company or privilege overrides."""

from taskify_identity.application.authenticate import IdentityService
from taskify_identity.domain.account import Account
from taskify_identity.domain.errors import ApplicationError
from taskify_identity.domain.values import Email, Name, Password


def create_user(
    service: IdentityService,
    token: str,
    csrf: str,
    display_name: str,
    email: str,
    initial_password: str,
) -> Account:
    """Validate input, hash privately and create one user under a fresh locked admin session.

    A global unique-email constraint produces the same generic conflict across companies.
    Authentication, credential version, first-change, role and CSRF are checked in the
    committing transaction; revocation cannot race a previously cached authorization.
    """
    name, address, password = Name(display_name), Email(email), Password(initial_password)
    hashed = service.passwords.hash(password.value)
    with service.store.transaction() as transaction:
        actor = service.validated(
            transaction, token=token, csrf=csrf, require_csrf=True, require_password_changed=True
        )
        if actor.account.role != "admin":
            raise ApplicationError("forbidden", "Only a company admin can create users.", 403)
        account = Account(
            id=service.ids.new(),
            company_id=actor.account.company_id,
            email=address.value,
            normalized_email=address.normalized,
            display_name=name.value,
            role="user",
            password_hash=hashed,
            created_at=service.clock.now(),
        )
        transaction.save_session(actor.session.touch(service.clock.now()))
        transaction.save_account(account)
        transaction.commit()
        return account
