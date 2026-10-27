"""Random opaque login tokens, lookup digests and synchronizer CSRF derivation."""

import hashlib
import hmac
import re
import secrets
from uuid import UUID

from taskify_identity.application.ports.security import SessionSecrets
from taskify_identity.domain.errors import AuthenticationRequired


class SecureTokens:
    """Keep raw tokens ephemeral; keyed email HMACs avoid a plaintext failed-email registry."""

    def __init__(self, email_hmac_key: str) -> None:
        """Retain a private process key supplied by validated bootstrap configuration."""
        self.key = email_hmac_key.encode("utf-8")

    def issue(self) -> SessionSecrets:
        """Generate a fresh random 256-bit login token and independent CSRF secret."""
        token = secrets.token_urlsafe(32)
        return SessionSecrets(token, self.digest(token), secrets.token_urlsafe(32))

    def digest(self, token: str) -> str:
        """Hash only a well-formed opaque token; malformed cookies receive a generic denial."""
        if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
            raise AuthenticationRequired()
        return hashlib.sha256(token.encode("ascii")).hexdigest()

    def csrf(self, session_id: UUID, secret: str) -> str:
        """Derive a session-bound synchronizer token without returning stored CSRF material."""
        return hmac.new(secret.encode("ascii"), session_id.bytes, hashlib.sha256).hexdigest()

    def email_key(self, normalized_email: str) -> str:
        """Return the HMAC key used for atomic failures of both known and unknown emails."""
        return hmac.new(self.key, normalized_email.encode("utf-8"), hashlib.sha256).hexdigest()
