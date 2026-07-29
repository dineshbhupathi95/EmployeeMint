import re
from typing import Annotated

from pydantic import BeforeValidator

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _normalize_email(value: str) -> str:
    email = value.strip().lower()
    if not EMAIL_PATTERN.match(email):
        raise ValueError("invalid email format")
    return email


# Allows dev/local domains (e.g. admin@employeemint.local) that EmailStr rejects.
AuthEmail = Annotated[str, BeforeValidator(_normalize_email)]
