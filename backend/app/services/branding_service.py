"""Tenant organization name + logo branding."""

from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Tenant

UPLOAD_ROOT = Path(__file__).resolve().parents[2] / "uploads"
ALLOWED_TYPES = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/pjpeg": ".jpg",
    "image/png": ".png",
    "image/x-png": ".png",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
}
MAX_BYTES = 2 * 1024 * 1024


def _sniff_image(content: bytes) -> tuple[str, str] | None:
    if len(content) >= 3 and content[:3] == b"\xff\xd8\xff":
        return "image/jpeg", ".jpg"
    if len(content) >= 8 and content[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png", ".png"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp", ".webp"
    # SVG is text — light check
    head = content[:200].lstrip().lower()
    if head.startswith(b"<?xml") or head.startswith(b"<svg"):
        return "image/svg+xml", ".svg"
    return None


class BrandingService:
    def absolute_path(self, relative: str) -> Path:
        return UPLOAD_ROOT / relative

    async def update_name(self, db: AsyncSession, tenant: Tenant, name: str) -> Tenant:
        cleaned = name.strip()
        if not cleaned:
            raise ValueError("Organization name is required")
        if len(cleaned) > 255:
            raise ValueError("Organization name is too long")
        tenant.name = cleaned
        await db.flush()
        return tenant

    async def save_logo(
        self,
        db: AsyncSession,
        *,
        tenant: Tenant,
        file_name: str,
        content_type: str | None,
        content: bytes,
    ) -> Tenant:
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
            elif lower.endswith(".svg"):
                ct, ext = "image/svg+xml", ".svg"
            else:
                raise ValueError(
                    "Only JPG, PNG, WebP, or SVG logos are allowed. "
                    f"Got type '{content_type or 'unknown'}' for '{file_name or 'file'}'."
                )

        if tenant.logo_path:
            old = self.absolute_path(tenant.logo_path)
            if old.exists():
                old.unlink(missing_ok=True)

        rel_dir = Path("logos") / str(tenant.id)
        abs_dir = UPLOAD_ROOT / rel_dir
        abs_dir.mkdir(parents=True, exist_ok=True)
        stored = f"{uuid.uuid4().hex}{ext}"
        abs_path = abs_dir / stored
        abs_path.write_bytes(content)

        tenant.logo_path = str(rel_dir / stored)
        tenant.logo_content_type = ct
        await db.flush()
        return tenant

    async def delete_logo(self, db: AsyncSession, tenant: Tenant) -> Tenant:
        if tenant.logo_path:
            path = self.absolute_path(tenant.logo_path)
            if path.exists():
                path.unlink(missing_ok=True)
        tenant.logo_path = None
        tenant.logo_content_type = None
        await db.flush()
        return tenant
