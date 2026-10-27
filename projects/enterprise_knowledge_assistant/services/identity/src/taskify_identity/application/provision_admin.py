"""Operator-only all-or-nothing company/admin provisioning through owned persistence ports."""

from dataclasses import dataclass
from uuid import UUID

from taskify_identity.application.ports.clock import Clock, IdGenerator
from taskify_identity.application.ports.identity_store import IdentityStore
from taskify_identity.application.ports.security import PasswordHasher
from taskify_identity.domain.account import Account
from taskify_identity.domain.company import Company
from taskify_identity.domain.errors import ApplicationError
from taskify_identity.domain.values import Email, Name, Password, identifier


@dataclass(frozen=True)
class ProvisionedAdmin:
    """Safe operator output; no initial password, hash, login token or CSRF material is returned."""

    company_id: UUID
    admin_id: UUID
    company_created: bool
    role: str = "admin"
    must_change_password: bool = True


def provision_admin(
    store: IdentityStore,
    passwords: PasswordHasher,
    clock: Clock,
    ids: IdGenerator,
    *,
    company_name: str | None,
    company_id: UUID | None,
    display_name: str,
    email: str,
    password: str,
) -> ProvisionedAdmin:
    """Validate operator input and atomically create an admin plus optional first company.

    Duplicate/unavailable email, malformed inputs and unknown companies leave no partial rows.
    Only this operator use case issues an admin role; it is never exposed through HTTP.
    """
    if (company_name is None) == (company_id is None):
        raise ValueError("Choose exactly one company name or company ID.")
    name, address, initial = Name(display_name), Email(email), Password(password)
    company_title = Name(company_name).value if company_name is not None else None
    selected = identifier(company_id) if company_id is not None else ids.new()
    password_hash = passwords.hash(initial.value)
    now = clock.now()
    account = Account(
        id=ids.new(),
        company_id=selected,
        email=address.value,
        normalized_email=address.normalized,
        display_name=name.value,
        role="admin",
        password_hash=password_hash,
        created_at=now,
    )
    with store.transaction() as transaction:
        if company_title is not None:
            transaction.create_company(Company(selected, company_title, now))
        elif not transaction.company_exists(selected):
            raise ApplicationError("not_found", "Company not found.", 404)
        transaction.scope(selected)
        transaction.save_account(account)
        transaction.commit()
    return ProvisionedAdmin(selected, account.id, company_title is not None)
