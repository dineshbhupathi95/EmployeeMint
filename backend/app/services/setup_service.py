import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Tenant, TenantSetting
from app.schemas.setup import (
    CompanyProfileSetup,
    SetupProgressResponse,
    WorkingDaysSetup,
)


class SetupService:
    PROFILE_KEY = "company_profile"
    WORKING_DAYS_KEY = "working_days"

    async def _get_setting(self, db: AsyncSession, tenant_id: uuid.UUID, key: str) -> dict | None:
        result = await db.execute(
            select(TenantSetting).where(
                TenantSetting.tenant_id == tenant_id,
                TenantSetting.key == key,
                TenantSetting.is_deleted.is_(False),
            )
        )
        setting = result.scalar_one_or_none()
        return setting.value if setting else None

    async def _upsert_setting(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        key: str,
        value: dict,
        created_by: uuid.UUID | None,
    ) -> None:
        result = await db.execute(
            select(TenantSetting).where(
                TenantSetting.tenant_id == tenant_id,
                TenantSetting.key == key,
                TenantSetting.is_deleted.is_(False),
            )
        )
        setting = result.scalar_one_or_none()
        if setting:
            setting.value = value
        else:
            db.add(
                TenantSetting(
                    tenant_id=tenant_id,
                    key=key,
                    value=value,
                    created_by=created_by,
                )
            )
        await db.flush()

    async def get_progress(self, db: AsyncSession, tenant: Tenant) -> SetupProgressResponse:
        profile_data = await self._get_setting(db, tenant.id, self.PROFILE_KEY)
        working_days_data = await self._get_setting(db, tenant.id, self.WORKING_DAYS_KEY)

        company_profile = CompanyProfileSetup(**profile_data) if profile_data else None
        working_days = WorkingDaysSetup(**working_days_data) if working_days_data else None

        profile_done = company_profile is not None
        working_days_done = working_days is not None and any(
            [
                working_days.monday,
                working_days.tuesday,
                working_days.wednesday,
                working_days.thursday,
                working_days.friday,
                working_days.saturday,
                working_days.sunday,
            ]
        )

        return SetupProgressResponse(
            is_setup_complete=tenant.is_setup_complete,
            steps={
                "company_profile": profile_done,
                "working_days": working_days_done,
            },
            company_profile=company_profile,
            working_days=working_days,
        )

    async def save_company_profile(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        data: CompanyProfileSetup,
        created_by: uuid.UUID | None,
    ) -> CompanyProfileSetup:
        await self._upsert_setting(db, tenant_id, self.PROFILE_KEY, data.model_dump(), created_by)
        return data

    async def save_working_days(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        data: WorkingDaysSetup,
        created_by: uuid.UUID | None,
    ) -> WorkingDaysSetup:
        if not any(data.model_dump().values()):
            raise ValueError("Select at least one working day")
        await self._upsert_setting(db, tenant_id, self.WORKING_DAYS_KEY, data.model_dump(), created_by)
        return data

    async def complete_setup(self, db: AsyncSession, tenant: Tenant) -> None:
        progress = await self.get_progress(db, tenant)
        if not all(progress.steps.values()):
            missing = [name for name, done in progress.steps.items() if not done]
            raise ValueError(f"Complete all setup steps first: {', '.join(missing)}")
        tenant.is_setup_complete = True
        await db.flush()
