"""Main FastAPI application entry point."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.api import routes
from app.core.exceptions import CodeRAGException
from app.services.session_service import SessionService
from app.utils.logger import setup_logging
import asyncio


# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("=" * 70)
    logger.info("Starting CodeRAG API server...")
    logger.info(f"OpenRouter Model: {settings.default_model}")
    logger.info(f"Using Local Embeddings: {settings.use_local_embeddings}")
    logger.info("=" * 70)
    
    # Test Redis connection
    try:
        session_service = SessionService()
        session_service.redis_client.ping()
        logger.info("[OK] Redis connection successful")
    except Exception as e:
        logger.error(f"[ERROR] Redis connection failed: {e}")
        logger.error("Please start Redis server!")
        raise
    
    # Start background session cleanup task
    cleanup_task = asyncio.create_task(
        session_service.auto_cleanup_sessions()
    )
    
    yield
    
    # Shutdown
    logger.info("Shutting down CodeRAG API server...")
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass


# Initialize FastAPI app
app = FastAPI(
    title="CodeRAG API",
    description="Retrieval-Augmented Codebase Explainer with OpenRouter",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handler
@app.exception_handler(CodeRAGException)
async def coderag_exception_handler(request: Request, exc: CodeRAGException):
    """Handle custom CodeRAG exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "error": exc.message,
            "details": exc.details
        }
    )


# Include routers
app.include_router(routes.router, prefix="/api")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check Redis
        session_service = SessionService()
        session_service.redis_client.ping()
        redis_status = "connected"
    except Exception as e:
        redis_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "service": "CodeRAG API",
        "version": "1.0.0",
        "redis": redis_status,
        "model": settings.default_model,
        "embeddings": "local" if settings.use_local_embeddings else "openai"
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Welcome to CodeRAG API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "features": {
            "llm_provider": "OpenRouter",
            "embeddings": "Local (FREE)" if settings.use_local_embeddings else "OpenAI",
            "vector_db": "ChromaDB",
            "session_store": "Redis"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=True,
        log_level=settings.log_level.lower()
    )