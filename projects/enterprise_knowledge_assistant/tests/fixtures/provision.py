"""Operator-only fixture provisioner: CLI admins, public first-login/users/uploads, no runtime Docker capability."""

import argparse
import hashlib
import json
import secrets
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.fixtures.public import PublicClient, PublicFlowError, save_private

ROOT = Path(__file__).resolve().parents[2]


def runtime_configuration() -> dict:
    """Inspect only nonsecret runtime mode/model metadata through explicit host operator access."""
    result = {}
    script = "import json,os; print(json.dumps({k:os.environ.get(k,'') for k in ('AI_MODE','OPEN_AI_MODEL','PIPELINE_VERSION','OPENAI_EMBEDDING_MODEL')}))"
    for service in ("chat", "knowledge"):
        output = subprocess.run(
            ["docker", "compose", "exec", "-T", service, "python", "-c", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if output.returncode:
            raise PublicFlowError("Runtime configuration inspection failed.")
        result[service] = json.loads(output.stdout)
    return result


def provision(
    output: Path, corpus: Path, origin: str, users: int, allow_paid: bool
) -> dict:
    """Create distinct disposable companies without truncating/resetting existing application data."""
    runtime = runtime_configuration()
    if (
        any(value["AI_MODE"] == "openai" for value in runtime.values())
        and not allow_paid
    ):
        raise PublicFlowError(
            "OpenAI uploads incur provider cost; explicit --allow-paid-provider is required."
        )
    if runtime["chat"]["AI_MODE"] != runtime["knowledge"]["AI_MODE"]:
        raise PublicFlowError("Fixture runs require matching explicit AI modes.")
    manifest_path = ROOT / "tests/fixtures/corpus/manifest.json"
    manifest = json.loads(manifest_path.read_text())
    record = {
        "run_id": str(uuid4()),
        "base_url": origin,
        "runtime": runtime,
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "companies": {},
        "status": "incomplete",
    }
    save_private(output, record, exclusive=True)
    try:
        for company in manifest["companies"]:
            initial, password = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            email = f"admin-{company}-{record['run_id']}@example.test"
            completed = subprocess.run(
                [
                    "docker",
                    "compose",
                    "run",
                    "--rm",
                    "--no-deps",
                    "-T",
                    "identity",
                    "taskify-admin",
                    "create",
                    "--company-name",
                    f"Acceptance {company} {record['run_id']}",
                    "--display-name",
                    f"Acceptance admin {company}",
                    "--email",
                    email,
                    "--password-stdin",
                ],
                cwd=ROOT,
                input=initial + "\n",
                capture_output=True,
                text=True,
                check=False,
            )
            if completed.returncode:
                raise PublicFlowError("Host CLI admin provisioning failed.")
            provisioned = json.loads(completed.stdout)
            client = PublicClient(origin)
            account = client.login(email, initial, password)
            owned = {
                "company_id": provisioned["company_id"],
                "admin": {
                    "email": email,
                    "password": password,
                    "account_id": account["id"],
                },
                "users": [],
                "items": {},
            }
            record["companies"][company] = owned
            save_private(output, record)
            for index in range(users):
                initial_user, changed_user = (
                    secrets.token_urlsafe(32),
                    secrets.token_urlsafe(32),
                )
                address = f"user-{company}-{index}-{record['run_id']}@example.test"
                created = client.request(
                    "POST",
                    "/api/v1/users",
                    expected=(201,),
                    json={
                        "display_name": f"Acceptance user {index}",
                        "email": address,
                        "initial_password": initial_user,
                    },
                ).json()
                user = PublicClient(origin)
                user.login(address, initial_user, changed_user)
                user.close()
                owned["users"].append(
                    {
                        "email": address,
                        "password": changed_user,
                        "account_id": created["id"],
                    }
                )
            for entry in manifest["documents"]:
                if entry["company"] != company:
                    continue
                path = corpus / entry["file"]
                item, elapsed = client.upload(entry["title"], path)
                owned["items"][entry["id"]] = {
                    "item_id": item["id"],
                    "revision_id": item["current_revision"]["id"],
                    "file": entry["file"],
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "ready_seconds": elapsed,
                }
                save_private(output, record)
            client.close()
        record["status"] = "ready"
        save_private(output, record)
        return record
    except Exception:
        save_private(output, record)
        raise


def main() -> None:
    """Prepare host-owned fixtures before containerized/live evaluation and print only a safe output path."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--corpus", required=True, type=Path)
    parser.add_argument("--base-url", default="http://localhost:8080")
    parser.add_argument("--users-per-company", type=int, default=20)
    parser.add_argument("--allow-paid-provider", action="store_true")
    parser.add_argument("--measure-boundaries", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.users_per_company <= 100:
        parser.error("users-per-company must be 1–100.")
    try:
        provision(
            args.output,
            args.corpus,
            args.base_url,
            args.users_per_company,
            args.allow_paid_provider,
        )
        if args.measure_boundaries:
            from tests.fixtures.measure_boundaries import measure

            measure(args.output, args.corpus, args.allow_paid_provider)
    except (PublicFlowError, ValueError, OSError, KeyError, TypeError, httpx.HTTPError):
        raise SystemExit(
            "Fixture provisioning failed; private progress is retained. Check service readiness/configuration without printing credentials."
        ) from None
    print(f"Host public-flow fixtures ready: {args.output}")


if __name__ == "__main__":
    main()
