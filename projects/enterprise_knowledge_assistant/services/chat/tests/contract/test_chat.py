"""US1 durable acceptance, owner isolation and five terminal outcomes follow the public contract."""

from uuid import uuid4

HEADERS = {"Origin": "http://localhost:8080", "X-CSRF-Token": "c" * 64}


def test_durable_acceptance_replay_and_terminal_poll(chat_client, chat_worker) -> None:
    """A committed queued user message survives polling; replay precedes sequence and active checks."""
    assert chat_client.get("/api/v1/chat").status_code == 404
    opened = chat_client.put("/api/v1/chat", json={}, headers=HEADERS)
    assert opened.status_code == 200
    assert (
        chat_client.put("/api/v1/chat", json={}, headers=HEADERS).json()["id"]
        == opened.json()["id"]
    )
    payload = {
        "client_message_id": str(uuid4()),
        "content": "What is the company leave policy?",
        "expected_last_sequence": 0,
    }
    accepted = chat_client.post("/api/v1/chat/messages", json=payload, headers=HEADERS)
    assert accepted.status_code == 202 and accepted.json()["assistant_message"] is None
    replay = chat_client.post("/api/v1/chat/messages", json=payload, headers=HEADERS)
    assert replay.status_code == 202 and replay.json()["id"] == accepted.json()["id"]
    assert (
        chat_client.post(
            "/api/v1/chat/messages",
            json={**payload, "content": "Different question"},
            headers=HEADERS,
        ).json()["code"]
        == "idempotency_conflict"
    )
    assert (
        chat_client.post(
            "/api/v1/chat/messages",
            json={**payload, "client_message_id": str(uuid4()), "expected_last_sequence": 1},
            headers=HEADERS,
        ).json()["code"]
        == "turn_in_progress"
    )
    assert chat_worker.run_once()
    terminal = chat_client.get(accepted.json()["poll_url"])
    assert terminal.status_code == 200 and terminal.json()["state"] == "completed"
    assistant = terminal.json()["assistant_message"]
    assert assistant["outcome"] == "answer" and assistant["citations"]
    assert (
        chat_client.post("/api/v1/chat/messages", json=payload, headers=HEADERS).status_code == 200
    )
    page = chat_client.get("/api/v1/chat/messages").json()
    assert [message["sequence"] for message in page["messages"]] == [1, 2]
    assert page["last_sequence"] == 2


def test_account_isolation_restrictions_and_unknown_fields(chat_client, chat_worker) -> None:
    """Same-company accounts cannot see each other's saved private chat; browser ownership/model selectors fail."""
    chat_client.put("/api/v1/chat", json={}, headers=HEADERS)
    payload = {
        "client_message_id": str(uuid4()),
        "content": "Leave policy?",
        "expected_last_sequence": 0,
    }
    accepted = chat_client.post("/api/v1/chat/messages", json=payload, headers=HEADERS)
    assert (
        chat_client.post(
            "/api/v1/chat/messages", json={**payload, "model": "override"}, headers=HEADERS
        ).status_code
        == 400
    )
    assert (
        chat_client.post(
            "/api/v1/chat/messages", json={**payload, "content": " "}, headers=HEADERS
        ).status_code
        == 422
    )
    assert (
        chat_client.put("/api/v1/chat", json={}, headers={"Origin": HEADERS["Origin"]}).status_code
        == 403
    )
    chat_client.cookies.set("taskify_session", "B" * 43)
    assert chat_client.get("/api/v1/chat").status_code == 404
    assert chat_client.get(accepted.json()["poll_url"]).status_code == 404
    other = chat_client.put("/api/v1/chat", json={}, headers=HEADERS)
    assert other.status_code == 200 and other.json()["last_sequence"] == 0
    chat_client.cookies.clear()
    assert chat_client.get("/api/v1/chat").status_code == 401


def test_question_maximum_is_measured_after_trimming(chat_client) -> None:
    """A 4000-code-point question with surrounding spaces is accepted and saved canonically."""
    chat_client.put("/api/v1/chat", json={}, headers=HEADERS)
    result = chat_client.post(
        "/api/v1/chat/messages",
        json={
            "client_message_id": str(uuid4()),
            "content": "  " + "é" * 4000 + "  ",
            "expected_last_sequence": 0,
        },
        headers=HEADERS,
    )
    assert result.status_code == 202 and result.json()["user_message"]["content"] == "é" * 4000
