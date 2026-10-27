"""Application composition is plain owned ports; requests/model state never become authority."""

from collections.abc import Callable
from dataclasses import dataclass

from taskify_chat.application.ports.chat_store import ChatStore
from taskify_chat.application.ports.clock import Clock, IdGenerator
from taskify_chat.application.ports.identity import Principal, SessionValidator
from taskify_chat.application.ports.knowledge import KnowledgeGateway
from taskify_chat.application.ports.workflow import AcceptedConfiguration, TurnWorkflow
from taskify_chat.domain.errors import ApplicationError


@dataclass
class ChatService:
    """Inject owned persistence, online authority/evidence, bounded workflow and runtime ports."""

    store: ChatStore
    identity: SessionValidator
    knowledge: KnowledgeGateway
    workflow: TurnWorkflow
    clock: Clock
    ids: IdGenerator
    configuration: AcceptedConfiguration
    monotonic: Callable[[], float]


def allowed(actor: Principal) -> None:
    """Enforce mandatory first-password change after online session resolution."""
    if actor.must_change_password:
        raise ApplicationError(
            "password_change_required", "Change your initial password first.", 403
        )
