"""API v1 router composition."""

from fastapi import APIRouter

from app.api.v1.audit_logs import router as audit_router
from app.api.v1.auth import router as auth_router
from app.api.v1.evaluations import router as eval_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.resumes import router as resumes_router
from app.api.v1.tasks import router as tasks_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth_router)
api_v1_router.include_router(jobs_router)
api_v1_router.include_router(resumes_router)
api_v1_router.include_router(eval_router)
api_v1_router.include_router(audit_router)
api_v1_router.include_router(tasks_router)

__all__ = ["api_v1_router"]
