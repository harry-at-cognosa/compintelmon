from datetime import datetime
import enum
import uuid
from typing import TYPE_CHECKING

from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from fastapi_users_db_sqlalchemy.generics import GUID
from sqlalchemy import (
    Boolean, DateTime, Enum, ForeignKey, Index, Integer, JSON, Text, VARCHAR,
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
    sources_list: Mapped[list["SubjectSources"]] = relationship("SubjectSources", back_populates="subject")

    __table_args__ = (
        # Composite index for group_id + sequence
        # (declared via Index in __table_args__ for consistency with the SQL schema)
    )


class PlaybookTemplates(Base):
    __tablename__ = "playbook_templates"

    template_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subject_type: Mapped[GSubjectTypeEnum] = mapped_column(
        Enum(GSubjectTypeEnum, name="gsubject_type_enum", create_constraint=False, native_enum=True),
        nullable=False,
    )
    category_key: Mapped[str] = mapped_column(VARCHAR(64), nullable=False)
    category_name: Mapped[str] = mapped_column(VARCHAR(128), nullable=False)
    category_group: Mapped[str] = mapped_column(VARCHAR(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    default_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("'TRUE'"))
    default_frequency_minutes: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("360"))
    collection_tool: Mapped[str] = mapped_column(VARCHAR(32), nullable=False)
    collection_config: Mapped[dict] = mapped_column(JSON, nullable=False, server_default=text("'{}'"))
    signal_instructions: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    user_inputs_schema: Mapped[dict] = mapped_column(JSON, nullable=False, server_default=text("'{}'"))
    priority: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("subject_type", "category_key", name="uq_playbook_subject_type_category"),
    )


class SubjectSources(Base):
    __tablename__ = "subject_sources"

    source_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    gsubject_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("group_subjects.gsubject_id", name="fk_subject_sources_gsubject_id"),
        nullable=False,
    )
    template_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("playbook_templates.template_id", name="fk_subject_sources_template_id"),
        nullable=True,
    )
    category_key: Mapped[str] = mapped_column(VARCHAR(64), nullable=False)
    category_name: Mapped[str] = mapped_column(VARCHAR(128), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("'TRUE'"))
    frequency_minutes: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("360"))
    collection_tool: Mapped[str] = mapped_column(VARCHAR(32), nullable=False)
    collection_config: Mapped[dict] = mapped_column(JSON, nullable=False, server_default=text("'{}'"))
    signal_instructions: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    user_inputs: Mapped[dict] = mapped_column(JSON, nullable=False, server_default=text("'{}'"))
    last_collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_status: Mapped[str] = mapped_column(VARCHAR(32), nullable=False, server_default=text("'pending'"))
    last_status_text: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    deleted: Mapped[int] = mapped_column(Integer, index=True, nullable=False, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    subject: Mapped["GroupSubjects"] = relationship("GroupSubjects", back_populates="sources_list")
    template: Mapped["PlaybookTemplates | None"] = relationship("PlaybookTemplates")

    __table_args__ = (
        Index("ix_subject_sources_gsubject_deleted", "gsubject_id", "deleted"),
    )


class SubjectSourceRuns(Base):
    __tablename__ = "subject_source_runs"

    run_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("subject_sources.source_id", name="fk_source_runs_source_id"),
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(VARCHAR(32), nullable=False, server_default=text("'pending'"))
    items_collected: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_hash: Mapped[str | None] = mapped_column(VARCHAR(64), nullable=True)

    source: Mapped["SubjectSources"] = relationship("SubjectSources")

    __table_args__ = (
        Index("ix_source_runs_source_started", "source_id", "started_at"),
    )


class Analyses(Base):
    __tablename__ = "analyses"

    analysis_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    gsubject_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("group_subjects.gsubject_id", name="fk_analyses_gsubject_id"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    analysis_type: Mapped[str] = mapped_column(VARCHAR(32), nullable=False, server_default=text("'full'"))
    summary: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    key_findings: Mapped[dict] = mapped_column(JSON, nullable=False, server_default=text("'[]'"))
    signals: Mapped[dict] = mapped_column(JSON, nullable=False, server_default=text("'[]'"))
    raw_analysis: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    sources_analyzed: Mapped[dict] = mapped_column(JSON, nullable=False, server_default=text("'[]'"))
    status: Mapped[str] = mapped_column(VARCHAR(32), nullable=False, server_default=text("'pending'"))
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    subject: Mapped["GroupSubjects"] = relationship("GroupSubjects")

    __table_args__ = (
        Index("ix_analyses_gsubject_created", "gsubject_id", "created_at"),
    )


class Reports(Base):
    __tablename__ = "reports"

    report_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analysis_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("analyses.analysis_id", name="fk_reports_analysis_id"),
        nullable=False,
    )
    gsubject_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("group_subjects.gsubject_id", name="fk_reports_gsubject_id"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    report_type: Mapped[str] = mapped_column(VARCHAR(32), nullable=False, server_default=text("'battlecard'"))
    title: Mapped[str] = mapped_column(VARCHAR(256), nullable=False, server_default=text("''"))
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    status: Mapped[str] = mapped_column(VARCHAR(32), nullable=False, server_default=text("'pending'"))
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    analysis: Mapped["Analyses"] = relationship("Analyses")
    subject: Mapped["GroupSubjects"] = relationship("GroupSubjects")

    __table_args__ = (
        Index("ix_reports_gsubject_created", "gsubject_id", "created_at"),
    )
