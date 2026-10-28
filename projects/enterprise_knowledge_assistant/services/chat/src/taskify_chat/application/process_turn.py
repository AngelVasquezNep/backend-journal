"""Application-owned final login/source authorization and lease-fenced terminal persistence."""

import logging
from dataclasses import replace
from datetime import timedelta
from uuid import UUID

from taskify_chat.application.ports.answerer import AnswerDraft, HistoryMessage
from taskify_chat.application.ports.identity import Principal, SessionRequest
from taskify_chat.application.ports.knowledge import CitationKey
from taskify_chat.application.ports.workflow import AcceptedConfiguration, ActorContext, Candidate
from taskify_chat.application.service import ChatService
from taskify_chat.domain.answer_policy import supported_membership
from taskify_chat.domain.citation import Citation
from taskify_chat.domain.errors import ApplicationError, AuthenticationRequired
from taskify_chat.domain.message import ChatMessage
from taskify_chat.domain.turn import ChatTurn


def stored_actor(service: ChatService, turn: ChatTurn) -> Principal:
    """Use only validated stored queue ownership for RLS; this value does not authorize factual release."""
    return Principal(
        turn.accepted_login_session_id,
        turn.account_id,
        turn.company_id,
        "user",
        False,
        service.clock.now() + timedelta(seconds=30),
    )


def authenticate(service: ChatService, turn: ChatTurn, correlation: UUID) -> Principal:
    """Resolve the accepting login online and require exact immutable stored ownership, without idle refresh."""
    actor = service.identity.resolve(
        SessionRequest(login_session_id=turn.accepted_login_session_id, activity="background"),
        correlation,
    )
    if (
        (actor.company_id, actor.account_id, actor.login_session_id)
        != (turn.company_id, turn.account_id, turn.accepted_login_session_id)
        or actor.must_change_password
        or actor.idle_expires_at <= service.clock.now()
    ):
        raise AuthenticationRequired()
    return actor


def failure(code: str, version: str | None = None) -> Candidate:
    """Build a safe failure without partial drafts, private diagnostics or fabricated absence."""
    message = (
        "Your login expired. Log in again to view this conversation and retry."
        if code == "authentication_required"
        else "Company information changed. Please retry."
        if code == "information_changed"
        else "The answer could not be completed. Please retry."
    )
    return Candidate(AnswerDraft("failure", message=message), version, error_code=code)


def process(service: ChatService, turn: ChatTurn) -> bool:
    """Restart from fresh history/evidence on every claim and save at most one authorized terminal result."""
    actor = stored_actor(service, turn)
    correlation = service.ids.new()
    deadline = service.monotonic() + 60
    with service.store.transaction(actor) as transaction:
        if not transaction.live_turn(turn, service.clock.now()):
            return False
        question = transaction.message(turn.user_message_id)
        if question is None:
            return False
        prior = transaction.history(question.sequence)
    try:
        authenticate(service, turn, correlation)
        configuration = AcceptedConfiguration(
            turn.ai_mode,
            turn.model,
            turn.graph_version,
            turn.prompt_version,
            turn.model_config_version,
        )
        candidate = service.workflow.run(
            question.content,
            tuple(HistoryMessage(value.sender, value.content) for value in prior),
            ActorContext(
                turn.company_id, turn.account_id, turn.accepted_login_session_id, correlation
            ),
            configuration,
            deadline,
        )
    except ApplicationError as error:
        candidate = failure(
            error.code
            if error.code in ("authentication_required", "configuration_unavailable")
            else "dependency_unavailable"
        )
    except Exception:
        candidate = failure("dependency_unavailable")
    with service.store.transaction(actor) as transaction:
        # This lock is held through the fresh single-use snapshot and terminal commit.
        # A reclaimed attempt cannot use any receipt/candidate from an older holder.
        if not transaction.live_turn(turn, service.clock.now()):
            return False
        citations: tuple[Citation, ...] = ()
        try:
            authenticate(service, turn, correlation)
            if service.monotonic() >= deadline and candidate.draft.outcome != "failure":
                raise ApplicationError("attempt_timeout", "The attempt timed out.", 503)
            if candidate.draft.outcome == "answer":
                supplied = {entry.chunk_id: entry for entry in candidate.evidence}
                if (
                    not supported_membership(candidate.draft.claims, frozenset(supplied))
                    or not candidate.retrieval_config_version
                ):
                    raise ApplicationError(
                        "verification_failed", "The proposed evidence was invalid.", 503
                    )
                wanted = tuple(
                    dict.fromkeys(
                        key for claim in candidate.draft.claims for key in claim.evidence_ids
                    )
                )
                if len(wanted) > 8:
                    raise ApplicationError(
                        "verification_failed", "Too many evidence references.", 503
                    )
                keys = tuple(
                    CitationKey(supplied[key].item_id, supplied[key].revision_id, key)
                    for key in wanted
                )
                snapshot = service.knowledge.validate(
                    turn.accepted_login_session_id, keys, "release", correlation
                )
                if not snapshot.all_current:
                    raise ApplicationError(
                        "information_changed", "The source information changed.", 503
                    )
                statuses = {source.key: source for source in snapshot.sources}
                if (
                    set(statuses) != set(keys)
                    or len(snapshot.sources) != len(keys)
                    or any(
                        statuses[key].availability != "current"
                        or statuses[key].label is None
                        or statuses[key].locator is None
                        or statuses[key].resource_url is None
                        or statuses[key].locator != supplied[key.chunk_id].locator
                        for key in keys
                    )
                ):
                    raise ApplicationError(
                        "verification_failed", "The source snapshot was invalid.", 503
                    )
                assistant_id = service.ids.new()
                citations = tuple(
                    Citation(
                        id=service.ids.new(),
                        company_id=turn.company_id,
                        account_id=turn.account_id,
                        assistant_message_id=assistant_id,
                        item_id=key.item_id,
                        revision_id=key.revision_id,
                        chunk_id=key.chunk_id,
                        locator=statuses[key].locator or {},
                        title_at_answer=statuses[key].label or "",
                        validated_at=snapshot.validated_at,
                    )
                    for key in keys
                )
                if service.monotonic() >= deadline:
                    raise ApplicationError("attempt_timeout", "The attempt timed out.", 503)
            else:
                assistant_id = service.ids.new()
                if candidate.draft.claims:
                    raise ApplicationError("verification_failed", "Unexpected factual claims.", 503)
        except ApplicationError as error:
            code = (
                error.code
                if error.code
                in (
                    "authentication_required",
                    "information_changed",
                    "verification_failed",
                    "attempt_timeout",
                )
                else "dependency_unavailable"
            )
            candidate = failure(code, candidate.retrieval_config_version)
            citations = ()
            assistant_id = service.ids.new()
        except Exception:
            candidate = failure("dependency_unavailable", candidate.retrieval_config_version)
            citations = ()
            assistant_id = service.ids.new()
        conversation = transaction.conversation(lock=True)
        if conversation is None:
            return False
        content = (
            "\n\n".join(claim.text for claim in candidate.draft.claims)
            if candidate.draft.outcome == "answer"
            else candidate.draft.message or "The answer could not be completed. Please retry."
        )
        if len(content) > 16000:
            candidate = failure("verification_failed", candidate.retrieval_config_version)
            content = candidate.draft.message or "Please retry."
            citations = ()
        now = service.clock.now()
        # Snapshot validity survives a source change after validation; lease validity does not.
        if not transaction.live_turn(turn, now):
            return False
        message = ChatMessage(
            id=assistant_id,
            company_id=turn.company_id,
            account_id=turn.account_id,
            conversation_id=turn.conversation_id,
            turn_id=turn.id,
            sequence=conversation.last_sequence + 1,
            sender="assistant",
            content=content,
            outcome=candidate.draft.outcome,
            refusal_text=candidate.draft.refusal_text,
            created_at=now,
        )
        transaction.save_message(message)
        for citation in citations:
            transaction.save_citation(citation)
        transaction.save_conversation(
            replace(conversation, last_sequence=message.sequence, updated_at=now)
        )
        transaction.save_turn(
            replace(
                turn,
                state="failed" if message.outcome == "failure" else "completed",
                assistant_message_id=message.id,
                completed_at=now,
                error_code=candidate.error_code,
                lease_owner=None,
                lease_until=None,
                retrieval_config_version=candidate.retrieval_config_version,
            )
        )
        transaction.commit()
    logging.getLogger("taskify.turn").info(
        "turn_terminal outcome=%s code=%s attempt=%d citations=%d",
        message.outcome,
        candidate.error_code or "none",
        turn.attempt_count,
        len(citations),
    )
    return True
