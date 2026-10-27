"""Opt-in submit-to-terminal capacity/readiness and genuine human onboarding evidence checks."""

import math
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import pytest

from tests.acceptance_config import ONBOARDING_MIN_PARTICIPANTS_PER_ROLE
from tests.fixtures.public import (
    PublicClient,
    PublicFlowError,
    private_json,
    save_private,
)


def percentile(values, fraction):
    """Use nearest-rank percentiles and retain every failure in the actual denominator."""
    return sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)]


@pytest.mark.load
def test_twenty_simultaneous_questioners(acceptance_fixture, tmp_path) -> None:
    """SC-005 includes acceptance, queue, generation/verification and one-second polling across two companies."""
    if os.environ.get("TASKIFY_RUN_LOAD") != "1":
        pytest.skip(
            "Set TASKIFY_RUN_LOAD=1 for explicit end-to-end capacity measurement."
        )
    barrier = threading.Barrier(20)
    actors = [
        (company, entry)
        for company in ("a", "b")
        for entry in acceptance_fixture["companies"][company]["users"][:10]
    ]
    assert len(actors) == 20, (
        "Provision at least ten independent questioners per company."
    )

    def measure(actor):
        """Give each simultaneous questioner its own first-party cookie jar and private conversation."""
        company, account = actor
        client = PublicClient(acceptance_fixture["base_url"])
        try:
            client.login(account["email"], account["password"])
            sequence = client.conversation()["last_sequence"]
            turn, elapsed = client.question(
                "How many leave days does company policy 2 grant?",
                expected_sequence=sequence,
                barrier=barrier,
            )
            outcome = turn["assistant_message"]["outcome"]
            return {
                "company": company,
                "seconds": elapsed,
                "outcome": outcome,
                "successful": outcome in ("answer", "insufficient_information")
                and elapsed <= 15,
            }
        except (
            PublicFlowError,
            httpx.HTTPError,
            ValueError,
            KeyError,
            threading.BrokenBarrierError,
        ):
            return {
                "company": company,
                "seconds": 90.0,
                "outcome": "failure",
                "successful": False,
            }
        finally:
            client.close()

    with ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(measure, actors))
    mode = acceptance_fixture["runtime"]["chat"]["AI_MODE"]
    evidence = {
        "run_id": acceptance_fixture["run_id"],
        "ai_mode": mode,
        "model": acceptance_fixture["runtime"]["chat"]["OPEN_AI_MODEL"],
        "actual_denominator": 20,
        "successful": sum(value["successful"] for value in results),
        "p95_seconds": percentile([value["seconds"] for value in results], 0.95),
        "results": results,
        "live_acceptance": mode == "openai",
    }
    destination = Path(
        os.environ.get("TASKIFY_LOAD_OUTPUT", str(tmp_path / "capacity.json"))
    )
    save_private(destination, evidence)
    assert evidence["successful"] >= 19, (
        "Fewer than 95% of twenty simultaneous questioners completed within fifteen seconds."
    )
    if mode != "openai":
        pytest.skip(
            "Deterministic capacity diagnostic completed; this cannot count as live-provider SC-005 acceptance."
        )


@pytest.mark.load
def test_representative_readiness(acceptance_fixture) -> None:
    """SC-006 retains failures and requires all formats plus one-byte/exact-20-MiB boundary coverage."""
    if os.environ.get("TASKIFY_RUN_LOAD") != "1":
        pytest.skip(
            "Set TASKIFY_RUN_LOAD=1 to assess representative readiness measurements."
        )
    observations = [
        item
        for company in acceptance_fixture["companies"].values()
        for item in company["items"].values()
    ]
    assert (
        observations
        and sum(item["ready_seconds"] <= 120 for item in observations)
        / len(observations)
        >= 0.95
    )
    extensions = {Path(item["file"]).suffix.lower() for item in observations}
    assert {".pdf", ".docx", ".txt", ".png", ".jpg"} <= extensions
    boundaries = acceptance_fixture.get("boundary_readiness", [])
    assert {1, 20971520} <= {entry["size_bytes"] for entry in boundaries}, (
        "Measured one-byte and exact-20-MiB readiness observations are still required."
    )
    combined = [item["ready_seconds"] for item in observations] + [
        item["ready_seconds"] for item in boundaries if item.get("state") == "ready"
    ]
    denominator = len(observations) + len(boundaries)
    assert sum(seconds <= 120 for seconds in combined) / denominator >= 0.95
    assert all(
        entry.get("state") == "ready" or entry.get("error_code") for entry in boundaries
    )
    if acceptance_fixture["runtime"]["knowledge"]["AI_MODE"] != "openai":
        pytest.skip(
            "Real parser readiness diagnostic completed with deterministic embeddings; live-provider SC-006 remains unverified."
        )


def test_human_first_time_onboarding_cohorts() -> None:
    """SC-003 never counts automated runs, implementers, coaching, abandonment or incomplete flows as success."""
    path = os.environ.get("TASKIFY_ONBOARDING_RESULTS")
    if not path:
        pytest.skip(
            "A real first-time human cohort record is required; automation is not evidence."
        )
    result = private_json(Path(path))
    assert result.get("minimum_per_role") == ONBOARDING_MIN_PARTICIPANTS_PER_ROLE
    for role, maximum in (("admin", 300), ("user", 180)):
        participants = result.get(role, [])
        assert len(participants) >= ONBOARDING_MIN_PARTICIPANTS_PER_ROLE
        assert len({entry["participant_id"] for entry in participants}) == len(
            participants
        )
        successes = 0
        for entry in participants:
            eligible = (
                entry.get("human") is True
                and entry.get("first_time") is True
                and entry.get("target_role") == role
                and entry.get("implementation_team_member") is False
            )
            assert eligible, (
                "Every recorded participant must be an eligible first-time target-role human."
            )
            assert entry.get(
                "clock_start"
            ) == "credentials_and_instructions_available" and (
                role != "admin" or entry.get("sample_file_available_at_start") is True
            )
            elapsed = entry.get("elapsed_seconds")
            assert (
                isinstance(elapsed, (int, float))
                and not isinstance(elapsed, bool)
                and elapsed >= 0
            )
            processing_wait = (
                entry.get("file_processing_wait_seconds", 0) if role == "admin" else 0
            )
            assert (
                isinstance(processing_wait, (int, float))
                and 0 <= processing_wait <= elapsed
            )
            completed = (
                entry.get("completed") is True
                and entry.get("first_attempt") is True
                and entry.get("coached") is False
                and entry.get("abandoned") is False
            )
            required = (
                ("created_user", "uploaded_supported_item")
                if role == "admin"
                else (
                    "logged_in",
                    "changed_initial_password",
                    "received_answer",
                    "opened_authorized_source",
                )
            )
            successes += int(
                completed
                and all(entry.get(step) is True for step in required)
                and elapsed - processing_wait <= maximum
            )
        assert successes / len(participants) >= 0.9, (
            f"{role} cohort failed the 90% unaided first-attempt threshold."
        )
