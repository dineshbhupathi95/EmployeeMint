"""Encrypt/decrypt tenant AI API keys using SECRET_KEY."""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.secret_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(plain: str) -> str:
    return _fernet().encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_secret(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Could not decrypt API key — check SECRET_KEY") from exc


def mask_api_key(plain: str | None) -> str | None:
    if not plain:
        return None
    if len(plain) <= 8:
        return "••••••••"
    return f"{plain[:4]}…{plain[-4:]}"
