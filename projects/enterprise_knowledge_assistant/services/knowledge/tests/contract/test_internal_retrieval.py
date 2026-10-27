"""Internal provider contracts expose only current-company evidence and exact atomic source snapshots."""

from uuid import uuid4


def test_search_and_snapshot_enforce_service_scope_and_exact_ownership(
    knowledge_client, knowledge_worker, admin_principal
) -> None:
    """Fresh background session authority precedes embedding/ranking and source metadata construction."""
    uploaded = knowledge_client.post(
        "/api/v1/knowledge",
        data={"title": "Leave policy"},
        files={"file": ("policy.txt", b"Company leave policy grants 20 days.", "text/plain")},
        headers={"Origin": "http://localhost:8080", "X-CSRF-Token": "c" * 64},
    )
    assert uploaded.status_code == 202 and knowledge_worker.run_once()
    payload = {
        "login_session_id": str(admin_principal.login_session_id),
        "query": "What is the company leave policy?",
        "request_id": str(uuid4()),
    }
    api = {"Authorization": "Bearer fixture-chat-api-" + "x" * 32}
    worker = {"Authorization": "Bearer fixture-chat-worker-" + "x" * 32}
    assert knowledge_client.post("/internal/v1/retrieval/search", json=payload).status_code == 401
    assert (
        knowledge_client.post(
            "/internal/v1/retrieval/search", json=payload, headers=api
        ).status_code
        == 403
    )
    result = knowledge_client.post("/internal/v1/retrieval/search", json=payload, headers=worker)
    assert result.status_code == 200
    body = result.json()
    assert (
        body["pipeline_version"]
        and body["retrieval_config_version"]
        and len(body["candidates"]) == 1
    )
    evidence = body["candidates"][0]
    key = {name: evidence[name] for name in ("item_id", "revision_id", "chunk_id")}
    batch = {
        "login_session_id": str(admin_principal.login_session_id),
        "citations": [key],
        "purpose": "release",
    }
    assert (
        knowledge_client.post("/internal/v1/sources/validate", json=batch, headers=api).status_code
        == 403
    )
    snapshot = knowledge_client.post("/internal/v1/sources/validate", json=batch, headers=worker)
    assert snapshot.status_code == 200 and snapshot.json()["all_current"] is True
    assert (
        snapshot.json()["sources"][0]["resource_url"]
        == f"/api/v1/knowledge/{key['item_id']}/source?revision_id={key['revision_id']}"
    )
    forged = {**key, "revision_id": str(uuid4())}
    blocked = knowledge_client.post(
        "/internal/v1/sources/validate", json={**batch, "citations": [forged]}, headers=worker
    )
    assert blocked.status_code == 200 and blocked.json()["all_current"] is False
    assert (
        blocked.json()["sources"][0]["label"] is None
        and blocked.json()["sources"][0]["locator"] is None
    )
    assert (
        knowledge_client.post(
            "/internal/v1/retrieval/search",
            json={**payload, "company_id": str(uuid4())},
            headers=worker,
        ).status_code
        == 422
    )
