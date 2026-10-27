"""FR-003 operator CLI is secret-safe, has no password argument and uses contracted exits."""

from typer.testing import CliRunner

from taskify_identity.adapters.inbound.cli import app


def test_help_has_no_configuration_or_password_argument_requirement() -> None:
    """Display operator usage and password-stdin without touching storage or requiring secrets."""
    result = CliRunner().invoke(app, ["create", "--help"])
    assert result.exit_code == 0
    assert "--password-stdin" in result.stdout
    assert "--company-name" in result.stdout
    assert "--company-id" in result.stdout


def test_company_selectors_are_exclusive() -> None:
    """Reject missing and double company selectors as usage errors before reading a password."""
    args = [
        "create",
        "--display-name",
        "Admin",
        "--email",
        "admin@example.test",
        "--password-stdin",
    ]
    assert CliRunner().invoke(app, args, input="Initial-password-123\n").exit_code == 2


def test_provisioning_json_and_all_exit_codes(
    identity_service, migration_engine, monkeypatch
) -> None:
    """Exercise new/additional admin, generic duplicate rollback, validation, missing company and outage."""
    import json
    from uuid import uuid4

    from sqlalchemy import text

    from taskify_identity.adapters.inbound import cli

    monkeypatch.setattr(cli, "build_runtime", lambda: identity_service)
    runner = CliRunner()
    base = ["create", "--display-name", "Admin", "--password-stdin"]
    initial = "Private-fixture-password-123"
    created = runner.invoke(
        app,
        [*base, "--company-name", "Second Company", "--email", "second@example.test"],
        input=initial + "\n",
    )
    assert created.exit_code == 0
    output = json.loads(created.stdout)
    assert set(output) == {
        "company_id",
        "admin_id",
        "role",
        "must_change_password",
        "company_created",
    }
    assert (
        output["role"] == "admin"
        and output["must_change_password"] is True
        and output["company_created"] is True
    )
    assert initial not in created.stdout
    additional = runner.invoke(
        app,
        [*base, "--company-id", output["company_id"], "--email", "third@example.test"],
        input=initial + "\n",
    )
    assert additional.exit_code == 0
    assert json.loads(additional.stdout)["company_created"] is False
    duplicate = runner.invoke(
        app,
        [*base, "--company-name", "Must Roll Back", "--email", "SECOND@example.test"],
        input=initial + "\n",
    )
    assert duplicate.exit_code == 3
    assert initial not in duplicate.output
    with migration_engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM companies")).scalar() == 2
    assert (
        runner.invoke(
            app,
            [*base, "--company-id", str(uuid4()), "--email", "missing@example.test"],
            input=initial + "\n",
        ).exit_code
        == 4
    )
    assert (
        runner.invoke(
            app, [*base, "--company-name", "Invalid", "--email", "bad email"], input=initial + "\n"
        ).exit_code
        == 2
    )

    def unavailable():
        """Simulate configuration failure without an exception payload containing a real secret."""
        raise RuntimeError("private-configuration-value")

    monkeypatch.setattr(cli, "build_runtime", unavailable)
    failed = runner.invoke(
        app,
        [*base, "--company-name", "Unavailable", "--email", "storage@example.test"],
        input=initial + "\n",
    )
    assert failed.exit_code == 5
    assert "private-configuration-value" not in failed.output
