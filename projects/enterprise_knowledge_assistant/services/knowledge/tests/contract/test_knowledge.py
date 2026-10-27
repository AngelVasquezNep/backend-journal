"""US3 public upload/list/read contracts validate roles, fields and exact file-size boundaries."""

import pytest
from fastapi.testclient import TestClient


def test_upload_is_durable_and_unready_items_are_admin_only(
    knowledge_client: TestClient, knowledge_worker
) -> None:
    """Accept a queued revision, retain the original, then publish only after the owned worker succeeds."""
    response = knowledge_client.post(
        "/api/v1/knowledge",
        data={"title": " Leave policy "},
        files={"file": ("policy.txt", b"Company A grants 20 leave days.", "text/plain")},
        headers={"Origin": "http://localhost:8080", "X-CSRF-Token": "c" * 64},
    )
    assert response.status_code == 202
    item = response.json()
    assert response.headers["ETag"] == '"1"'
    assert item["title"] == "Leave policy" and item["availability"] == "processing"
    knowledge_client.cookies.set("taskify_session", "B" * 43)
    assert knowledge_client.get("/api/v1/knowledge").json()["items"] == []
    assert knowledge_client.get("/api/v1/knowledge/" + item["id"]).status_code == 404
    assert knowledge_worker.run_once()
    ready = knowledge_client.get("/api/v1/knowledge/" + item["id"])
    assert ready.status_code == 200 and ready.json()["availability"] == "ready"
    assert ready.json()["current_revision"]["original_filename"] == "policy.txt"


@pytest.mark.parametrize("size,status", [(0, 422), (1, 202), (20_971_520, 202), (20_971_521, 413)])
def test_file_size_boundaries(knowledge_client: TestClient, size: int, status: int) -> None:
    """Accept exact inclusive byte limits and reject zero/oversize without a partial item."""
    response = knowledge_client.post(
        "/api/v1/knowledge",
        data={"title": "Boundary"},
        files={"file": ("boundary.txt", b"x" * size, "text/plain")},
        headers={"Origin": "http://localhost:8080", "X-CSRF-Token": "c" * 64},
    )
    assert response.status_code == status
    assert len(knowledge_client.get("/api/v1/knowledge").json()["items"]) == (
        1 if status == 202 else 0
    )


def test_role_origin_csrf_and_format_rejection(knowledge_client: TestClient) -> None:
    """Reject user mutations, unknown fields, spoofed authority and mismatched binary signatures."""
    knowledge_client.cookies.set("taskify_session", "B" * 43)
    args = {"data": {"title": "Policy"}, "files": {"file": ("policy.txt", b"x", "text/plain")}}
    headers = {"Origin": "http://localhost:8080", "X-CSRF-Token": "c" * 64, "X-Role": "admin"}
    assert knowledge_client.post("/api/v1/knowledge", **args, headers=headers).status_code == 403
    knowledge_client.cookies.set("taskify_session", "A" * 43)
    assert knowledge_client.post("/api/v1/knowledge", **args).status_code == 403
    assert (
        knowledge_client.post(
            "/api/v1/knowledge",
            data={"title": "Policy", "company_id": "forged"},
            files={"file": ("policy.txt", b"x", "text/plain")},
            headers=headers,
        ).status_code
        == 400
    )
    invalid = knowledge_client.post(
        "/api/v1/knowledge",
        data={"title": "Invalid"},
        files={"file": ("policy.png", b"not an image", "image/png")},
        headers=headers,
    )
    assert invalid.status_code == 422
    assert knowledge_client.get("/api/v1/knowledge").json()["items"] == []
