"""Identity-owned password and token protocols expose no cryptography-library types."""

from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class SessionSecrets:
    """Ephemeral browser credentials and stored digest/material; never log or serialize this value."""

    token: str = field(repr=False)
    digest: str = field(repr=False)
    csrf_secret: str = field(repr=False)


class PasswordHasher(Protocol):
    """Hash new passwords and perform equal-cost verification for missing accounts."""

    def hash(self, password: str) -> str:
        """Return an Argon2id hash containing its parameters; never store the input."""
        ...

    def verify(self, password: str, password_hash: str | None) -> bool:
        """Verify a real/dummy hash and return no information about account existence."""
        ...


class TokenIssuer(Protocol):
    """Issue 256-bit tokens and derive session-bound synchronizer CSRF values."""

    def issue(self) -> SessionSecrets:
        """Return fresh secret material without any persistence or logging."""
        ...

    def digest(self, token: str) -> str:
        """Return a lookup digest; malformed browser tokens cannot grant authority."""
        ...

    def csrf(self, session_id: UUID, secret: str) -> str:
        """Derive the session-bound browser CSRF token from private stored random material."""
        ...

    def email_key(self, normalized_email: str) -> str:
        """Return a secret-keyed HMAC for known and unknown email failure accounting."""
        ...
