"""Measure explicit one-byte/exact-20-MiB processing outcomes through public flows on an isolated fixture run."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.fixtures.provision import runtime_configuration
from tests.fixtures.public import (
    PublicClient,
    PublicFlowError,
    private_json,
    save_private,
)


def measure(configuration: Path, corpus: Path, allow_paid: bool = False) -> None:
    """Retain every boundary failure/explanatory code in the actual readiness denominator."""
    fixture = private_json(configuration)
    runtime = runtime_configuration()
    if runtime != fixture["runtime"]:
        raise PublicFlowError(
            "Fixture/runtime configuration changed; use a fresh isolated run."
        )
    if runtime["knowledge"]["AI_MODE"] == "openai" and not allow_paid:
        raise PublicFlowError(
            "Boundary embeddings require explicit paid-provider opt-in."
        )
    account = fixture["companies"]["a"]["admin"]
    client = PublicClient(fixture["base_url"])
    client.login(account["email"], account["password"])
    observations = fixture.setdefault("boundary_readiness", [])
    try:
        for filename in ("one-byte.txt", "exactly-20-mib.txt"):
            path = corpus / "invalid" / filename
            size = path.stat().st_size
            if any(entry["size_bytes"] == size for entry in observations):
                continue
            item, elapsed = client.upload(
                "Boundary readiness " + filename, path, allow_failed=True
            )
            current = item.get("current_revision")
            candidate = item.get("candidate_revision")
            observations.append(
                {
                    "size_bytes": size,
                    "item_id": item["id"],
                    "state": "ready" if current else "failed",
                    "ready_seconds": elapsed,
                    "error_code": candidate.get("error_code") if candidate else None,
                }
            )
            save_private(configuration, fixture)
    finally:
        client.close()


def main() -> None:
    """Extend an existing private fixture record without resetting existing companies or rerunning paid corpus uploads."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", required=True, type=Path)
    parser.add_argument("--corpus", required=True, type=Path)
    parser.add_argument("--allow-paid-provider", action="store_true")
    args = parser.parse_args()
    measure(args.fixtures, args.corpus, args.allow_paid_provider)
    print("Boundary readiness outcomes recorded privately.")


if __name__ == "__main__":
    main()
