"""Query endpoint with OpenRouter model selection support."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging

from app.models.requests import QueryRequest
from app.models.responses import QueryResponse, CodeSnippet
from app.services.session_service import SessionService
from app.services.rag_service import RAGService
from app.core.exceptions import SessionNotFoundException

logger = logging.getLogger(__name__)
router = APIRouter()


class QueryWithModelRequest(QueryRequest):
    """Extended query request with model selection."""
    model: Optional[str] = None


@router.post("/", response_model=QueryResponse)
async def query_codebase(request: QueryWithModelRequest):
    """
    Ask a question about the uploaded codebase.
    
    - Validates session exists
    - Embeds question
    - Retrieves relevant code chunks
    - Generates explanation using LLM via OpenRouter
    - Returns answer with code snippets
    
    Optional: Specify a model with the 'model' field
    Example models:
    - openai/gpt-4
    - openai/gpt-3.5-turbo
    - anthropic/claude-3-opus
    - google/gemini-pro
    """
    session_service = SessionService()
    rag_service = RAGService()
    
    try:
        # Verify session exists and is ready
        session_data = session_service.get_session(request.session_id)
        
        if session_data['status'] != 'ready':
            raise HTTPException(
                status_code=400,
                detail=f"Session is not ready. Current status: {session_data['status']}"
            )
        
        # Update last activity
        session_service.update_session(request.session_id, {})
        
        # Process query through RAG pipeline
        result = await rag_service.process_query(
            request.session_id,
            request.question,
            model=request.model
        )
        
        # Convert to response format
        code_snippets = [
            CodeSnippet(
                file=snippet['file'],
                lines=snippet['lines'],
                code=snippet['code'],
                language=snippet.get('language')
            )
            for snippet in result['code_snippets']
        ]
        
        response = QueryResponse(
            answer=result['answer'],
            code_snippets=code_snippets,
            relevant_files=result['relevant_files'],
            processing_time=result['processing_time']
        )
        
        # Add metadata about model used
        response.metadata = {
            "model_used": result.get('model_used'),
            "tokens": result.get('tokens'),
            "cost": result.get('cost')
        }
        
        return response
        
    except SessionNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
async def get_available_models():
    """
    Get list of available models from OpenRouter.
    
    Returns:
        List of models with metadata (name, pricing, context length, etc.)
    """
    try:
        rag_service = RAGService()
        models = await rag_service.get_available_models()
        
        return {
            "status": "success",
            "models": models,
            "count": len(models)
        }
        
    except Exception as e:
        logger.error(f"Error fetching models: {e}")
        raise HTTPException(status_code=500, detail=str(e))