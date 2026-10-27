"""Operator-only admin CLI: hidden/stdin passwords, atomic provisioning and safe contracted exits."""

import json
import sys
from dataclasses import asdict
from typing import Annotated
from uuid import UUID

import typer

from taskify_identity.application.authenticate import IdentityService
from taskify_identity.application.provision_admin import provision_admin
from taskify_identity.domain.errors import ApplicationError

app = typer.Typer(
    help="Provision Taskify admins. Exit codes: 0 success; 2 validation; 3 email unavailable; 4 company not found; 5 storage/configuration failure.",
    pretty_exceptions_enable=False,
)


def build_runtime() -> IdentityService:
    """Load owned runtime adapters only when executing provisioning, never while displaying help."""
    from taskify_identity.adapters.outbound.settings import Settings
    from taskify_identity.bootstrap import create_service

    return create_service(Settings.from_env())


@app.callback()
def operator() -> None:
    """Expose only operator provisioning; the HTTP application has no admin-creation endpoint."""


@app.command("create")
def create(
    company_name: Annotated[
        str | None, typer.Option(help="Create a company; trimmed 1–100 characters, no controls.")
    ] = None,
    company_id: Annotated[
        UUID | None,
        typer.Option(help="Existing authorized company UUID; exclusive with company-name."),
    ] = None,
    display_name: Annotated[
        str, typer.Option(help="Admin name; trimmed 1–100 characters, no controls.")
    ] = "",
    email: Annotated[
        str, typer.Option(help="Valid globally unique email; at most 254 characters.")
    ] = "",
    password_stdin: Annotated[
        bool,
        typer.Option(
            "--password-stdin",
            help="Read one private password line; 12–128 characters, no trimming.",
        ),
    ] = False,
) -> None:
    """Create a new-company first admin or an additional admin; never echo the initial password."""
    if (company_name is None) == (company_id is None) or not display_name or not email:
        typer.echo(
            "Choose exactly one company selector and provide display-name and email.", err=True
        )
        raise typer.Exit(2)
    if password_stdin:
        raw = sys.stdin.readline(130)
        password = raw[:-2] if raw.endswith("\r\n") else raw[:-1] if raw.endswith("\n") else raw
    else:
        password = typer.prompt(
            "Initial password (12–128 characters)", hide_input=True, confirmation_prompt=True
        )
    # Import bootstrap only after usage handling: --help needs neither storage nor provider secrets.
    try:
        service = build_runtime()
    except Exception:
        typer.echo("Identity configuration or storage is unavailable.", err=True)
        raise typer.Exit(5) from None
    try:
        result = provision_admin(
            service.store,
            service.passwords,
            service.clock,
            service.ids,
            company_name=company_name,
            company_id=company_id,
            display_name=display_name,
            email=email,
            password=password,
        )
    except ValueError:
        typer.echo("Check name/email/UUID and the 12–128 character password bounds.", err=True)
        raise typer.Exit(2) from None
    except ApplicationError as error:
        code = 3 if error.code == "account_unavailable" else 4 if error.code == "not_found" else 5
        typer.echo(
            "Account unavailable."
            if code == 3
            else "Company not found."
            if code == 4
            else "Identity storage is unavailable.",
            err=True,
        )
        raise typer.Exit(code) from None
    except Exception:
        typer.echo("Identity storage is unavailable.", err=True)
        raise typer.Exit(5) from None
    typer.echo(json.dumps(asdict(result), default=str))


def main() -> None:
    """Run the independent operator CLI and preserve its documented process exit status."""
    app()
