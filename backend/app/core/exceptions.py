"""Custom exceptions for CodeRAG application."""

from typing import Optional


class CodeRAGException(Exception):
    """Base exception for CodeRAG application."""
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: Optional[str] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)


class InvalidFileException(CodeRAGException):
    """Exception raised for invalid file uploads."""
    
    def __init__(self, message: str = "Invalid file format", details: Optional[str] = None):
        super().__init__(message, status_code=400, details=details)


class SessionNotFoundException(CodeRAGException):
    """Exception raised when session is not found."""
    
    def __init__(self, session_id: str):
        super().__init__(
            message=f"Session not found: {session_id}",
            status_code=404,
            details="Session may have expired or does not exist"
        )


class ParsingException(CodeRAGException):
    """Exception raised during code parsing."""
    
    def __init__(self, message: str = "Code parsing failed", details: Optional[str] = None):
        super().__init__(message, status_code=500, details=details)


class EmbeddingException(CodeRAGException):
    """Exception raised during embedding generation."""
    
    def __init__(self, message: str = "Embedding generation failed", details: Optional[str] = None):
        super().__init__(message, status_code=500, details=details)


class LLMException(CodeRAGException):
    """Exception raised during LLM interaction."""
    
    def __init__(self, message: str = "LLM request failed", details: Optional[str] = None):
        super().__init__(message, status_code=500, details=details)


class VectorDBException(CodeRAGException):
    """Exception raised during vector database operations."""
    
    def __init__(self, message: str = "Vector DB operation failed", details: Optional[str] = None):
        super().__init__(message, status_code=500, details=details)