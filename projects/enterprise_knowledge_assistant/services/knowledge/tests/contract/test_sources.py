"""Current-original access resolves exact company/revision ownership for every request."""

from uuid import uuid4

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


def test_multiple_chunk_citations_download_the_complete_original(
    knowledge_client, knowledge_worker, admin_principal
) -> None:
    """Distinct evidence fragments retain one original identity and never become download bodies."""
    original = "".join(
        f"Policy section {index}: employees receive 20 days of annual leave.\r\n"
        for index in range(150)
    ).encode()
    uploaded = knowledge_client.post(
        "/api/v1/knowledge",
        data={"title": "Complete leave policy"},
        files={"file": ("leave-policy.txt", original, "text/plain")},
        headers={"Origin": "http://localhost:8080", "X-CSRF-Token": "c" * 64},
    )
    assert uploaded.status_code == 202 and knowledge_worker.run_once()
    item = knowledge_client.get("/api/v1/knowledge/" + uploaded.json()["id"]).json()
    worker = {"Authorization": "Bearer fixture-chat-worker-" + "x" * 32}
    search = knowledge_client.post(
        "/internal/v1/retrieval/search",
        json={
            "login_session_id": str(admin_principal.login_session_id),
            "query": "Company leave policy?",
            "request_id": str(uuid4()),
        },
        headers=worker,
    )
    assert search.status_code == 200
    chunks = search.json()["candidates"]
    assert 1 < len(chunks) < 20
    assert len({chunk["chunk_id"] for chunk in chunks}) == len(chunks)
    assert all(chunk["item_id"] == item["id"] for chunk in chunks)
    assert all(chunk["revision_id"] == item["current_revision"]["id"] for chunk in chunks)
    assert all(len(chunk["text"].encode()) < len(original) for chunk in chunks)
    keys = [
        {field: chunk[field] for field in ("item_id", "revision_id", "chunk_id")}
        for chunk in chunks[:2]
    ]
    snapshot = knowledge_client.post(
        "/internal/v1/sources/validate",
        json={
            "login_session_id": str(admin_principal.login_session_id),
            "citations": keys,
            "purpose": "release",
        },
        headers=worker,
    )
    assert snapshot.status_code == 200 and snapshot.json()["all_current"]
    sources = snapshot.json()["sources"]
    assert len(sources) == 2
    assert sources[0]["resource_url"] == sources[1]["resource_url"]
    knowledge_client.cookies.set("taskify_session", "B" * 43)
    for source in sources:
        response = knowledge_client.get(source["resource_url"])
        assert response.status_code == 200 and response.content == original
        assert response.headers["content-type"].split(";")[0] == "text/plain"
        assert response.headers["content-disposition"] == 'attachment; filename="leave-policy.txt"'
