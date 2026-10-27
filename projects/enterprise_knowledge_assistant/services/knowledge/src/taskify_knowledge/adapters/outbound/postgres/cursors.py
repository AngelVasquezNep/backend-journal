"""Bounded authenticated cursors are scoped to company/account/role/query and never authorize reads."""

import base64
import hashlib
import hmac
import json
from datetime import datetime
from uuid import UUID

from taskify_knowledge.application.ports.identity import Principal
from taskify_knowledge.domain.errors import ApplicationError


class CursorCodec:
    """Use a domain-separated caller secret to authenticate opaque page positions."""

    def __init__(self, credential: str) -> None:
        """Derive a private cursor key without exposing/reusing raw service credentials as payload."""
        self.key = hashlib.sha256(b"taskify-knowledge-cursor-v1:" + credential.encode()).digest()

    def encode(self, actor: Principal, created: datetime, item_id: UUID) -> str:
        """Encode owner/query-bound chronological position and an HMAC in <=512 characters."""
        payload = json.dumps(
            [
                str(actor.company_id),
                str(actor.account_id),
                actor.role,
                created.isoformat(),
                str(item_id),
            ],
            separators=(",", ":"),
        ).encode()
        signed = payload + hmac.digest(self.key, payload, "sha256")
        return base64.urlsafe_b64encode(signed).decode().rstrip("=")

    def decode(self, token: str, actor: Principal) -> tuple[datetime, UUID]:
        """Reject malformed, tampered, foreign-account/company or wrong-role page cursors."""
        try:
            if not 1 <= len(token) <= 512:
                raise ValueError("Invalid cursor size.")
            raw = base64.b64decode(token + "=" * (-len(token) % 4), altchars=b"-_", validate=True)
            payload, mac = raw[:-32], raw[-32:]
            if not hmac.compare_digest(mac, hmac.digest(self.key, payload, "sha256")):
                raise ValueError("Invalid cursor signature.")
            company, account, role, created, item_id = json.loads(payload)
            if (company, account, role) != (
                str(actor.company_id),
                str(actor.account_id),
                actor.role,
            ):
                raise ValueError("Invalid cursor scope.")
            instant = datetime.fromisoformat(created)
            if instant.tzinfo is None:
                raise ValueError("Invalid cursor timestamp.")
            return instant, UUID(item_id)
        except (ValueError, TypeError, AttributeError):
            raise ApplicationError(
                "invalid_request", "Reload the list with a valid page cursor.", 400
            ) from None
