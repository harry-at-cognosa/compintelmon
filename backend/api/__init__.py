from fastapi import APIRouter

from backend.config import API_URL_PREFIX
from backend.db.schemas import UserRead, UserCreate
from backend.auth.users import fastapi_users, auth_backend

from backend.api.users import router_users
from backend.api.groups import router_groups
from backend.api.settings import router_settings
from backend.api.subjects import router_subjects
from backend.api.sources import router_sources
from backend.api.scheduler import router_scheduler
from backend.api.dashboard import router_dashboard
from backend.api.analyses import router_analyses
from backend.api.conversations import router_conversations
from backend.api.subject_types import router_subject_types
from backend.api.manage_users import router_manage_users

api_router = APIRouter(prefix=API_URL_PREFIX)

# Auth routes from fastapi-users
api_router.include_router(
    fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["Auth"]
)
api_router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate), prefix="/auth", tags=["Auth"]
)

# Application routes
api_router.include_router(router_users, tags=["Users"])
api_router.include_router(router_groups, tags=["Groups"])
api_router.include_router(router_settings, tags=["Settings"])
api_router.include_router(router_subjects, tags=["Subjects"])
api_router.include_router(router_sources, tags=["Sources"])
api_router.include_router(router_scheduler)
api_router.include_router(router_dashboard)
api_router.include_router(router_analyses, tags=["Analyses"])
api_router.include_router(router_conversations, tags=["Conversations"])
api_router.include_router(router_subject_types, tags=["Subject Types"])
api_router.include_router(router_manage_users, tags=["Manage Users"])
