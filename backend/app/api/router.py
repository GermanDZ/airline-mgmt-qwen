"""API router — mounts sub-routers. Endpoints added per sprint."""

from fastapi import APIRouter

# Sprint 1: auth, users, RBAC
# from app.api.auth import router as auth_router

router = APIRouter(prefix="/api/v1")

# router.include_router(auth_router, prefix="/auth", tags=["auth"])
