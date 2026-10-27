"""Immutable account ownership and versioned password-change state."""

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from typing import Literal
from uuid import UUID

from taskify_identity.domain.values import Email, Name, identifier


@dataclass(frozen=True, kw_only=True)
class Account:
    """Keep email globally unique and ownership immutable; never persist a plaintext password.

    Unique normalized email across companies; role exactly `admin` or `user`;
    company immutable in this scope; password never persisted as plaintext.
    """

    id: UUID
    company_id: UUID
    email: str
    normalized_email: str
    display_name: str
    role: Literal["admin", "user"]
    password_hash: str = field(repr=False)
    credential_version: int = 1
    must_change_password: bool = True
    created_at: datetime
    password_changed_at: datetime | None = None

    def __post_init__(self) -> None:
        """Validate canonical fields and UTC timestamps; ownership cannot be reassigned."""
        identifier(self.id)
        identifier(self.company_id)
        if Email(self.email).normalized != self.normalized_email:
            raise ValueError("Account email must have a matching normalized key.")
        object.__setattr__(self, "display_name", Name(self.display_name).value)
        if self.role not in ("admin", "user") or type(self.must_change_password) is not bool:
            raise ValueError("Invalid account permissions.")
        if (
            type(self.credential_version) is not int
            or self.credential_version < 1
            or not self.password_hash.startswith("$argon2id$")
        ):
            raise ValueError("Invalid account credential metadata.")
        for value in (self.created_at, self.password_changed_at):
            if value is not None and (value.tzinfo is None or value.utcoffset() != timedelta(0)):
                raise ValueError("Account timestamps must be UTC.")

    def change_password(self, password_hash: str, now: datetime) -> "Account":
        """Return a version-incremented changed account, preserving immutable company and role."""
        return replace(
            self,
            password_hash=password_hash,
            credential_version=self.credential_version + 1,
            must_change_password=False,
            password_changed_at=now,
        )
