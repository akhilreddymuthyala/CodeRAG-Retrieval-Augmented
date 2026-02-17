"""Embedding generation service using local sentence-transformers (FREE - no API key needed)."""

import numpy as np
from typing import List
import logging
from sentence_transformers import SentenceTransformer

from app.config import settings
from app.core.exceptions import EmbeddingException
from app.services.parser_service import CodeChunk

logger = logging.getLogger(__name__)


class LocalEmbeddingService:
    """
    Generate embeddings for code chunks using FREE local models.
    
    Uses sentence-transformers library - completely free, no API key required!
    Models run locally on your machine.
    """
    
    def __init__(self):
        """Initialize local embedding model."""
        # Use a smaller, faster model for code
        # Options:
        # - 'all-MiniLM-L6-v2' (fast, 384 dimensions) - DEFAULT
        # - 'all-mpnet-base-v2' (better quality, 768 dimensions)
        # - 'paraphrase-MiniLM-L6-v2' (optimized for similarity)
        
        model_name = getattr(settings, 'local_embedding_model', 'all-MiniLM-L6-v2')
        
        logger.info(f"Loading local embedding model: {model_name}")
        logger.info("This is FREE and runs on your computer - no API key needed!")
        
        try:
            self.model = SentenceTransformer(model_name)
            logger.info(f"[OK] Model loaded successfully! Dimension: {self.model.get_sentence_embedding_dimension()}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise EmbeddingException(f"Failed to initialize local embedding model: {str(e)}")
        
        self.batch_size = 32
    
    async def generate_embeddings(self, chunks: List[CodeChunk]) -> List[np.ndarray]:
        """
        Generate embeddings for code chunks using local model.
        
        Args:
            chunks: List of CodeChunk objects
        
        Returns:
            List of embedding vectors (numpy arrays)
        """
        if not chunks:
            return []
        
        logger.info(f"Generating embeddings for {len(chunks)} chunks using LOCAL model (FREE)")
        
        try:
            # Prepare texts with context
            texts = [chunk.get_context_text() for chunk in chunks]
            
            # Truncate if too long (most models support ~512 tokens)
            texts = [text[:2000] for text in texts]
            
            # Generate embeddings (synchronous, but fast)
            # sentence-transformers handles batching automatically
            embeddings = self.model.encode(
                texts,
                batch_size=self.batch_size,
                show_progress_bar=False,
                convert_to_numpy=True
            )
            
            # Convert to list of arrays
            embeddings_list = [emb for emb in embeddings]
            
            logger.info(f"✓ Generated {len(embeddings_list)} embeddings successfully (FREE)")
            return embeddings_list
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise EmbeddingException(f"Failed to generate embeddings: {str(e)}")
    
    async def generate_single_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for a single text (e.g., query)."""
        try:
            # Truncate if too long
            text = text[:2000]
            
            # Generate embedding
            embedding = self.model.encode(
                text,
                convert_to_numpy=True
            )
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise EmbeddingException(f"Failed to generate embedding: {str(e)}")
    
    @staticmethod
    def normalize_embeddings(embeddings: List[np.ndarray]) -> List[np.ndarray]:
        """Normalize embeddings to unit length."""
        return [emb / np.linalg.norm(emb) for emb in embeddings]
    
    @staticmethod
    def cosine_similarity(emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Calculate cosine similarity between two embeddings."""
        return np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
    
    def get_model_info(self) -> dict:
        """Get information about the loaded model."""
        return {
            "model_name": self.model._model_name if hasattr(self.model, '_model_name') else "unknown",
            "embedding_dimension": self.model.get_sentence_embedding_dimension(),
            "max_seq_length": self.model.max_seq_length,
            "is_local": True,
            "is_free": True,
            "requires_api_key": False
        }


# Alias for backward compatibility
EmbeddingService = LocalEmbeddingService