"""Real owned storage prevents cross-company duplicate disclosure and partial user creation."""

import pytest

from taskify_identity.application.change_password import change_password
from taskify_identity.application.create_user import create_user
from taskify_identity.application.provision_admin import provision_admin
from taskify_identity.domain.errors import ApplicationError


def test_cross_company_duplicate_is_generic_and_owner_is_server_selected(identity_service) -> None:
    """A duplicate address in another company gives the same generic conflict and no new rows."""
    service = identity_service
    provision_admin(
        service.store,
        service.passwords,
        service.clock,
        service.ids,
        company_name="Company B",
        company_id=None,
        display_name="Other admin",
        email="reserved@example.test",
        password="Other-initial-password-123",
    )
    first = service.login("admin@example.test", "Initial-password-123")
    changed = change_password(
        service, first.token, first.csrf_token, "Initial-password-123", "Changed-admin-password-456"
    )
    with pytest.raises(ApplicationError) as duplicate:
        create_user(
            service,
            changed.token,
            changed.csrf_token,
            "Client",
            "RESERVED@example.test",
            "Initial-user-password-123",
        )
    assert duplicate.value.code == "account_unavailable" and duplicate.value.status == 409
    created = create_user(
        service,
        changed.token,
        changed.csrf_token,
        "Client",
        "client@example.test",
        "Initial-user-password-123",
    )
    assert created.company_id == changed.account.company_id and created.role == "user"
    with service.store.transaction() as transaction:
        transaction.scope(created.company_id)
        stored = transaction.account(created.id)
        assert stored is not None and stored.password_hash != "Initial-user-password-123"
        assert service.passwords.verify("Initial-user-password-123", stored.password_hash)
