from uuid import UUID

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.logging import tenant_id_var


async def set_rls_tenant(session: AsyncSession, tenant_id: UUID | None) -> None:
    """Set PostgreSQL session variable for Row-Level Security policies."""
    if tenant_id:
        await session.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": str(tenant_id)},
        )
    else:
        await session.execute(text("SELECT set_config('app.current_tenant_id', '', true)"))


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Extract tenant slug from path prefix for unauthenticated routes."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        # Tenant slug may be resolved later during auth; path hint stored on request state
        parts = request.url.path.strip("/").split("/")
        if len(parts) >= 3 and parts[0] == "api" and parts[1] == "v1" and parts[2] not in {
            "auth",
            "platform",
            "health",
            "docs",
            "openapi.json",
            "redoc",
        }:
            request.state.tenant_slug_hint = parts[2] if parts[2] != "tenants" else None
        return await call_next(request)
