"""Configuration management for CodeRAG application with OpenRouter support."""

from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra='ignore'  # Ignore extra fields in .env
    )
    
    # OpenRouter API Configuration
    openrouter_api_key: str
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_app_name: str = "CodeRAG"
    openrouter_app_url: str = "http://localhost:3000"
    
    # OpenAI API Key (OPTIONAL - only if using OpenAI embeddings)
    openai_api_key: Optional[str] = None
    
    # Local Embeddings Configuration
    use_local_embeddings: bool = True  # Default to FREE local embeddings
    local_embedding_model: str = "all-MiniLM-L6-v2"
    
    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db: int = 0
    
    # ChromaDB
    chroma_persist_directory: str = "./chroma_db"
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    
    # Session
    session_ttl: int = 3600
    session_cleanup_interval: int = 300
    temp_folder: str = "/tmp/coderag_sessions"
    
    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    cors_origins: str = "http://localhost:3000"
    
    # Model Configuration
    default_model: str = "google/gemini-flash-1.5"  # FREE model
    fallback_models: str = "google/gemini-pro,meta-llama/llama-3-8b-instruct"
    embedding_model: str = "text-embedding-3-small"  # Only used if openai_api_key provided
    max_tokens: int = 4096
    temperature: float = 0.3
    
    # Limits
    max_file_size: int = 104857600  # 100MB
    max_chunk_size: int = 1000
    max_chunks_per_query: int = 5
    max_concurrent_uploads: int = 5
    
    # Retry Configuration
    max_retries: int = 3
    retry_delay: int = 2
    enable_fallback: bool = True
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/app.log"
    log_openrouter_requests: bool = True
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    @property
    def fallback_models_list(self) -> List[str]:
        """Parse fallback models from comma-separated string."""
        if not self.fallback_models:
            return []
        return [model.strip() for model in self.fallback_models.split(",")]
    
    def ensure_directories(self):
        """Create necessary directories if they don't exist."""
        os.makedirs(self.temp_folder, exist_ok=True)
        os.makedirs(self.chroma_persist_directory, exist_ok=True)
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)


# Global settings instance
settings = Settings()
settings.ensure_directories()