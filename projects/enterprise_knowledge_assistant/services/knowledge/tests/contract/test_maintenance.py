"""US5 mutations require admin/company/Origin/CSRF plus exact optimistic concurrency versions."""

ORIGIN = {"Origin": "http://localhost:8080", "X-CSRF-Token": "c" * 64}


def ready(client, worker):
    """Prepare a real parsed/published fixture through the public admin upload contract."""
    response = client.post(
        "/api/v1/knowledge",
        data={"title": "Original policy"},
        files={"file": ("policy.txt", b"Company leave policy grants 20 days.", "text/plain")},
        headers=ORIGIN,
    )
    assert response.status_code == 202 and worker.run_once()
    return client.get("/api/v1/knowledge/" + response.json()["id"])


def test_rename_replacement_and_removal_preserve_cas_and_source_identity(
    knowledge_client, knowledge_worker
) -> None:
    """Old originals remain current until success; obsolete revisions never relink to replacement bytes."""
    current = ready(knowledge_client, knowledge_worker)
    path = "/api/v1/knowledge/" + current.json()["id"]
    original = current.json()["current_revision"]["id"]
    assert (
        knowledge_client.patch(path, json={"title": "New title"}, headers=ORIGIN).status_code == 422
    )
    renamed = knowledge_client.patch(
        path, json={"title": "New title"}, headers={**ORIGIN, "If-Match": current.headers["etag"]}
    )
    assert renamed.status_code == 200 and renamed.headers["etag"] != current.headers["etag"]
    assert (
        knowledge_client.patch(
            path,
            json={"title": "Stale title"},
            headers={**ORIGIN, "If-Match": current.headers["etag"]},
        ).status_code
        == 409
    )
    replacement = knowledge_client.post(
        path + "/revisions",
        files={"file": ("replacement.txt", b"Company leave policy grants 25 days.", "text/plain")},
        headers={**ORIGIN, "If-Match": renamed.headers["etag"]},
    )
    assert replacement.status_code == 202 and replacement.json()["availability"] == "ready"
    assert knowledge_client.get(path + f"/source?revision_id={original}").status_code == 200
    conflict = knowledge_client.post(
        path + "/revisions",
        files={"file": ("other.txt", b"Another policy.", "text/plain")},
        headers={**ORIGIN, "If-Match": replacement.headers["etag"]},
    )
    assert conflict.status_code == 409
    assert knowledge_worker.run_once()
    published = knowledge_client.get(path)
    assert published.json()["current_revision"]["id"] != original
    assert knowledge_client.get(path + f"/source?revision_id={original}").status_code == 410
    assert (
        knowledge_client.delete(
            path, headers={**ORIGIN, "If-Match": published.headers["etag"]}
        ).status_code
        == 204
    )
    assert knowledge_client.get(path).status_code == 404
    assert (
        knowledge_client.get(
            path + "/source?revision_id=" + published.json()["current_revision"]["id"]
        ).status_code
        == 410
    )


def test_failed_replacement_retains_ready_and_users_cannot_edit(
    knowledge_client, knowledge_worker
) -> None:
    """A valid-format unreadable candidate fails durably while the old current revision survives."""
    current = ready(knowledge_client, knowledge_worker)
    path = "/api/v1/knowledge/" + current.json()["id"]
    original = current.json()["current_revision"]["id"]
    replacement = knowledge_client.post(
        path + "/revisions",
        files={"file": ("empty-content.txt", b" \n ", "text/plain")},
        headers={**ORIGIN, "If-Match": current.headers["etag"]},
    )
    assert replacement.status_code == 202 and knowledge_worker.run_once()
    result = knowledge_client.get(path).json()
    assert (
        result["current_revision"]["id"] == original
        and result["candidate_revision"]["state"] == "failed"
    )
    knowledge_client.cookies.set("taskify_session", "B" * 43)
    assert (
        knowledge_client.patch(
            path,
            json={"title": "Forbidden"},
            headers={**ORIGIN, "If-Match": str(replacement.headers["etag"])},
        ).status_code
        == 403
    )
    assert knowledge_client.get(path + f"/source?revision_id={original}").status_code == 200


def test_title_maximum_is_measured_after_trimming(knowledge_client, knowledge_worker) -> None:
    """Two hundred Unicode characters plus surrounding spaces remain valid after canonical trimming."""
    current = ready(knowledge_client, knowledge_worker)
    path = "/api/v1/knowledge/" + current.json()["id"]
    result = knowledge_client.patch(
        path,
        json={"title": "  " + "é" * 200 + "  "},
        headers={**ORIGIN, "If-Match": current.headers["etag"]},
    )
    assert result.status_code == 200 and result.json()["title"] == "é" * 200
