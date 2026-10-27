"""Host acceptance consumes preprovisioned private public-flow fixtures; no runtime operator access is injected."""

import hashlib
import json
import os
from pathlib import Path

import pytest

from tests.fixtures.public import private_json

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def acceptance_fixture():
    """Require a ready private fixture record tied to this exact frozen corpus manifest."""
    path = os.environ.get("TASKIFY_FIXTURES")
    if not path:
        pytest.skip(
            "Provision host-owned fixtures and set TASKIFY_FIXTURES explicitly."
        )
    fixture = private_json(Path(path))
    assert fixture.get("status") == "ready", "Host fixture provisioning is incomplete."
    digest = hashlib.sha256(
        (ROOT / "tests/fixtures/corpus/manifest.json").read_bytes()
    ).hexdigest()
    assert fixture.get("manifest_sha256") == digest, (
        "Fixture corpus version changed; provision a fresh isolated run."
    )
    assert set(fixture["companies"]) == {"a", "b"}
    return fixture


@pytest.fixture(scope="session")
def reviewed_manifest(acceptance_fixture):
    """Require independent reference review before any paid quality collection can count toward acceptance."""
    if os.environ.get("TASKIFY_RUN_LIVE_OPENAI") != "1":
        pytest.skip("Live evaluation is opt-in and can incur provider cost.")
    for service in ("chat", "knowledge"):
        assert acceptance_fixture["runtime"][service]["AI_MODE"] == "openai", (
            "Deterministic mode cannot count as live-provider evidence."
        )
    assert acceptance_fixture["runtime"]["chat"]["OPEN_AI_MODEL"], (
        "An exact accepted chat model is required."
    )
    review_path = os.environ.get("TASKIFY_REFERENCE_REVIEW")
    assert review_path, (
        "Independent reference review is required before paid collection."
    )
    review = private_json(Path(review_path))
    assert review.get("manifest_sha256") == acceptance_fixture["manifest_sha256"]
    assert (
        review.get("approved") is True
        and review.get("independent") is True
        and review.get("implementation_team_member") is False
    )
    assert review.get("reviewed_by"), "Identify the independent reference reviewer."
    return json.loads((ROOT / "tests/fixtures/corpus/manifest.json").read_text())
