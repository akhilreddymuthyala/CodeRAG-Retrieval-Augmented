"""Main router registration."""

from fastapi import APIRouter
from app.api import upload, query, session

router = APIRouter()

# Include sub-routers
router.include_router(upload.router, prefix="/upload", tags=["Upload"])
router.include_router(query.router, prefix="/query", tags=["Query"])
router.include_router(session.router, prefix="/session", tags=["Session"])