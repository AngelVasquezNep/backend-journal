"""Argon2id hashing records parameters and equalizes missing-account verification work."""

import secrets

from pwdlib import PasswordHash


class ArgonPasswords:
    """Use pwdlib's recommended recorded Argon2id profile without storing plaintext passwords."""

    def __init__(self) -> None:
        """Prepare one process-local dummy hash; no input credential is retained or logged."""
        self.hasher = PasswordHash.recommended()
        self.dummy = self.hasher.hash(secrets.token_urlsafe(32))

    def hash(self, password: str) -> str:
        """Return an Argon2id encoded hash; callers validate code-point bounds first."""
        return self.hasher.hash(password)

    def verify(self, password: str, password_hash: str | None) -> bool:
        """Verify a real or dummy hash and never distinguish unknown accounts through diagnostics."""
        verified = self.hasher.verify(password, password_hash or self.dummy)
        return verified and password_hash is not None
