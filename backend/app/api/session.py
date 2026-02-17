"""Session management endpoints."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging

from app.models.requests import CleanupRequest
from app.models.responses import SessionStatusResponse
from app.services.session_service import SessionService
from app.services.file_service import FileService
from app.services.vector_service import VectorService
from app.core.exceptions import SessionNotFoundException
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/status", response_model=SessionStatusResponse)
async def get_session_status(session_id: str = Query(...)):
    """
    Get status of a session.
    
    - Returns session metadata
    - Shows TTL remaining
    - Indicates if session is ready for queries
    """
    session_service = SessionService()
    
    try:
        session_data = session_service.get_session(session_id)
        
        # Calculate TTL remaining
        created_at = datetime.fromisoformat(session_data['created_at'])
        now = datetime.now()
        elapsed = (now - created_at).total_seconds()
        ttl_remaining = max(0, int(3600 - elapsed))  # Assuming 1 hour TTL
        
        return SessionStatusResponse(
            session_id=session_id,
            status=session_data['status'],
            created_at=datetime.fromisoformat(session_data['created_at']),
            last_activity=datetime.fromisoformat(session_data['last_activity']),
            ttl_remaining=ttl_remaining,
            metadata=session_data.get('metadata', {})
        )
        
    except SessionNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting session status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cleanup")
async def cleanup_session(request: CleanupRequest):
    """
    Manually cleanup a session.
    
    - Deletes temporary files
    - Removes vector database collection
    - Deletes session from Redis
    """
    session_service = SessionService()
    file_service = FileService()
    vector_service = VectorService()
    
    try:
        # Verify session exists
        session_service.get_session(request.session_id)
        
        # Cleanup resources
        await file_service.cleanup_temp_files(request.session_id)
        await vector_service.delete_collection(request.session_id)
        session_service.delete_session(request.session_id)
        
        logger.info(f"Manually cleaned up session: {request.session_id}")
        
        return {
            "status": "success",
            "message": f"Session {request.session_id} cleaned up successfully"
        }
        
    except SessionNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error cleaning up session: {e}")
        raise HTTPException(status_code=500, detail=str(e))