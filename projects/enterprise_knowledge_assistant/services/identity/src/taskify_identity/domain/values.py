"""Framework-free Identity values; lengths count Unicode code points, never bytes."""

import re
import unicodedata
from dataclasses import dataclass, field
from email.errors import HeaderParseError
from email.headerregistry import Address
from uuid import UUID

from taskify_identity.domain.errors import ValidationFailed


@dataclass(frozen=True)
class Name:
    """Trim; 1–100 code points; reject control characters; raise ValueError otherwise."""

    value: str

    def __post_init__(self) -> None:
        """Normalize surrounding whitespace and reject invalid names without echoing input."""
        if not isinstance(self.value, str):
            raise ValidationFailed("A name must be text.")
        value = self.value.strip()
        if not 1 <= len(value) <= 100 or any(unicodedata.category(c) == "Cc" for c in self.value):
            raise ValidationFailed("Names must contain 1–100 characters and no controls.")
        object.__setattr__(self, "value", value)


@dataclass(frozen=True)
class Email:
    """Valid address syntax, at most 254 characters; case-insensitive uniqueness."""

    value: str

    def __post_init__(self) -> None:
        """Validate one addr-spec, excluding display names, whitespace and control injection."""
        if not isinstance(self.value, str) or not 1 <= len(self.value) <= 254:
            raise ValidationFailed("Enter a valid email of at most 254 characters.")
        if any(c.isspace() or unicodedata.category(c) == "Cc" for c in self.value):
            raise ValidationFailed("Enter a valid email address.")
        try:
            address = Address(addr_spec=self.value)
            domain = address.domain.encode("idna").decode("ascii")
            valid_domain = bool(re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?", domain))
            if not address.username or not valid_domain or ".." in domain:
                raise ValidationFailed("Invalid address.")
        except (ValueError, UnicodeError, HeaderParseError) as error:
            raise ValidationFailed("Enter a valid email address.") from error

    @property
    def normalized(self) -> str:
        """Return the case-insensitive persistence key; repository uniqueness is authoritative."""
        return self.value.casefold()


@dataclass(frozen=True)
class Password:
    """12–128 code points; no trimming/truncation; new password differs on first change."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        """Reject out-of-range passwords without transforming or exposing their content."""
        if not isinstance(self.value, str) or not 12 <= len(self.value) <= 128:
            raise ValidationFailed("Passwords must contain 12–128 characters.")


def identifier(value: UUID | str) -> UUID:
    """Return a valid UUID; raise a safe ValueError for malformed identifiers."""
    try:
        return value if isinstance(value, UUID) else UUID(value)
    except (ValueError, TypeError, AttributeError) as error:
        raise ValidationFailed("A valid UUID is required.") from error
