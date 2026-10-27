"""Pure factual release policy permits only verified supplied evidence and application-built source references."""

import re
from typing import Protocol
from uuid import UUID


class CitedClaim(Protocol):
    """A plain factual claim has bounded text and one or more supplied evidence identities."""

    @property
    def text(self) -> str:
        """Return immutable proposed claim text."""
        ...

    @property
    def evidence_ids(self) -> tuple[UUID, ...]:
        """Return immutable proposed evidence references."""
        ...


def plain(value: str) -> bool:
    """Reject HTML/URLs/Markdown links from model text; rendering remains escaped plain text."""
    return (
        bool(value.strip())
        and len(value) <= 12000
        and not re.search(r"https?://|www\.|<[^>]+>|\]\s*\(", value, re.IGNORECASE)
    )


def supported_membership(claims: tuple[CitedClaim, ...], evidence_ids: frozenset[UUID]) -> bool:
    """Require claims, citations, unique known IDs and safe bounded text for a factual answer."""
    return (
        bool(claims)
        and len(claims) <= 12
        and all(
            plain(claim.text)
            and 1 <= len(claim.evidence_ids) <= 8
            and len(set(claim.evidence_ids)) == len(claim.evidence_ids)
            and set(claim.evidence_ids) <= evidence_ids
            for claim in claims
        )
    )
