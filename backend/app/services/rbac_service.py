import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.permissions_seed import DEFAULT_PERMISSIONS, DEFAULT_ROLES
from app.core.security import hash_password
from app.models import Permission, Role, RolePermission, User, UserRole


def _permission_matches(granted: str, required: str) -> bool:
    if granted == "*" or granted == required:
        return True
    if granted.endswith(".*"):
        prefix = granted[:-2]
        return required == prefix or required.startswith(f"{prefix}.")
    return False


def resolve_permissions(granted_codes: list[str], all_permission_codes: list[str]) -> list[str]:
    resolved: set[str] = set()
    for required in all_permission_codes:
        for granted in granted_codes:
            if _permission_matches(granted, required):
                resolved.add(required)
                break
    if "*" in granted_codes:
        resolved.update(all_permission_codes)
    return sorted(resolved)


class RBACService:
    async def get_user_permissions(self, db: AsyncSession, user_id: uuid.UUID) -> list[str]:
        result = await db.execute(select(Permission.code))
        all_codes = [row[0] for row in result.all()]

        result = await db.execute(
            select(User)
            .options(
                selectinload(User.user_roles).selectinload(UserRole.role).selectinload(Role.role_permissions).selectinload(RolePermission.permission)
            )
            .where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return []

        granted: list[str] = []
        for user_role in user.user_roles:
            for rp in user_role.role.role_permissions:
                granted.append(rp.permission.code)

        return resolve_permissions(granted, all_codes)

    async def seed_tenant_roles(self, db: AsyncSession, tenant_id: uuid.UUID) -> dict[str, Role]:
        result = await db.execute(select(Permission))
        permissions = {p.code: p for p in result.scalars().all()}
        roles: dict[str, Role] = {}

        for role_name, perm_codes in DEFAULT_ROLES.items():
            role = Role(
                tenant_id=tenant_id,
                name=role_name,
                description=f"Default {role_name} role",
                is_system=True,
            )
            db.add(role)
            await db.flush()

            for code in perm_codes:
                if code == "*":
                    for perm in permissions.values():
                        db.add(RolePermission(role_id=role.id, permission_id=perm.id))
                elif code.endswith(".*"):
                    prefix = code[:-2]
                    for perm_code, perm in permissions.items():
                        if perm_code == prefix or perm_code.startswith(f"{prefix}."):
                            db.add(RolePermission(role_id=role.id, permission_id=perm.id))
                elif code in permissions:
                    db.add(RolePermission(role_id=role.id, permission_id=permissions[code].id))

            roles[role_name] = role

        return roles

    async def assign_role(self, db: AsyncSession, user_id: uuid.UUID, role_id: uuid.UUID) -> None:
        existing = await db.execute(
            select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
        )
        if existing.scalar_one_or_none():
            return
        db.add(UserRole(user_id=user_id, role_id=role_id))

    async def get_user_role_ids(self, db: AsyncSession, user_id: uuid.UUID) -> list[uuid.UUID]:
        result = await db.execute(select(UserRole.role_id).where(UserRole.user_id == user_id))
        return [row[0] for row in result.all()]

    async def set_user_roles(self, db: AsyncSession, user_id: uuid.UUID, role_ids: list[uuid.UUID]) -> None:
        result = await db.execute(select(UserRole).where(UserRole.user_id == user_id))
        for user_role in result.scalars().all():
            await db.delete(user_role)
        for role_id in role_ids:
            db.add(UserRole(user_id=user_id, role_id=role_id))

    async def get_role_matrix(self, db: AsyncSession, tenant_id: uuid.UUID):
        from app.schemas.rbac import PermissionResponse, RolePermissionMatrix, RoleResponse

        # Avoid stale identity-map Role/RolePermission from prior updates in this session
        db.expire_all()

        perms_result = await db.execute(select(Permission).order_by(Permission.module, Permission.code))
        permissions = [PermissionResponse.model_validate(p) for p in perms_result.scalars().all()]

        roles_result = await db.execute(
            select(Role)
            .options(selectinload(Role.role_permissions).selectinload(RolePermission.permission))
            .where(Role.tenant_id == tenant_id, Role.is_deleted.is_(False))
            .order_by(Role.name)
            .execution_options(populate_existing=True)
        )
        roles = []
        for role in roles_result.scalars().unique().all():
            role_perms = []
            for rp in role.role_permissions:
                if rp.permission is None:
                    continue
                role_perms.append(PermissionResponse.model_validate(rp.permission))
            roles.append(
                RoleResponse(
                    id=role.id,
                    name=role.name,
                    description=role.description,
                    is_system=role.is_system,
                    permissions=role_perms,
                )
            )

        return RolePermissionMatrix(permissions=permissions, roles=roles)
