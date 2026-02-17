"""Request models for API endpoints."""

from pydantic import BaseModel, Field, validator
from typing import Optional


class UploadZipRequest(BaseModel):
    """Request model for ZIP file upload (handled as form data)."""
    pass


class UploadGitHubRequest(BaseModel):
    """Request model for GitHub repository upload."""
    
    repo_url: str = Field(..., description="GitHub repository URL")
    branch: str = Field(default="main", description="Branch to clone")
    
    @validator("repo_url")
    def validate_repo_url(cls, v):
        """Validate GitHub URL format."""
        if not v.startswith(("https://github.com/", "git@github.com:")):
            raise ValueError("Invalid GitHub URL")
        return v


class QueryRequest(BaseModel):
    """Request model for code query."""
    
    session_id: str = Field(..., description="Session identifier")
    question: str = Field(..., min_length=3, max_length=500, description="Question about the code")
    
    @validator("question")
    def validate_question(cls, v):
        """Validate question is not empty."""
        if not v.strip():
            raise ValueError("Question cannot be empty")
        return v.strip()


class CleanupRequest(BaseModel):
    """Request model for manual session cleanup."""
    
    session_id: str = Field(..., description="Session identifier to cleanup")