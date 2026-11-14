"""Versioned API router."""

from fastapi import APIRouter

from backend.api.auth import router as auth_router
from backend.api.health import router as health_router

router = APIRouter()
router.include_router(health_router)
router.include_router(auth_router)
