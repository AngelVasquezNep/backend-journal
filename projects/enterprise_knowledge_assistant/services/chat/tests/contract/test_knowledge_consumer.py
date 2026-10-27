"""Knowledge consumer fails closed on malformed active versions, evidence and source snapshots."""

from uuid import uuid4

import httpx
import pytest

from taskify_chat.adapters.outbound.http.knowledge import KnowledgeHTTP
from taskify_chat.domain.errors import DependencyUnavailable


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"pipeline_version": "", "retrieval_config_version": "v", "candidates": []},
        {"pipeline_version": "v", "retrieval_config_version": "", "candidates": []},
        {
            "pipeline_version": "v",
            "retrieval_config_version": "v",
            "candidates": [{"text": "partial"}],
        },
    ],
)
def test_missing_or_malformed_retrieval_is_never_empty_evidence(payload) -> None:
    """Only a well-formed successful empty response can mean no company evidence."""
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    )
    gateway = KnowledgeHTTP(
        "http://knowledge:8000", "fixture-worker", allow_insecure=True, client=client
    )
    with pytest.raises(DependencyUnavailable):
        gateway.search(uuid4(), "Company policy?", uuid4())


def test_empty_success_retains_active_versions() -> None:
    """An empty result still records which current configuration this attempt searched."""
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={
                    "pipeline_version": "active-pipeline",
                    "retrieval_config_version": "active-retrieval",
                    "candidates": [],
                },
            )
        )
    )
    result = KnowledgeHTTP(
        "http://knowledge:8000", "fixture-worker", allow_insecure=True, client=client
    ).search(uuid4(), "Company policy?", uuid4())
    assert result.candidates == () and result.retrieval_config_version == "active-retrieval"
