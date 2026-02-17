"""RAG orchestration service with OpenRouter integration."""

import time
from typing import List, Dict, Any, Optional
import logging

from app.services.parser_service import CodeChunk
from app.services.embedding_service import EmbeddingService
from app.services.vector_service import VectorService
from app.services.llm_service import OpenRouterLLMService
from app.config import settings

logger = logging.getLogger(__name__)


class RAGService:
    """Orchestrate the RAG pipeline for code explanation with OpenRouter."""
    
    def __init__(self):
        """Initialize all services."""
        self.embedding_service = EmbeddingService()
        self.vector_service = VectorService()
        self.llm_service = OpenRouterLLMService()
    
    async def index_codebase(
        self,
        session_id: str,
        chunks: List[CodeChunk]
    ) -> Dict[str, Any]:
        """
        Index codebase by generating and storing embeddings.
        
        Args:
            session_id: Session identifier
            chunks: List of parsed code chunks
        
        Returns:
            Dictionary with indexing metadata
        """
        logger.info(f"Starting indexing for session {session_id} with {len(chunks)} chunks")
        start_time = time.time()
        
        try:
            # Generate embeddings
            embeddings = await self.embedding_service.generate_embeddings(chunks)
            
            # Create collection
            await self.vector_service.create_collection(session_id)
            
            # Insert embeddings
            await self.vector_service.insert_embeddings(session_id, chunks, embeddings)
            
            duration = time.time() - start_time
            
            result = {
                "session_id": session_id,
                "chunks_indexed": len(chunks),
                "embeddings_generated": len(embeddings),
                "duration": round(duration, 2),
                "status": "success"
            }
            
            logger.info(f"Indexing completed in {duration:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Indexing failed: {e}", exc_info=True)
            raise
    
    async def process_query(
        self,
        session_id: str,
        question: str,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a query through the complete RAG pipeline.
        
        Args:
            session_id: Session identifier
            question: User's question
            model: Optional specific model to use
        
        Returns:
            Dictionary with answer and metadata
        """
        logger.info(f"Processing query for session {session_id}")
        logger.debug(f"Question: {question}")
        
        start_time = time.time()
        
        try:
            # Step 1: Embed the question
            query_embedding = await self.embedding_service.generate_single_embedding(question)
            
            # Step 2: Retrieve relevant chunks
            similar_chunks = await self.vector_service.search_similar(
                session_id,
                query_embedding,
                top_k=settings.max_chunks_per_query
            )
            
            logger.info(f"Retrieved {len(similar_chunks)} relevant code chunks")
            
            # Step 3: Generate answer using LLM (via OpenRouter)
            llm_result = await self.llm_service.generate_explanation(
                question,
                similar_chunks,
                model=model
            )
            
            # Step 4: Extract code snippets and relevant files
            code_snippets = self._extract_code_snippets(similar_chunks)
            relevant_files = list(set(chunk['metadata']['file_path'] for chunk in similar_chunks))
            
            duration = time.time() - start_time
            
            result = {
                "answer": llm_result["answer"],
                "code_snippets": code_snippets,
                "relevant_files": relevant_files,
                "processing_time": round(duration, 2),
                "chunks_retrieved": len(similar_chunks),
                "model_used": llm_result.get("model_used"),
                "tokens": llm_result.get("tokens"),
                "cost": llm_result.get("cost")
            }
            
            logger.info(f"Query processed successfully in {duration:.2f}s")
            logger.info(f"Model used: {result['model_used']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Query processing failed: {e}", exc_info=True)
            raise
    
    def _extract_code_snippets(self, chunks: List[Dict]) -> List[Dict[str, str]]:
        """Extract code snippets from retrieved chunks."""
        snippets = []
        
        for chunk in chunks:
            metadata = chunk['metadata']
            snippets.append({
                "file": metadata['file_path'],
                "lines": metadata['lines'],
                "code": chunk['code'],
                "language": metadata['language'],
                "type": metadata['type'],
                "name": metadata['name']
            })
        
        return snippets
    
    async def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available models from OpenRouter."""
        return await self.llm_service.get_available_models()