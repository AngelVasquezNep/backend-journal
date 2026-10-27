"""FR-016 Chat message and pagination boundaries remain separate from saved history."""

import pytest

from taskify_chat.domain.values import MessageText, Pagination, positive_version, sequence


def test_message_unicode_and_trim_bounds() -> None:
    """Accept exact Unicode limits; reject empty and oversized questions without truncation."""
    assert MessageText(" x ").value == "x"
    assert len(MessageText("😀" * 4000).value) == 4000
    for value in ("", " ", "x" * 4001):
        with pytest.raises(ValueError):
            MessageText(value)


def test_strict_sequences_versions_and_pagination() -> None:
    """Reject boolean integers, negative sequences, nonpositive versions and unbounded cursors."""
    assert sequence(0) == 0
    assert positive_version(1) == 1
    assert Pagination().limit == 50
    for value in (-1, True):
        with pytest.raises(ValueError):
            sequence(value)
    with pytest.raises(ValueError):
        positive_version(0)
    for value in (0, 101, True):
        with pytest.raises(ValueError):
            Pagination(limit=value)
    with pytest.raises(ValueError):
        Pagination(cursor="x" * 513)
