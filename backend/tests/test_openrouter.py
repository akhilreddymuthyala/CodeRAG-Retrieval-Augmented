"""
Test script for OpenRouter integration.

Run with: pytest tests/test_openrouter.py -v
"""

import pytest
import os
import logging
from dotenv import load_dotenv

# Setup logger
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


@pytest.mark.asyncio
async def test_openrouter_llm_service():
    """Test OpenRouter LLM service with default model."""
    from app.services.llm_service import OpenRouterLLMService
    
    # Check if API key is set
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key or api_key == "sk-or-v1-your-openrouter-key-here":
        pytest.skip("OPENROUTER_API_KEY not configured")
    
    service = OpenRouterLLMService()
    
    # Test simple query
    code_chunks = [
        {
            "code": "def hello_world():\n    return 'Hello, World!'",
            "metadata": {
                "file_path": "example.py",
                "type": "function",
                "name": "hello_world",
                "language": "python",
                "lines": "1-2"
            }
        }
    ]
    
    print("\n\nTesting with default model...")
    result = await service.generate_explanation(
        "What does this function do?",
        code_chunks
    )
    
    assert result is not None
    assert "answer" in result
    assert result["model_used"] is not None
    
    print(f"✓ Model used: {result['model_used']}")
    print(f"✓ Answer length: {len(result['answer'])} chars")
    print(f"✓ Tokens: {result.get('tokens')}")
    
    # Verify the answer makes sense
    assert len(result['answer']) > 50, "Answer too short"
    assert "hello" in result['answer'].lower() or "greeting" in result['answer'].lower()


@pytest.mark.asyncio
async def test_openrouter_with_fallback():
    """Test OpenRouter with specific model and fallback."""
    from app.services.llm_service import OpenRouterLLMService
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key or api_key == "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":
        pytest.skip("OPENROUTER_API_KEY not configured")
    
    service = OpenRouterLLMService()
    
    code_chunks = [
        {
            "code": "def add(a, b):\n    return a + b",
            "metadata": {
                "file_path": "math.py",
                "type": "function",
                "name": "add",
                "language": "python",
                "lines": "1-2"
            }
        }
    ]
    
    print("\n\nTesting with specific model (GPT-3.5)...")
    result = await service.generate_explanation(
        "Explain this function",
        code_chunks,
        model="openai/gpt-3.5-turbo"
    )
    
    assert result is not None
    assert result["model_used"] == "openai/gpt-3.5-turbo"
    print(f"✓ Successfully used specified model: {result['model_used']}")


@pytest.mark.asyncio
async def test_embedding_service():
    """Test embedding generation using FREE local model (no API key needed)."""
    from app.services.parser_service import CodeChunk
    
    # Try to import local embedding service (FREE)
    try:
        from app.services.embedding_service import LocalEmbeddingService
        service = LocalEmbeddingService()
        logger.info("Using FREE local embedding model (no API key required)")
    except ImportError:
        pytest.skip("sentence-transformers not installed. Run: pip install sentence-transformers")
    
    # Create test chunk
    chunk = CodeChunk(
        id="test_001",
        type="function",
        name="test_func",
        code="def test(): pass",
        file_path="test.py",
        start_line=1,
        end_line=1,
        language="python"
    )
    
    print("\n\nTesting embedding generation with FREE local model...")
    embeddings = await service.generate_embeddings([chunk])
    
    assert len(embeddings) == 1
    assert len(embeddings[0]) > 0
    print(f"✓ Generated embedding with {len(embeddings[0])} dimensions (FREE)")
    
    # Show model info
    model_info = service.get_model_info()
    print(f"✓ Model: {model_info.get('model_name', 'unknown')}")
    print(f"✓ Local: {model_info.get('is_local')}, Free: {model_info.get('is_free')}")


@pytest.mark.asyncio
async def test_get_available_models():
    """Test fetching available models from OpenRouter."""
    from app.services.llm_service import OpenRouterLLMService
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key or api_key == "sk-or-v1-your-openrouter-key-here":
        pytest.skip("OPENROUTER_API_KEY not configured")
    
    service = OpenRouterLLMService()
    
    print("\n\nFetching available models...")
    models = await service.get_available_models()
    
    assert isinstance(models, list)
    assert len(models) > 0
    
    print(f"✓ Found {len(models)} available models")
    print("\nSome popular models:")
    
    # Show first 10 models
    for i, model in enumerate(models[:10], 1):
        model_id = model.get('id', 'Unknown')
        model_name = model.get('name', 'Unknown')
        print(f"  {i}. {model_id}: {model_name}")


@pytest.mark.asyncio
async def test_rag_pipeline():
    """Test complete RAG pipeline with OpenRouter and FREE local embeddings."""
    import tempfile
    import shutil
    from app.services.parser_service import CodeChunk
    
    # Check OpenRouter key
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if not openrouter_key or openrouter_key == "sk-or-v1-your-openrouter-key-here":
        pytest.skip("OPENROUTER_API_KEY not configured")
    
    # Use local embeddings (FREE - no API key needed)
    try:
        from app.services.embedding_service import LocalEmbeddingService
        from app.services.rag_service import RAGService
        from app.services.vector_service import VectorService
        
        # Create RAG service with local embeddings
        class LocalRAGService(RAGService):
            def __init__(self):
                self.embedding_service = LocalEmbeddingService()
                self.vector_service = VectorService()
                from app.services.llm_service import OpenRouterLLMService
                self.llm_service = OpenRouterLLMService()
        
        rag_service = LocalRAGService()
        print("\n\nUsing FREE local embeddings (no OpenAI key needed)")
        
    except ImportError:
        pytest.skip("sentence-transformers not installed. Run: pip install sentence-transformers")
    
    test_session_id = "test_session_001"
    
    # Create test chunks
    chunks = [
        CodeChunk(
            id="chunk_001",
            type="function",
            name="authenticate",
            code="""def authenticate(username, password):
    '''Authenticate user with username and password.'''
    user = get_user(username)
    if user and check_password(password, user.password_hash):
        return create_session(user)
    return None""",
            file_path="auth.py",
            start_line=10,
            end_line=16,
            language="python",
            docstring="Authenticate user with username and password."
        ),
        CodeChunk(
            id="chunk_002",
            type="function",
            name="create_session",
            code="""def create_session(user):
    '''Create a new session for authenticated user.'''
    session_id = generate_session_id()
    sessions[session_id] = {
        'user_id': user.id,
        'created_at': datetime.now()
    }
    return session_id""",
            file_path="session.py",
            start_line=5,
            end_line=12,
            language="python",
            docstring="Create a new session for authenticated user."
        )
    ]
    
    try:
        print("\n\nTesting RAG pipeline indexing with FREE local embeddings...")
        # Index the chunks
        index_result = await rag_service.index_codebase(test_session_id, chunks)
        
        assert index_result["status"] == "success"
        assert index_result["chunks_indexed"] == 2
        print(f"✓ Indexed {index_result['chunks_indexed']} chunks in {index_result['duration']}s (FREE)")
        
        print("\nTesting RAG pipeline query with OpenRouter LLM...")
        # Query the indexed codebase
        query_result = await rag_service.process_query(
            test_session_id,
            "How does the authentication system work?"
        )
        
        assert "answer" in query_result
        assert len(query_result["answer"]) > 50
        assert query_result["model_used"] is not None
        
        print(f"✓ Query processed in {query_result['processing_time']}s")
        print(f"✓ Model used: {query_result['model_used']}")
        print(f"✓ Retrieved {query_result['chunks_retrieved']} relevant chunks")
        print(f"\nAnswer preview: {query_result['answer'][:200]}...")
        
    finally:
        # Cleanup
        from app.services.vector_service import VectorService
        vector_service = VectorService()
        await vector_service.delete_collection(test_session_id)
        print("\n✓ Cleanup completed")


def test_configuration():
    """Test configuration loading."""
    from app.config import settings
    
    print("\n\nTesting configuration...")
    
    # Check required settings
    assert settings.openrouter_api_key is not None
    assert settings.openrouter_base_url == "https://openrouter.ai/api/v1"
    assert settings.default_model is not None
    
    print(f"✓ OpenRouter Base URL: {settings.openrouter_base_url}")
    print(f"✓ Default Model: {settings.default_model}")
    print(f"✓ Embedding Model: {settings.embedding_model}")
    print(f"✓ Fallback Models: {settings.fallback_models_list}")


if __name__ == "__main__":
    """Run tests directly with asyncio."""
    import asyncio
    
    print("=" * 70)
    print("CodeRAG OpenRouter Integration Tests")
    print("=" * 70)
    
    # Run async tests
    async def run_all_tests():
        try:
            print("\n[1/6] Testing configuration...")
            test_configuration()
            
            print("\n[2/6] Testing LLM service...")
            await test_openrouter_llm_service()
            
            print("\n[3/6] Testing LLM with fallback...")
            await test_openrouter_with_fallback()
            
            print("\n[4/6] Testing embedding service...")
            await test_embedding_service()
            
            print("\n[5/6] Testing available models...")
            await test_get_available_models()
            
            print("\n[6/6] Testing complete RAG pipeline...")
            await test_rag_pipeline()
            
            print("\n" + "=" * 70)
            print("✓ All tests passed!")
            print("=" * 70)
            
        except Exception as e:
            print(f"\n✗ Test failed: {e}")
            import traceback
            traceback.print_exc()
    
    asyncio.run(run_all_tests())