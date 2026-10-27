"""Composed public provider/consumer contracts remain versioned and independent across all three services."""

import json
from pathlib import Path
from uuid import uuid4

import jsonschema

from tests.fixtures.public import PublicClient

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads(
    (ROOT / "specs/001-company-knowledge-qa/contracts/openapi.json").read_text()
)


def validate(name: str, value: object) -> None:
    """Validate actual composed public DTOs against the frozen OpenAPI component schema."""
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$ref": "#/components/schemas/" + name,
        "components": SCHEMA["components"],
    }
    jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker()
    ).validate(value)


def test_public_operation_inventory_is_exactly_eighteen() -> None:
    """Independent service release compatibility preserves the committed eighteen public operations."""
    operations = {
        (method.upper(), path)
        for path, methods in SCHEMA["paths"].items()
        for method in methods
        if method in ("get", "put", "post", "patch", "delete")
    }
    assert len(operations) == 18
    assert ("POST", "/users") in operations
    assert ("POST", "/chat/messages") in operations
    assert not any("/internal" in path for _, path in operations)


def test_composed_contracts_and_private_ownership(acceptance_fixture) -> None:
    """Authenticate real public actors and validate saved-chat/source/role/CSRF/tenant behavior end to end."""
    fixture = acceptance_fixture
    clients = []
    try:
        actors = {}
        for company in ("a", "b"):
            owned = fixture["companies"][company]
            for role, account in (
                ("admin", owned["admin"]),
                ("user", owned["users"][0]),
                ("other_user", owned["users"][1]),
            ):
                client = PublicClient(fixture["base_url"])
                clients.append(client)
                client.login(account["email"], account["password"])
                session = client.request("GET", "/api/v1/auth/session").json()
                validate("Session", session)
                actors[(company, role)] = client
        owner = actors[("a", "user")]
        conversation = owner.conversation()
        validate("Conversation", conversation)
        turn, _ = owner.question("How many days does company policy 2 grant?")
        validate("Turn", turn)
        page = owner.request("GET", "/api/v1/chat/messages").json()
        validate("MessagePage", page)
        assert owner.conversation()["id"] == conversation["id"]
        for selector in (
            ("a", "admin"),
            ("a", "other_user"),
            ("b", "admin"),
            ("b", "user"),
        ):
            denied = actors[selector].request("GET", turn["poll_url"], expected=(404,))
            validate("Error", denied.json())
            other_conversation = actors[selector].conversation()
            assert other_conversation["id"] != conversation["id"]
        for company in ("a", "b"):
            user = actors[(company, "user")]
            visible = user.request("GET", "/api/v1/knowledge").json()
            validate("ItemPage", visible)
            own_items = {
                entry["item_id"]
                for entry in fixture["companies"][company]["items"].values()
            }
            if company == "a":
                own_items.update(
                    entry["item_id"] for entry in fixture.get("boundary_readiness", [])
                )
            assert all(entry["id"] in own_items for entry in visible["items"])
            own = next(iter(fixture["companies"][company]["items"].values()))
            foreign_company = "b" if company == "a" else "a"
            foreign = next(
                iter(fixture["companies"][foreign_company]["items"].values())
            )
            user.request(
                "GET", f"/api/v1/knowledge/{foreign['item_id']}", expected=(404,)
            )
            user.request(
                "GET",
                f"/api/v1/knowledge/{foreign['item_id']}/source?revision_id={foreign['revision_id']}",
                expected=(404,),
            )
            user.request(
                "PATCH",
                f"/api/v1/knowledge/{own['item_id']}",
                expected=(403,),
                json={"title": "Forbidden"},
                headers={"If-Match": '"1"'},
            )
            user.request(
                "POST",
                "/api/v1/users",
                expected=(403,),
                json={
                    "display_name": "Forbidden",
                    "email": f"{uuid4()}@example.test",
                    "initial_password": "Fixture-password-only-123",
                },
            )
            user.request(
                "POST",
                "/api/v1/chat/messages",
                expected=(400,),
                json={
                    "client_message_id": str(uuid4()),
                    "content": "Company policy?",
                    "expected_last_sequence": 0,
                    "model": "browser-override",
                },
            )
            no_csrf = user.csrf
            user.csrf = None
            denied = user.request("PUT", "/api/v1/chat", expected=(403,), json={})
            user.csrf = no_csrf
            validate("Error", denied.json())
            assert user.client.get("/internal/v1/retrieval/search").status_code == 404
            assert user.client.get("/health/ready").status_code == 404
    finally:
        for client in clients:
            client.close()


def test_all_mutating_public_operations_match_dtos(acceptance_fixture) -> None:
    """Exercise the remaining auth/user/knowledge operations against the composed frozen response schemas."""
    import secrets
    import time

    fixture = acceptance_fixture
    credentials = fixture["companies"]["a"]["admin"]
    admin = PublicClient(fixture["base_url"])
    reader = PublicClient(fixture["base_url"])
    try:
        admin.login(credentials["email"], credentials["password"])
        email = f"contract-{uuid4()}@example.test"
        initial, changed = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        account = admin.request(
            "POST",
            "/api/v1/users",
            expected=(201,),
            json={
                "display_name": "Contract reader",
                "email": email,
                "initial_password": initial,
            },
        ).json()
        validate("Account", account)
        login = reader.request(
            "POST", "/api/v1/auth/login", json={"email": email, "password": initial}
        ).json()
        validate("Session", login)
        reader.csrf = login["csrf_token"]
        rotated = reader.request(
            "PUT",
            "/api/v1/auth/password",
            json={"current_password": initial, "new_password": changed},
        ).json()
        validate("Session", rotated)
        reader.csrf = rotated["csrf_token"]
        uploaded = admin.request(
            "POST",
            "/api/v1/knowledge",
            expected=(202,),
            data={"title": "Contract policy"},
            files={
                "file": (
                    "contract.txt",
                    b"Company contract policy grants 17 days.",
                    "text/plain",
                )
            },
        )
        validate("KnowledgeItem", uploaded.json())
        item = uploaded.json()
        path = "/api/v1/knowledge/" + item["id"]
        status = admin.request(
            "GET", path + "/revisions/" + item["candidate_revision"]["id"]
        ).json()
        validate("Revision", status)
        deadline = time.monotonic() + 120
        while item["availability"] != "ready" and time.monotonic() < deadline:
            time.sleep(0.5)
            response = admin.request("GET", path)
            item = response.json()
            validate("KnowledgeItem", item)
        assert item["availability"] == "ready"
        response = admin.request("GET", path)
        renamed = admin.request(
            "PATCH",
            path,
            json={"title": "Renamed contract policy"},
            headers={"If-Match": response.headers["etag"]},
        )
        validate("KnowledgeItem", renamed.json())
        original = item["current_revision"]["id"]
        source = reader.request("GET", path + "?ignored=true", expected=(400,))
        validate("Error", source.json())
        reader.request("GET", path + "/source?revision_id=" + original)
        replacement = admin.request(
            "POST",
            path + "/revisions",
            expected=(202,),
            files={
                "file": (
                    "replacement.txt",
                    b"Company contract policy grants 18 days.",
                    "text/plain",
                )
            },
            headers={"If-Match": renamed.headers["etag"]},
        )
        validate("KnowledgeItem", replacement.json())
        latest = admin.request("GET", path)
        deleted = admin.request(
            "DELETE",
            path,
            expected=(204, 409),
            headers={"If-Match": latest.headers["etag"]},
        )
        if deleted.status_code == 409:
            latest = admin.request("GET", path)
            admin.request(
                "DELETE",
                path,
                expected=(204,),
                headers={"If-Match": latest.headers["etag"]},
            )
        admin.request("GET", path + "/source?revision_id=" + original, expected=(410,))
        reader.request("POST", "/api/v1/auth/logout", expected=(204,))
        denied = reader.request("GET", "/api/v1/auth/session", expected=(401,))
        validate("Error", denied.json())
    finally:
        admin.close()
        reader.close()


def test_historical_citations_hydrate_titles_and_never_relink_replacements(
    acceptance_fixture,
) -> None:
    """Actual Chat/Knowledge HTTP preserves original provenance across rename, replacement and removal."""
    import time

    fixture = acceptance_fixture
    admin = PublicClient(fixture["base_url"])
    reader = PublicClient(fixture["base_url"])
    try:
        owner = fixture["companies"]["a"]
        admin.login(owner["admin"]["email"], owner["admin"]["password"])
        reader.login(owner["users"][0]["email"], owner["users"][0]["password"])
        name = "Zephyr benefit " + str(uuid4())
        accepted = admin.request(
            "POST",
            "/api/v1/knowledge",
            expected=(202,),
            data={"title": name},
            files={
                "file": (
                    "zephyr.txt",
                    b"Company zephyr benefit grants 19 days.",
                    "text/plain",
                )
            },
        ).json()
        path = "/api/v1/knowledge/" + accepted["id"]
        deadline = time.monotonic() + 120
        current = admin.request("GET", path)
        while current.json()["availability"] != "ready" and time.monotonic() < deadline:
            time.sleep(0.5)
            current = admin.request("GET", path)
        assert current.json()["availability"] == "ready"
        first_revision = current.json()["current_revision"]["id"]
        turn, _ = reader.question(
            "How many days does the company zephyr benefit grant?"
        )
        reference = next(
            entry
            for entry in turn["assistant_message"]["citations"]
            if entry["item_id"] == accepted["id"]
        )
        original_locator = reference["locator"]
        content = turn["assistant_message"]["content"]
        renamed = admin.request(
            "PATCH",
            path,
            json={"title": name + " revised"},
            headers={"If-Match": current.headers["etag"]},
        )
        hydrated = reader.request("GET", turn["poll_url"]).json()
        changed = next(
            entry
            for entry in hydrated["assistant_message"]["citations"]
            if entry["item_id"] == accepted["id"]
        )
        assert (
            changed["label"] == name + " revised"
            and changed["availability"] == "current"
        )
        replacement = admin.request(
            "POST",
            path + "/revisions",
            expected=(202,),
            files={
                "file": (
                    "replacement.txt",
                    b"Company zephyr benefit grants 22 days.",
                    "text/plain",
                )
            },
            headers={"If-Match": renamed.headers["etag"]},
        ).json()
        deadline = time.monotonic() + 120
        current = admin.request("GET", path)
        while (
            current.json()["current_revision"]["id"] == first_revision
            and time.monotonic() < deadline
        ):
            time.sleep(0.5)
            current = admin.request("GET", path)
        assert (
            current.json()["current_revision"]["id"]
            == replacement["candidate_revision"]["id"]
        )
        historical = reader.request("GET", turn["poll_url"]).json()["assistant_message"]
        old = next(
            entry
            for entry in historical["citations"]
            if entry["item_id"] == accepted["id"]
        )
        assert (
            historical["content"] == content
            and old["availability"] == "unavailable"
            and old["resource_url"] is None
        )
        assert (
            old["revision_id"] == first_revision and old["locator"] == original_locator
        )
        reader.request(
            "GET", path + "/source?revision_id=" + first_revision, expected=(410,)
        )
        admin.request(
            "DELETE",
            path,
            expected=(204,),
            headers={"If-Match": current.headers["etag"]},
        )
        after, _ = reader.question(
            "How many days does the company zephyr benefit grant?"
        )
        assert all(
            entry["item_id"] != accepted["id"]
            for entry in after["assistant_message"]["citations"]
        )
    finally:
        admin.close()
        reader.close()
