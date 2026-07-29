"""Profile avatar upload/storage."""

import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Employee

UPLOAD_ROOT = Path(__file__).resolve().parents[2] / "uploads"
ALLOWED_TYPES = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/pjpeg": ".jpg",
    "image/png": ".png",
    "image/x-png": ".png",
    "image/webp": ".webp",
}
MAX_BYTES = 2 * 1024 * 1024


def _sniff_image(content: bytes) -> tuple[str, str] | None:
    """Detect image type from magic bytes. Returns (content_type, ext)."""
    if len(content) >= 3 and content[:3] == b"\xff\xd8\xff":
        return "image/jpeg", ".jpg"
    if len(content) >= 8 and content[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png", ".png"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp", ".webp"
    return None


class AvatarService:
    def absolute_path(self, relative: str) -> Path:
        return UPLOAD_ROOT / relative

    async def save(
        self,
        db: AsyncSession,
        *,
        employee: Employee,
        file_name: str,
        content_type: str | None,
        content: bytes,
    ) -> Employee:
        if not content:
            raise ValueError("Empty file")
        if len(content) > MAX_BYTES:
            raise ValueError("File too large (max 2MB)")

        sniffed = _sniff_image(content)
        ct = (content_type or "").lower().split(";")[0].strip()
        ext = ALLOWED_TYPES.get(ct)

        if sniffed:
            ct, ext = sniffed
        elif not ext:
            lower = (file_name or "").lower()
            if lower.endswith((".jpg", ".jpeg")):
                ct, ext = "image/jpeg", ".jpg"
            elif lower.endswith(".png"):
                ct, ext = "image/png", ".png"
            elif lower.endswith(".webp"):
                ct, ext = "image/webp", ".webp"
            else:
                raise ValueError(
                    "Only JPG, PNG, or WebP images are allowed. "
                    f"Got type '{content_type or 'unknown'}' for '{file_name or 'file'}'."
                )

        # Remove previous file if present
        if employee.avatar_path:
            old = self.absolute_path(employee.avatar_path)
            if old.exists():
                old.unlink(missing_ok=True)

        rel_dir = Path("avatars") / str(employee.tenant_id) / str(employee.id)
        abs_dir = UPLOAD_ROOT / rel_dir
        abs_dir.mkdir(parents=True, exist_ok=True)
        stored = f"{uuid.uuid4().hex}{ext}"
        abs_path = abs_dir / stored
        abs_path.write_bytes(content)

        employee.avatar_path = str(rel_dir / stored).replace("\\", "/")
        employee.avatar_content_type = ct
        await db.flush()
        return employee

    async def clear(self, db: AsyncSession, employee: Employee) -> None:
        if employee.avatar_path:
            path = self.absolute_path(employee.avatar_path)
            if path.exists():
                path.unlink(missing_ok=True)
        employee.avatar_path = None
        employee.avatar_content_type = None
        await db.flush()
