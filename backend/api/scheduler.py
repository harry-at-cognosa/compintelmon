from fastapi import APIRouter, Depends, HTTPException, status

from backend.db.models import User
from backend.auth.users import current_active_user
from backend.services.scheduler_service import scheduler
from backend.db.schemas import SchedulerStatusResponse

router_scheduler = APIRouter(prefix="/scheduler", tags=["Scheduler"])


def _require_superuser(user: User):
    if not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superuser required")


@router_scheduler.post("/start", response_model=SchedulerStatusResponse)
async def start_scheduler(user: User = Depends(current_active_user)):
    _require_superuser(user)
    scheduler.start()
    return SchedulerStatusResponse(running=scheduler.is_running, next_check_time=scheduler.next_check_time)


@router_scheduler.post("/stop", response_model=SchedulerStatusResponse)
async def stop_scheduler(user: User = Depends(current_active_user)):
    _require_superuser(user)
    scheduler.stop()
    return SchedulerStatusResponse(running=scheduler.is_running, next_check_time=None)


@router_scheduler.get("/status", response_model=SchedulerStatusResponse)
async def get_scheduler_status(user: User = Depends(current_active_user)):
    return SchedulerStatusResponse(running=scheduler.is_running, next_check_time=scheduler.next_check_time)
