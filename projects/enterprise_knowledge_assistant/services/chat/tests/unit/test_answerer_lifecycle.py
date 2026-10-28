"""Consecutive worker attempts must never inherit transports closed by an earlier attempt."""

import asyncio

from taskify_chat.adapters.outbound.langchain_openai import OpenAIAnswerer
from taskify_chat.application.ports.workflow import AcceptedConfiguration


def test_consecutive_attempts_receive_open_clients_and_close_their_own_pools() -> None:
    """Construct real SDK clients without provider calls, using separate loops as the worker does."""
    configuration = AcceptedConfiguration(
        "openai", "fixture-model", "graph-v1", "prompt-v2", "responses-v1"
    )
    for _ in range(3):
        answerer = OpenAIAnswerer(configuration, "fixture-not-a-provider-key")
        try:
            assert not answerer.model.root_client.is_closed()
            assert not answerer.model.root_async_client.is_closed()
        finally:
            asyncio.run(answerer.close())
        assert answerer.model.root_client.is_closed()
        assert answerer.model.root_async_client.is_closed()
