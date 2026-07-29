import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.platform import TenantScopedMixin


class User(Base, TenantScopedMixin):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_platform_impersonation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    employee: Mapped["Employee | None"] = relationship(back_populates="user", uselist=False)
    user_roles: Mapped[list["UserRole"]] = relationship(back_populates="user")


class Employee(Base, TenantScopedMixin):
    __tablename__ = "employees"
    __table_args__ = (UniqueConstraint("tenant_id", "employee_code", name="uq_employees_tenant_code"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, unique=True
    )
    employee_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    work_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    date_of_joining: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )
    designation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("designations.id", ondelete="SET NULL"), nullable=True
    )
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id", ondelete="SET NULL"), nullable=True
    )
    reports_to_employee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="SET NULL"), nullable=True
    )
    employment_status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    avatar_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    avatar_content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    user: Mapped["User | None"] = relationship(back_populates="employee")
    department: Mapped["Department | None"] = relationship(
        back_populates="employees",
        foreign_keys=[department_id],
    )
    designation: Mapped["Designation | None"] = relationship(back_populates="employees")
    location: Mapped["Location | None"] = relationship(back_populates="employees")
    reports_to: Mapped["Employee | None"] = relationship(
        remote_side=[id],
        foreign_keys=[reports_to_employee_id],
    )


class Department(Base, TenantScopedMixin):
    __tablename__ = "departments"
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_departments_tenant_name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    head_employee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="SET NULL"), nullable=True
    )
    parent_department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )

    employees: Mapped[list["Employee"]] = relationship(
        back_populates="department",
        foreign_keys="Employee.department_id",
    )
    head: Mapped["Employee | None"] = relationship(
        foreign_keys=[head_employee_id],
    )
    parent: Mapped["Department | None"] = relationship(
        remote_side=[id],
        foreign_keys=[parent_department_id],
    )


class Designation(Base, TenantScopedMixin):
    __tablename__ = "designations"
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_designations_tenant_name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    level: Mapped[int | None] = mapped_column(nullable=True)

    employees: Mapped[list["Employee"]] = relationship(back_populates="designation")


class Location(Base, TenantScopedMixin):
    __tablename__ = "locations"
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_locations_tenant_name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    employees: Mapped[list["Employee"]] = relationship(back_populates="location")
