import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

logger = logging.getLogger(__name__)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(
    subject: str,
    *,
    extra_claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    payload: dict[str, Any] = {"sub": subject, "exp": expire, "type": "access"}
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_expire_days)
    payload = {
        "sub": subject,
        "exp": expire,
        "type": "refresh",
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])


def verify_token(token: str, expected_type: str) -> dict[str, Any] | None:
    try:
        payload = decode_token(token)
        if payload.get("type") != expected_type:
            return None
        return payload
    except JWTError:
        return None
