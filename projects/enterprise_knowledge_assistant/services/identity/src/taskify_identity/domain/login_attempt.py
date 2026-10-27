"""HMAC-keyed login pauses apply identically to known and unknown email addresses."""

import math
import re
from dataclasses import dataclass, replace
from datetime import datetime, timedelta


@dataclass(frozen=True)
class LoginAttemptWindow:
    """Count failures atomically; five in 15 minutes impose a 15-minute pause.

    HMAC of normalized email, including unknown emails; atomic failure accounting;
    five failures in 15 minutes impose a 15-minute pause; no account-existence disclosure.
    """

    email_key: str
    window_started_at: datetime
    failure_count: int = 0
    blocked_until: datetime | None = None

    def __post_init__(self) -> None:
        """Validate the HMAC key, bounded failure count and aware UTC window timestamps."""
        if (
            not re.fullmatch(r"[0-9a-f]{64}", self.email_key)
            or type(self.failure_count) is not int
            or not 0 <= self.failure_count <= 5
        ):
            raise ValueError("Invalid login-window metadata.")
        for value in (self.window_started_at, self.blocked_until):
            if value is not None and (value.tzinfo is None or value.utcoffset() != timedelta(0)):
                raise ValueError("Login-window timestamps must be UTC.")

    def pause_seconds(self, now: datetime) -> int:
        """Return the nonnegative Retry-After bound without disclosing account membership."""
        return (
            max(0, math.ceil((self.blocked_until - now).total_seconds()))
            if self.blocked_until
            else 0
        )

    def failed(self, now: datetime) -> "LoginAttemptWindow":
        """Record one failure; the repository serializes this read-modify-write for every email key."""
        if now - self.window_started_at >= timedelta(minutes=15):
            return LoginAttemptWindow(self.email_key, now, 1)
        count = self.failure_count + 1
        return replace(
            self,
            failure_count=count,
            blocked_until=now + timedelta(minutes=15) if count >= 5 else None,
        )
