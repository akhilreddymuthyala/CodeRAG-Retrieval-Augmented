"""Session management service with Redis."""

import redis
import json
import uuid
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
import logging

from app.config import settings
from app.core.exceptions import SessionNotFoundException

logger = logging.getLogger(__name__)


class SessionService:
    """Manage user sessions with Redis."""
    
    def __init__(self):
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                password=settings.redis_password if settings.redis_password else None,
                db=settings.redis_db,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            logger.info(f"Redis connected: {settings.redis_host}:{settings.redis_port}")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            logger.error("Make sure Redis is running: redis-server")
            raise
    
    def create_session(self) -> str:
        """Create a new session and return session ID."""
        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        
        session_data = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "temp_folder": f"{settings.temp_folder}/{session_id}",
            "status": "initializing",
            "metadata": {}
        }
        
        # Store in Redis with TTL
        key = f"session:{session_id}"
        try:
            self.redis_client.setex(
                key,
                settings.session_ttl,
                json.dumps(session_data)
            )
            logger.info(f"Created session: {session_id} (TTL: {settings.session_ttl}s)")
        except Exception as e:
            logger.error(f"Failed to create session in Redis: {e}")
            raise
        
        return session_id
    
    def get_session(self, session_id: str) -> Dict[str, Any]:
        """Get session data by ID."""
        key = f"session:{session_id}"
        try:
            data = self.redis_client.get(key)
            
            if not data:
                logger.warning(f"Session not found: {session_id}")
                raise SessionNotFoundException(session_id)
            
            return json.loads(data)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse session data: {e}")
            raise SessionNotFoundException(session_id)
        except redis.RedisError as e:
            logger.error(f"Redis error getting session: {e}")
            raise
    
    def update_session(self, session_id: str, updates: Dict[str, Any]) -> None:
        """Update session data."""
        try:
            session_data = self.get_session(session_id)
            session_data.update(updates)
            session_data["last_activity"] = datetime.now().isoformat()
            
            key = f"session:{session_id}"
            self.redis_client.setex(
                key,
                settings.session_ttl,
                json.dumps(session_data)
            )
            
            logger.debug(f"Updated session: {session_id}")
        except SessionNotFoundException:
            logger.error(f"Cannot update non-existent session: {session_id}")
            raise
        except Exception as e:
            logger.error(f"Failed to update session: {e}")
            raise
    
    def delete_session(self, session_id: str) -> None:
        """Delete session from Redis."""
        key = f"session:{session_id}"
        try:
            result = self.redis_client.delete(key)
            if result:
                logger.info(f"Deleted session: {session_id}")
            else:
                logger.warning(f"Session not found for deletion: {session_id}")
        except Exception as e:
            logger.error(f"Failed to delete session: {e}")
    
    def get_all_sessions(self) -> list:
        """Get all active session IDs."""
        try:
            keys = self.redis_client.keys("session:*")
            return [key.replace("session:", "") for key in keys]
        except Exception as e:
            logger.error(f"Failed to get all sessions: {e}")
            return []
    
    def get_session_ttl(self, session_id: str) -> int:
        """Get remaining TTL for a session in seconds."""
        key = f"session:{session_id}"
        try:
            ttl = self.redis_client.ttl(key)
            return max(0, ttl) if ttl > 0 else 0
        except Exception as e:
            logger.error(f"Failed to get TTL: {e}")
            return 0
    
    async def auto_cleanup_sessions(self):
        """Background task to cleanup inactive sessions."""
        logger.info("Starting auto-cleanup task")
        
        while True:
            try:
                await asyncio.sleep(settings.session_cleanup_interval)
                
                session_ids = self.get_all_sessions()
                current_time = datetime.now()
                cleaned = 0
                
                for session_id in session_ids:
                    try:
                        session_data = self.get_session(session_id)
                        last_activity = datetime.fromisoformat(
                            session_data["last_activity"]
                        )
                        
                        # Check if session is inactive
                        inactive_duration = (current_time - last_activity).total_seconds()
                        
                        if inactive_duration > settings.session_ttl:
                            logger.info(f"Cleaning up inactive session: {session_id}")
                            
                            try:
                                # Import services
                                from app.services.file_service import FileService
                                from app.services.vector_service import VectorService
                                
                                file_service = FileService()
                                vector_service = VectorService()
                                
                                # Cleanup resources
                                await file_service.cleanup_temp_files(session_id)
                                await vector_service.delete_collection(session_id)
                                self.delete_session(session_id)
                                cleaned += 1
                            except Exception as cleanup_error:
                                logger.error(f"Error during cleanup: {cleanup_error}")
                                # Delete session anyway
                                self.delete_session(session_id)
                            
                    except SessionNotFoundException:
                        continue
                    except Exception as e:
                        logger.error(f"Error cleaning up session {session_id}: {e}")
                
                if cleaned > 0:
                    logger.info(f"Cleaned up {cleaned} inactive sessions")
                
            except asyncio.CancelledError:
                logger.info("Auto-cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in auto-cleanup task: {e}")