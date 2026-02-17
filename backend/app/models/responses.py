"""Response models for API endpoints."""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class CodeSnippet(BaseModel):
    """Model for code snippet in response."""
    
    file: str = Field(..., description="File path")
    lines: str = Field(..., description="Line range (e.g., '10-25')")
    code: str = Field(..., description="Code content")
    language: Optional[str] = Field(None, description="Programming language")


class UploadMetadata(BaseModel):
    """Metadata about uploaded codebase."""
    
    file_count: int
    primary_language: str
    chunk_count: int
    processing_time: float
    languages: Dict[str, int] = Field(default_factory=dict)


class UploadResponse(BaseModel):
    """Response model for upload endpoints."""
    
    status: str = "success"
    session_id: str
    message: str
    metadata: UploadMetadata


class QueryResponse(BaseModel):
    """Response model for query endpoint."""
    
    status: str = "success"
    answer: str
    code_snippets: List[CodeSnippet] = Field(default_factory=list)
    relevant_files: List[str] = Field(default_factory=list)
    processing_time: float
    metadata: Optional[Dict[str, Any]] = None  # ← ADD THIS LINE


class SessionStatusResponse(BaseModel):
    """Response model for session status."""
    
    session_id: str
    status: str
    created_at: datetime
    last_activity: datetime
    ttl_remaining: int
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Response model for errors."""
    
    status: str = "error"
    error: str
    details: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class HealthResponse(BaseModel):
    """Response model for health check."""
    
    status: str
    service: str
    version: str