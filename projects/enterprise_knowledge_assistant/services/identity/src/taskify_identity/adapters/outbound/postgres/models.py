"""Owned Identity ORM mappings mirror the versioned migration; no ORM object enters core."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Identity's independent mapping registry; it never includes another service's tables."""


class CompanyRow(Base):
    """Map canonical company identity; CLI provisioning creates its first admin atomically."""

    __tablename__ = "companies"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AccountRow(Base):
    """Map immutable ownership, globally unique canonical email and versioned Argon2 metadata."""

    __tablename__ = "accounts"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"))
    email: Mapped[str] = mapped_column(String(254))
    normalized_email: Mapped[str] = mapped_column(String(254), unique=True)
    display_name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(5))
    password_hash: Mapped[str] = mapped_column(String)
    credential_version: Mapped[int] = mapped_column(Integer)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SessionRow(Base):
    """Map only login-token digests and private CSRF material, never raw browser tokens."""

    __tablename__ = "login_sessions"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    account_id: Mapped[UUID] = mapped_column(ForeignKey("accounts.id"))
    token_digest: Mapped[str] = mapped_column(String(64), unique=True)
    credential_version: Mapped[int] = mapped_column(Integer)
    csrf_secret: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LoginWindowRow(Base):
    """Map global HMAC-keyed login windows without retaining failed plaintext email addresses."""

    __tablename__ = "login_attempt_windows"
    email_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    window_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    failure_count: Mapped[int] = mapped_column(Integer)
    blocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
