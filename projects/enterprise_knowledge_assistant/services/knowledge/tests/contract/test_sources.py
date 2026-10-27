"""Current-original access resolves exact company/revision ownership for every request."""

from fastapi.testclient import TestClient


def test_source_opens_only_current_same_company_original(
    knowledge_client: TestClient, knowledge_worker
) -> None:
    """Stream the immutable original with safe headers; foreign company gets an indistinguishable 404."""
    original = b"Company A grants 20 leave days."
    item = knowledge_client.post(
        "/api/v1/knowledge",
        data={"title": "Policy"},
        files={"file": ("policy.txt", original, "text/plain")},
        headers={"Origin": "http://localhost:8080", "X-CSRF-Token": "c" * 64},
    ).json()
    assert knowledge_worker.run_once()
    ready = knowledge_client.get("/api/v1/knowledge/" + item["id"]).json()
    path = (
        "/api/v1/knowledge/" + item["id"] + "/source?revision_id=" + ready["current_revision"]["id"]
    )
    knowledge_client.cookies.set("taskify_session", "B" * 43)
    source = knowledge_client.get(path)
    assert source.status_code == 200 and source.content == original
    assert source.headers["X-Content-Type-Options"] == "nosniff"
    assert source.headers["Cache-Control"] == "no-store"
    knowledge_client.cookies.set("taskify_session", "C" * 43)
    assert knowledge_client.get(path).status_code == 404
    assert knowledge_client.get("/api/v1/knowledge/" + item["id"]).status_code == 404
