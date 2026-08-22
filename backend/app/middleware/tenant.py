from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def set_rls_tenant(session: AsyncSession, tenant_id: UUID | None) -> None:
    """Set PostgreSQL session variable for Row-Level Security policies."""
    if tenant_id:
        await session.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": str(tenant_id)},
        )
    else:
        await session.execute(text("SELECT set_config('app.current_tenant_id', '', true)"))


class TenantContextMiddleware:
    """Extract tenant slug from path prefix for unauthenticated routes."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            path = scope.get("path", "").strip("/")
            parts = path.split("/")
            if len(parts) >= 3 and parts[0] == "api" and parts[1] == "v1" and parts[2] not in {
                "auth",
                "platform",
                "health",
                "docs",
                "openapi.json",
                "redoc",
            }:
                scope.setdefault("state", {})
                scope["state"]["tenant_slug_hint"] = parts[2] if parts[2] != "tenants" else None
        await self.app(scope, receive, send)
