"""Schemas for employee personal, academic, and work history details."""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, Field


class PersonalDetailsUpdate(BaseModel):
    date_of_birth: date | None = None
    gender: str | None = Field(default=None, max_length=30)
    marital_status: str | None = Field(default=None, max_length=30)
    blood_group: str | None = Field(default=None, max_length=10)
    nationality: str | None = Field(default=None, max_length=100)
    personal_email: str | None = Field(default=None, max_length=255)
    father_name: str | None = Field(default=None, max_length=200)
    emergency_contact_name: str | None = Field(default=None, max_length=200)
    emergency_contact_phone: str | None = Field(default=None, max_length=50)
    emergency_contact_relation: str | None = Field(default=None, max_length=100)
    current_address: str | None = None
    permanent_address: str | None = None
    pan_number: str | None = Field(default=None, max_length=20)
    aadhaar_number: str | None = Field(default=None, max_length=20)
    passport_number: str | None = Field(default=None, max_length=50)


class BackgroundVerificationUpdate(BaseModel):
    background_verification_status: str | None = Field(default=None, max_length=30)
    background_verification_notes: str | None = None


class EducationCreate(BaseModel):
    degree: str = Field(min_length=1, max_length=200)
    institution: str = Field(min_length=1, max_length=255)
    field_of_study: str | None = Field(default=None, max_length=200)
    year_of_passing: int | None = Field(default=None, ge=1950, le=2100)
    grade_or_percentage: str | None = Field(default=None, max_length=50)
    notes: str | None = None


class EducationUpdate(BaseModel):
    degree: str | None = Field(default=None, min_length=1, max_length=200)
    institution: str | None = Field(default=None, min_length=1, max_length=255)
    field_of_study: str | None = Field(default=None, max_length=200)
    year_of_passing: int | None = Field(default=None, ge=1950, le=2100)
    grade_or_percentage: str | None = Field(default=None, max_length=50)
    notes: str | None = None


class EducationResponse(BaseModel):
    id: uuid.UUID
    degree: str
    institution: str
    field_of_study: str | None
    year_of_passing: int | None
    grade_or_percentage: str | None
    notes: str | None

    model_config = {"from_attributes": True}


class WorkExperienceCreate(BaseModel):
    company_name: str = Field(min_length=1, max_length=255)
    designation: str = Field(min_length=1, max_length=200)
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool = False
    location: str | None = Field(default=None, max_length=200)
    last_drawn_salary: str | None = Field(default=None, max_length=50)
    reason_for_leaving: str | None = Field(default=None, max_length=255)
    responsibilities: str | None = None


class WorkExperienceUpdate(BaseModel):
    company_name: str | None = Field(default=None, min_length=1, max_length=255)
    designation: str | None = Field(default=None, min_length=1, max_length=200)
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool | None = None
    location: str | None = Field(default=None, max_length=200)
    last_drawn_salary: str | None = Field(default=None, max_length=50)
    reason_for_leaving: str | None = Field(default=None, max_length=255)
    responsibilities: str | None = None


class WorkExperienceResponse(BaseModel):
    id: uuid.UUID
    company_name: str
    designation: str
    start_date: date | None
    end_date: date | None
    is_current: bool
    location: str | None
    last_drawn_salary: str | None
    reason_for_leaving: str | None
    responsibilities: str | None

    model_config = {"from_attributes": True}


class EmployeeDetailsResponse(BaseModel):
    employee_id: uuid.UUID
    employee_code: str
    first_name: str
    last_name: str
    work_email: str | None
    phone: str | None
    date_of_joining: date | None
    date_of_birth: date | None
    gender: str | None
    marital_status: str | None
    blood_group: str | None
    nationality: str | None
    personal_email: str | None
    father_name: str | None
    emergency_contact_name: str | None
    emergency_contact_phone: str | None
    emergency_contact_relation: str | None
    current_address: str | None
    permanent_address: str | None
    pan_number: str | None
    aadhaar_number: str | None
    passport_number: str | None
    background_verification_status: str | None
    background_verification_notes: str | None
    educations: list[EducationResponse] = []
    work_experiences: list[WorkExperienceResponse] = []
    documents: list[dict] = []
