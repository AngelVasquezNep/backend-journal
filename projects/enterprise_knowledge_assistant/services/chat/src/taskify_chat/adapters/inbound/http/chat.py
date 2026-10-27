"""Public saved-private-chat routes enforce online ownership, strict input and nonrefreshing automatic polling."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BeforeValidator, Field

from taskify_chat.adapters.inbound.http.common import (
    StrictDTO,
    json_guard,
    origin_guard,
    request_id,
)
from taskify_chat.adapters.outbound.settings import Settings
from taskify_chat.application.conversations import history, open_conversation
from taskify_chat.application.ports.identity import Principal, SessionRequest, SessionValidator
from taskify_chat.application.ports.knowledge import CitationKey, SourceStatus
from taskify_chat.application.service import ChatService
from taskify_chat.application.submit_message import TurnView, read_turn, submit
from taskify_chat.domain.citation import Citation
from taskify_chat.domain.errors import ApplicationError, AuthenticationRequired
from taskify_chat.domain.message import ChatMessage
from taskify_chat.domain.values import MessageText, Pagination


def json_uuid(value: object) -> UUID:
    """Accept a JSON string UUID explicitly while all other primitive fields remain strict."""
    if not isinstance(value, (UUID, str)):
        raise ValueError("A UUID is required.")
    return UUID(value) if isinstance(value, str) else value


def canonical_question(value: object) -> object:
    """Validate the 1–4000-character bound after trimming, without changing nonstring primitive types."""
    return MessageText(value).value if isinstance(value, str) else value


class OpenInput(StrictDTO):
    """Own conversation opening accepts only an empty object; no arbitrary chat/account selector exists."""


class MessageInput(StrictDTO):
    """No browser override exists for ownership, model, prompts, graph or retrieval settings."""

    client_message_id: Annotated[UUID, BeforeValidator(json_uuid)]
    content: Annotated[
        str, BeforeValidator(canonical_question), Field(min_length=1, max_length=4000)
    ]
    expected_last_sequence: Annotated[int, Field(ge=0)]


def query_fields(request: Request, permitted: set[str]) -> None:
    """Reject unknown/duplicate selectors rather than silently accepting authority-like parameters."""
    if any(
        key not in permitted or len(request.query_params.getlist(key)) != 1
        for key in request.query_params
    ):
        raise ApplicationError("invalid_request", "Check the documented query fields.", 400)


def actor(
    request: Request,
    settings: Settings,
    identity: SessionValidator,
    *,
    mutation: bool = False,
    poll: bool = False,
) -> Principal:
    """Select activity and CSRF policy in the receiving handler, never from browser JSON or headers."""
    if mutation:
        origin_guard(request, settings.public_origin)
        json_guard(request)
    token = request.cookies.get(settings.cookie_name)
    if not token:
        raise AuthenticationRequired()
    csrf = request.headers.get("x-csrf-token")
    if mutation and not csrf:
        raise ApplicationError("csrf_failed", "Refresh the session and retry.", 403)
    try:
        selected = SessionRequest(
            session_token=token,
            csrf_token=csrf,
            require_csrf=mutation,
            require_password_changed=True,
            activity="poll" if poll else "user_activity",
        )
    except ValueError:
        raise AuthenticationRequired() from None
    return identity.resolve(selected, request_id(request))


def hydrated(
    service: ChatService, principal: Principal, messages: tuple[ChatMessage, ...], correlation: UUID
) -> list[dict[str, object]]:
    """Hydrate only own saved citations; dependency outages disable links without rewriting saved text."""
    saved: dict[UUID, tuple[Citation, ...]] = {}
    with service.store.transaction(principal) as transaction:
        for message in messages:
            saved[message.id] = (
                transaction.citations(message.id) if message.sender == "assistant" else ()
            )
    keys = tuple(
        dict.fromkeys(
            CitationKey(value.item_id, value.revision_id, value.chunk_id)
            for values in saved.values()
            for value in values
        )
    )
    statuses: dict[CitationKey, SourceStatus] = {}
    try:
        for index in range(0, len(keys), 100):
            result = service.knowledge.validate(
                principal.login_session_id, keys[index : index + 100], "history", correlation
            )
            statuses.update({value.key: value for value in result.sources})
    except AuthenticationRequired:
        raise
    except Exception:
        statuses = {}
    result_messages = []
    for message in messages:
        references = []
        for citation in saved[message.id]:
            current = statuses.get(
                CitationKey(citation.item_id, citation.revision_id, citation.chunk_id)
            )
            available = current is not None and current.availability == "current"
            references.append(
                {
                    "id": str(citation.id),
                    "item_id": str(citation.item_id),
                    "revision_id": str(citation.revision_id),
                    "chunk_id": str(citation.chunk_id),
                    "locator": dict(current.locator)
                    if current is not None and available and current.locator
                    else dict(citation.locator),
                    "label": current.label
                    if current is not None and available and current.label
                    else citation.title_at_answer,
                    "availability": "current" if available else "unavailable",
                    "resource_url": current.resource_url
                    if current is not None and available
                    else None,
                }
            )
        result_messages.append(
            {
                "id": str(message.id),
                "turn_id": str(message.turn_id),
                "sequence": message.sequence,
                "sender": message.sender,
                "content": message.content,
                "outcome": message.outcome,
                "refusal_text": message.refusal_text,
                "citations": references,
                "created_at": message.created_at.isoformat(),
            }
        )
    return result_messages


def turn_body(
    service: ChatService, principal: Principal, view: TurnView, correlation: UUID
) -> dict[str, object]:
    """Serialize only committed user/terminal messages and a server-built exact own polling URL."""
    messages = hydrated(
        service,
        principal,
        (view.user_message,) + ((view.assistant_message,) if view.assistant_message else ()),
        correlation,
    )
    return {
        "id": str(view.turn.id),
        "state": view.turn.state,
        "user_message": messages[0],
        "assistant_message": messages[1] if len(messages) > 1 else None,
        "poll_url": f"/api/v1/chat/turns/{view.turn.id}",
        "error_code": view.turn.error_code,
        "retryable": view.turn.state == "failed",
    }


def chat_router(service: ChatService, identity: SessionValidator, settings: Settings) -> APIRouter:
    """Bind the unique own chat without new-chat/reset/share/list-other-chats capabilities."""
    router = APIRouter(prefix="/api/v1/chat")

    def conversation_body(request: Request, create: bool) -> dict[str, object]:
        """Return saved metadata after online authentication and atomic optional creation."""
        query_fields(request, set())
        principal = actor(request, settings, identity, mutation=create)
        view = open_conversation(service, principal, create=create)
        value = view.conversation
        return {
            "id": str(value.id),
            "last_sequence": value.last_sequence,
            "active_turn_id": str(view.active_turn_id) if view.active_turn_id else None,
            "created_at": value.created_at.isoformat(),
            "updated_at": value.updated_at.isoformat(),
        }

    @router.put("")
    def open_chat(body: OpenInput, request: Request) -> dict[str, object]:
        """Open/create the same saved conversation idempotently under an account-level lock."""
        return conversation_body(request, True)

    @router.get("")
    def get_chat(request: Request) -> dict[str, object]:
        """Get own saved metadata; return 404 before lazy initial creation."""
        return conversation_body(request, False)

    @router.get("/messages")
    def messages(request: Request) -> dict[str, object]:
        """Read own ordered newest/older history pages; no conversation ID is accepted."""
        query_fields(request, {"limit", "cursor"})
        principal = actor(request, settings, identity)
        raw = request.query_params.get("limit", "50")
        try:
            if not raw.isascii() or not raw.isdigit() or len(raw) > 3:
                raise ValueError()
            pagination = Pagination(int(raw), request.query_params.get("cursor"))
        except ValueError:
            raise ApplicationError(
                "validation_failed", "Use limit 1–100 and a valid history cursor.", 422
            ) from None
        page = history(service, principal, pagination)
        return {
            "messages": hydrated(service, principal, page.messages, request_id(request)),
            "next_cursor": page.next_cursor,
            "last_sequence": page.last_sequence,
        }

    @router.post("/messages", status_code=202)
    def send_message(body: MessageInput, request: Request) -> JSONResponse:
        """Return 202 after durable acceptance, or 200 for an identical already-terminal replay."""
        query_fields(request, set())
        principal = actor(request, settings, identity, mutation=True)
        view = submit(
            service, principal, body.client_message_id, body.content, body.expected_last_sequence
        )
        return JSONResponse(
            turn_body(service, principal, view, request_id(request)),
            status_code=200 if view.turn.state in ("completed", "failed") else 202,
        )

    @router.get("/turns/{turn_id}")
    def poll(turn_id: UUID, request: Request) -> dict[str, object]:
        """Automatic processing polls never refresh session inactivity and expose no other account's turn."""
        query_fields(request, set())
        principal = actor(request, settings, identity, poll=True)
        return turn_body(
            service, principal, read_turn(service, principal, turn_id), request_id(request)
        )

    return router
