import uuid
from datetime import datetime

from fastapi_users import schemas
from pydantic import BaseModel, Field, field_validator


# ── User schemas (fastapi-users) ──────────────��───────────────


class UserRead(schemas.BaseUser[uuid.UUID]):
    user_id: int
    group_id: int
    user_name: str
    full_name: str
    is_groupadmin: bool = False
    is_subjectmanager: bool = False
    created_at: datetime | None = None


class UserCreate(schemas.BaseUserCreate):
    user_id: int | None = None
    group_id: int
    user_name: str = Field(..., min_length=3, max_length=32)
    full_name: str = ""
    is_groupadmin: bool = False
    is_subjectmanager: bool = False

    @field_validator("user_name")
    @classmethod
    def validate_user_name(cls, v: str) -> str:
        import re
        v = v.lower()
        if not re.match(r"^[a-z0-9_-]+$", v):
            raise ValueError("user_name must contain only lowercase letters, numbers, underscores, or hyphens")
        return v


class UserUpdate(schemas.BaseUserUpdate):
    user_name: str | None = None
    full_name: str | None = None
    group_id: int | None = None
    is_groupadmin: bool | None = None
    is_subjectmanager: bool | None = None


class UsersMe(BaseModel):
    id: uuid.UUID
    user_id: int
    group_id: int
    group_name: str
    email: str
    user_name: str
    full_name: str
    is_active: bool
    is_superuser: bool
    is_verified: bool
    is_groupadmin: bool
    is_subjectmanager: bool

    class Config:
        from_attributes = True


# ── Group schemas ─────────────────────────────────────────────


class GroupRead(BaseModel):
    group_id: int
    group_name: str
    deleted: int
    created_at: datetime

    class Config:
        from_attributes = True


class GroupCreate(BaseModel):
    group_name: str = Field(..., min_length=1, max_length=200)


class GroupUpdate(BaseModel):
    group_name: str | None = None


# ── Settings schemas ─────────────────────────────���────────────


class SettingRead(BaseModel):
    name: str
    value: str

    class Config:
        from_attributes = True


class SettingUpdate(BaseModel):
    name: str
    value: str


class GroupSettingRead(BaseModel):
    group_id: int
    name: str
    value: str

    class Config:
        from_attributes = True


class GroupSettingUpdate(BaseModel):
    name: str
    value: str


# ── Subject schemas ───────────────────────────────────────────


class SubjectRead(BaseModel):
    gsubject_id: int
    group_id: int
    gsubject_seqn: int
    gsubject_type: str
    gsubject_name: str
    gsubject_status: str
    gsubject_status_text: str
    gsubject_status_updated_at: datetime | None
    gsubject_created_at: datetime
    enabled: bool
    deleted: int

    class Config:
        from_attributes = True


class SubjectCreate(BaseModel):
    gsubject_type: str = Field(..., description="One of: company, product, service, topic")
    gsubject_name: str = Field(..., min_length=1, max_length=200)
    enabled: bool = True


class SubjectUpdate(BaseModel):
    gsubject_name: str | None = None
    gsubject_type: str | None = None
    enabled: bool | None = None
