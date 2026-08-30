"""Multi-user authentication (部署准备：多用户认证).

JWT bearer token + bcrypt password hashing. Opt-in via
``ASRO_AUTH_ENABLED=true`` — the default (false) keeps the local dev /
E2E flow auth-free. When enabled, every /api/v1/* route (except
/auth/* and /health) requires a valid Bearer token.

Roles: admin (user management + full access) / analyst (full access) /
viewer (read-only). Permission enforcement is a fast follow — the
current gate is binary (authenticated or 401).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from jose import JWTError, jwt
import bcrypt as _bcrypt
from pydantic import BaseModel, Field
from sqlalchemy import JSON, Boolean, DateTime, Integer, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.config import get_settings
from app.storage.orm import Base

def hash_password(plain: str) -> str:
    return _bcrypt.hashpw(plain.encode("utf-8"), _bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return _bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_token(username: str, role: str) -> str:
    settings = get_settings()
    expiry = timedelta(hours=settings.jwt_expiry_hours)
    payload = {
        "sub": username,
        "role": role,
        "exp": datetime.now(timezone.utc) + expiry,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> dict | None:
    try:
        settings = get_settings()
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except JWTError:
        return None


class UserORM(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(16), default="analyst")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def _utc() -> datetime:
    return datetime.now(timezone.utc)


class UserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def count(self) -> int:
        from sqlalchemy import func

        return self._session.scalar(select(func.count(UserORM.id))) or 0

    def get_by_username(self, username: str) -> UserORM | None:
        return self._session.scalars(
            select(UserORM).where(UserORM.username == username)
        ).first()

    def create_user(self, *, username: str, password: str, role: str = "analyst") -> UserORM:
        row = UserORM(
            user_id=f"usr_{uuid4().hex[:12]}",
            username=username,
            password_hash=hash_password(password),
            role=role,
            enabled=True,
            created_at=_utc(),
        )
        self._session.add(row)
        self._session.flush()
        return row


class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(default="analyst", pattern="^(admin|analyst|viewer)$")


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)
