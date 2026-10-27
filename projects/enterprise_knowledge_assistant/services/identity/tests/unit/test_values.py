"""FR-016 Identity boundary cases count Unicode code points and preserve secret inputs."""

import pytest

from taskify_identity.domain.values import Email, Name, Password, identifier


def test_name_and_password_exact_bounds() -> None:
    """Accept exact limits without byte counting or trimming a password."""
    assert Name("  A  ").value == "A"
    assert len(Name("😀" * 100).value) == 100
    assert Password(" " * 12).value == " " * 12
    assert len(Password("😀" * 128).value) == 128
    assert "secret-value-123" not in repr(Password("secret-value-123"))


@pytest.mark.parametrize("value", ["", " ", "a" * 101, "a\x00b", "\nA"])
def test_invalid_names(value: str) -> None:
    """Reject empty, oversized and control-bearing names before any persistence."""
    with pytest.raises(ValueError):
        Name(value)


@pytest.mark.parametrize("value", ["x" * 11, "x" * 129, ""])
def test_invalid_password_bounds(value: str) -> None:
    """Reject each out-of-range password with a corrective, redacted error."""
    with pytest.raises(ValueError):
        Password(value)


def test_email_normalization_and_identifiers() -> None:
    """Normalize email case and reject malformed addresses and identifiers."""
    assert Email("Admin@Example.test").normalized == "admin@example.test"
    for value in ("a@@example.test", "a@", "@example.test", "a b@example.test", "a@.example.test"):
        with pytest.raises(ValueError):
            Email(value)
    with pytest.raises(ValueError):
        identifier("not-a-uuid")
