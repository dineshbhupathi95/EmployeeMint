"""Database seed script — run with: python -m app.scripts.seed"""

import asyncio

from sqlalchemy import select, text

from app.core.config import settings
from app.core.database import async_session_factory
from app.core.permissions_seed import DEFAULT_PERMISSIONS
from app.core.tenant_defaults import seed_tenant_defaults
from app.core.security import hash_password
from app.models import Permission, PlatformAdmin


async def seed_permissions(session) -> None:
    for perm_data in DEFAULT_PERMISSIONS:
        result = await session.execute(select(Permission).where(Permission.code == perm_data["code"]))
        if not result.scalar_one_or_none():
            session.add(Permission(**perm_data))


async def seed_platform_admin(session) -> None:
    result = await session.execute(
        select(PlatformAdmin).where(PlatformAdmin.email == settings.platform_admin_email)
    )
    if not result.scalar_one_or_none():
        session.add(
            PlatformAdmin(
                email=settings.platform_admin_email,
                password_hash=hash_password(settings.platform_admin_password),
                full_name="Platform Administrator",
            )
        )


async def setup_rls(session) -> None:
    """Enable RLS on tenant-scoped tables."""
    tenant_tables = [
        "tenant_settings",
        "users",
        "employees",
        "departments",
        "designations",
        "locations",
        "roles",
        "audit_logs",
        "notifications",
    ]
    for table in tenant_tables:
        await session.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
        await session.execute(text(f"DROP POLICY IF EXISTS tenant_isolation ON {table}"))
        await session.execute(
            text(f"""
                CREATE POLICY tenant_isolation ON {table}
                USING (
                    tenant_id::text = current_setting('app.current_tenant_id', true)
                    OR current_setting('app.current_tenant_id', true) = ''
                )
                WITH CHECK (
                    tenant_id::text = current_setting('app.current_tenant_id', true)
                    OR current_setting('app.current_tenant_id', true) = ''
                )
            """)
        )


async def seed_existing_tenant_defaults(session) -> None:
    """Backfill defaults for tenants created before module seeding existed."""
    from sqlalchemy import select
    from app.core.tenant_defaults import ensure_missing_workflows
    from app.models import ApprovalWorkflow, LeaveType, Tenant

    result = await session.execute(select(Tenant))
    for tenant in result.scalars().all():
        lt = await session.execute(
            select(LeaveType).where(LeaveType.tenant_id == tenant.id).limit(1)
        )
        if not lt.scalar_one_or_none():
            await seed_tenant_defaults(session, tenant.id, None)
            print(f"Seeded defaults for tenant: {tenant.slug}")
        else:
            added = await ensure_missing_workflows(session, tenant.id, None)
            if added:
                print(f"Added missing workflows for {tenant.slug}: {', '.join(added)}")

async def main() -> None:
    async with async_session_factory() as session:
        await seed_permissions(session)
        await seed_platform_admin(session)
        await seed_existing_tenant_defaults(session)
        await session.commit()

    async with async_session_factory() as session:
        try:
            await setup_rls(session)
            await session.commit()
            print("RLS policies applied.")
        except Exception as e:
            print(f"RLS setup skipped (tables may not exist yet): {e}")
            await session.rollback()

    print("Seed completed.")
    print(f"Platform admin: {settings.platform_admin_email}")


if __name__ == "__main__":
    asyncio.run(main())
