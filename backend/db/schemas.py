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
    is_active: bool
    deleted: int
    created_at: datetime

    class Config:
        from_attributes = True


class GroupCreate(BaseModel):
    group_name: str = Field(..., min_length=1, max_length=200)


class GroupUpdate(BaseModel):
    group_name: str | None = None
    is_active: bool | None = None


# ── User management schemas ──────────────────────────────────


class UserManageRead(BaseModel):
    user_id: int
    user_name: str
    full_name: str
    email: str
    group_id: int
    is_active: bool
    is_superuser: bool
    is_groupadmin: bool
    is_subjectmanager: bool
    is_verified: bool
    created_at: datetime | None
    last_seen: datetime | None

    class Config:
        from_attributes = True


class UserManageCreate(BaseModel):
    user_name: str = Field(..., min_length=3, max_length=32)
    full_name: str = ""
    email: str = Field(..., min_length=5)
    password: str = Field(..., min_length=4)
    group_id: int
    is_active: bool = True
    is_superuser: bool = False
    is_groupadmin: bool = False
    is_subjectmanager: bool = False


class UserManageUpdate(BaseModel):
    full_name: str | None = None
    email: str | None = None
    group_id: int | None = None
    is_active: bool | None = None
    is_superuser: bool | None = None
    is_groupadmin: bool | None = None
    is_subjectmanager: bool | None = None


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


class SubjectReadWithSources(SubjectRead):
    sources_provisioned: int = 0


# ── Playbook template schemas ────────────────────────────────


class SubjectTypeRead(BaseModel):
    subj_type_id: int
    subj_type_name: str
    subj_type_desc: str
    subj_type_enabled: bool

    class Config:
        from_attributes = True


class SubjectTypeCreate(BaseModel):
    subj_type_name: str = Field(..., min_length=1, max_length=64)
    subj_type_desc: str = ""
    subj_type_enabled: bool = True


class SubjectTypeUpdate(BaseModel):
    subj_type_name: str | None = None
    subj_type_desc: str | None = None
    subj_type_enabled: bool | None = None


class PlaybookTemplateRead(BaseModel):
    template_id: int
    subject_type_id: int
    subject_type: str
    category_key: str
    category_name: str
    category_group: str
    description: str
    default_enabled: bool
    default_frequency_minutes: int
    collection_tool: str
    collection_config: dict
    signal_instructions: str
    user_inputs_schema: dict
    priority: int
    version: int

    class Config:
        from_attributes = True


class PlaybookTemplateCreate(BaseModel):
    subject_type_id: int
    category_key: str = Field(..., max_length=64)
    category_name: str = Field(..., max_length=128)
    category_group: str = Field(..., max_length=64)
    description: str = ""
    default_enabled: bool = True
    default_frequency_minutes: int = 360
    collection_tool: str = Field(..., max_length=32)
    collection_config: dict = {}
    signal_instructions: str = ""
    user_inputs_schema: dict = {}
    priority: int = 0


class PlaybookTemplateUpdate(BaseModel):
    category_key: str | None = None
    category_name: str | None = None
    category_group: str | None = None
    description: str | None = None
    default_enabled: bool | None = None
    default_frequency_minutes: int | None = None
    collection_tool: str | None = None
    collection_config: dict | None = None
    signal_instructions: str | None = None
    user_inputs_schema: dict | None = None
    priority: int | None = None


class PlaybookTemplateClone(BaseModel):
    target_subject_type_id: int
    new_category_key: str | None = None


# ── Subject source schemas ────────────────────────────────────


class SubjectSourceRead(BaseModel):
    source_id: int
    gsubject_id: int
    template_id: int | None
    category_key: str
    category_name: str
    enabled: bool
    frequency_minutes: int
    collection_tool: str
    collection_config: dict
    signal_instructions: str
    user_inputs: dict
    last_collected_at: datetime | None
    last_status: str
    last_status_text: str
    created_at: datetime

    class Config:
        from_attributes = True


class SubjectSourceUpdate(BaseModel):
    enabled: bool | None = None
    frequency_minutes: int | None = None
    user_inputs: dict | None = None


class SubjectSourceCreate(BaseModel):
    category_key: str = Field(..., max_length=64)
    category_name: str = Field(..., max_length=128)
    enabled: bool = True
    frequency_minutes: int = 360
    collection_tool: str = "crawl4ai"
    collection_config: dict = {}
    signal_instructions: str = ""
    user_inputs: dict = {}


# ── Collection run schemas ────────────────────────────────────


class SubjectSourceRunRead(BaseModel):
    run_id: int
    source_id: int
    started_at: datetime
    finished_at: datetime | None
    status: str
    items_collected: int
    error_detail: str | None
    data_hash: str | None

    class Config:
        from_attributes = True


class CollectResponse(BaseModel):
    run_id: int
    status: str
    message: str


class CollectAllResponse(BaseModel):
    runs: list[CollectResponse]
    message: str


# ── Discovery schemas ─────────────────────────────────────────


class DiscoverResponse(BaseModel):
    status: str
    message: str


# ── Scheduler schemas ─────────────────────────────────────────


class SchedulerStatusResponse(BaseModel):
    running: bool
    next_check_time: datetime | None


# ── Dashboard schemas ─────────────────────────────────────────


class DashboardStats(BaseModel):
    total_subjects: int
    total_enabled_sources: int
    sources_due: int
    scheduler_running: bool


class RecentRunRead(BaseModel):
    run_id: int
    subject_name: str
    source_name: str
    status: str
    started_at: datetime


# ── Analysis schemas ──────────────────────────────────────────


class AnalysisRead(BaseModel):
    analysis_id: int
    gsubject_id: int
    created_at: datetime
    analysis_type: str
    summary: str
    key_findings: list
    signals: list
    sources_analyzed: list
    status: str
    error_detail: str | None
    archived: bool = False

    class Config:
        from_attributes = True


class AnalyzeResponse(BaseModel):
    analysis_id: int
    status: str
    message: str


# ── Report schemas ────────────────────────────────────────────


class ReportRead(BaseModel):
    report_id: int
    analysis_id: int
    gsubject_id: int
    created_at: datetime
    report_type: str
    title: str
    content_markdown: str
    status: str
    error_detail: str | None
    archived: bool = False

    class Config:
        from_attributes = True


class GenerateReportRequest(BaseModel):
    report_type: str = "battlecard"


class GenerateReportResponse(BaseModel):
    report_id: int
    status: str
    message: str


# ── Conversation schemas ──────────────────────────────────────


class ConversationRead(BaseModel):
    conversation_id: int
    gsubject_id: int
    user_id: int
    conversation_type: str
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationCreate(BaseModel):
    conversation_type: str = Field(..., pattern=r"^(update|query)$")
    title: str = ""


class ConversationMessageRead(BaseModel):
    message_id: int
    conversation_id: int
    role: str
    content: str
    message_type: str
    metadata_json: dict
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)


class SendMessageResponse(BaseModel):
    message_id: int
    status: str
    message: str
