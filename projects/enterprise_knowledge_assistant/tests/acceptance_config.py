"""Shared acceptance-study configuration for Taskify.

The onboarding recorder uses this minimum separately for human admins and users.
Changing it requires updating SC-003 and reporting the configured value with the
actual cohort denominators. Automated runs do not count as human participants.
Importing this module performs no I/O and requires no application dependencies.
"""

from typing import Final

# Ten participants permit the 90% threshold to distinguish nine passes from eight.
ONBOARDING_MIN_PARTICIPANTS_PER_ROLE: Final[int] = 10
