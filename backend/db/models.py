from datetime import datetime
import enum
import uuid
from typing import TYPE_CHECKING

from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from fastapi_users_db_sqlalchemy.generics import GUID
from sqlalchemy import (
    Boolean, DateTime, Enum, ForeignKey, Integer, VARCHAR,
    CheckConstraint, UniqueConstraint,
    func, text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db import Base


class ApiGroups(Base):
    __tablename__ = "api_groups"

    group_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    deleted: Mapped[int] = mapped_column(Integer, index=True, nullable=False, server_default=text("0"))
    group_name: Mapped[str] = mapped_column(VARCHAR, nullable=False, server_default=text("'Undefined group'"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    api_users_list: Mapped[list["User"]] = relationship("User", back_populates="group")
    group_subjects_list: Mapped[list["GroupSubjects"]] = relationship("GroupSubjects", back_populates="group")
    group_settings_list: Mapped[list["GroupSettings"]] = relationship("GroupSettings", back_populates="group")


class GSubjectTypeEnum(str, enum.Enum):
    company = "company"
    product = "product"
    service = "service"
    topic = "topic"


# Inherits id (UUID), email, hashed_password, is_active, is_superuser, is_verified
class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "api_users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    deleted: Mapped[int] = mapped_column(Integer, index=True, nullable=False, server_default=text("0"))
    group_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("api_groups.group_id", name="fk_api_users_group_id"),
        nullable=False,
        server_default=text("2"),
    )
    user_name: Mapped[str] = mapped_column(VARCHAR(32), nullable=False, unique=True)
    full_name: Mapped[str] = mapped_column(VARCHAR, nullable=False, server_default=text("''"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_groupadmin: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("'FALSE'"))
    is_subjectmanager: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("'FALSE'"))

    group: Mapped["ApiGroups"] = relationship("ApiGroups", back_populates="api_users_list")

    # Override UUID id from primary key to unique (user_id is our real PK)
    if TYPE_CHECKING:
        id: uuid.UUID
    else:
        id: Mapped[uuid.UUID] = mapped_column(GUID, unique=True, default=uuid.uuid4)

    __table_args__ = (
        UniqueConstraint("user_name", name="uq_api_users_user_name"),
        CheckConstraint(
            "char_length(user_name) BETWEEN 3 AND 32 AND user_name ~ '^[a-z0-9_-]+$'",
            name="ck_api_users_user_name_format",
        ),
    )


class ApiSettings(Base):
    __tablename__ = "api_settings"

    name: Mapped[str] = mapped_column(VARCHAR, primary_key=True)
    value: Mapped[str] = mapped_column(VARCHAR, nullable=False)


class GroupSettings(Base):
    __tablename__ = "group_settings"

    group_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("api_groups.group_id", name="fk_group_settings_group_id"),
        primary_key=True,
    )
    name: Mapped[str] = mapped_column(VARCHAR, primary_key=True)
    value: Mapped[str] = mapped_column(VARCHAR, nullable=False)

    group: Mapped["ApiGroups"] = relationship("ApiGroups", back_populates="group_settings_list")


class GroupSubjects(Base):
    __tablename__ = "group_subjects"

    gsubject_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    deleted: Mapped[int] = mapped_column(Integer, index=True, nullable=False, server_default=text("0"))
    group_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("api_groups.group_id", name="fk_group_subjects_group_id"),
        nullable=False,
    )
    gsubject_seqn: Mapped[int] = mapped_column(Integer, nullable=False)
    gsubject_type: Mapped[GSubjectTypeEnum] = mapped_column(
        Enum(GSubjectTypeEnum, name="gsubject_type_enum", create_constraint=False, native_enum=True),
        nullable=False,
    )
    gsubject_name: Mapped[str] = mapped_column(VARCHAR, nullable=False, server_default=text("'No subject name'"))
    gsubject_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    gsubject_status: Mapped[str] = mapped_column(VARCHAR, nullable=False, server_default=text("'warning'"))
    gsubject_status_text: Mapped[str] = mapped_column(VARCHAR, nullable=False, server_default=text("''"))
    gsubject_status_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("'TRUE'"))

    group: Mapped["ApiGroups"] = relationship("ApiGroups", back_populates="group_subjects_list")

    __table_args__ = (
        # Composite index for group_id + sequence
        # (declared via Index in __table_args__ for consistency with the SQL schema)
    )
