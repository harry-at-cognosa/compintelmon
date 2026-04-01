from fastapi import APIRouter

from backend.config import API_URL_PREFIX
from backend.db.schemas import UserRead, UserCreate
from backend.auth.users import fastapi_users, auth_backend

from backend.api.users import router_users
from backend.api.groups import router_groups
from backend.api.settings import router_settings
from backend.api.subjects import router_subjects

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
