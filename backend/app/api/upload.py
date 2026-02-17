"""Upload endpoints for ZIP and GitHub."""

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import time
import logging

from app.models.requests import UploadGitHubRequest
from app.models.responses import UploadResponse, UploadMetadata
from app.services.session_service import SessionService
from app.services.file_service import FileService
from app.services.parser_service import ParserService
from app.services.rag_service import RAGService
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/zip", response_model=UploadResponse)
async def upload_zip(file: UploadFile = File(...)):
    """
    Upload ZIP file containing codebase.
    
    - Creates temporary session
    - Extracts and parses code
    - Generates embeddings
    - Stores in vector database
    """
    start_time = time.time()
    
    # Validate file
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Only ZIP files are accepted")
    
    if file.size and file.size > settings.max_file_size:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {settings.max_file_size / (1024*1024):.0f}MB"
        )
    
    session_service = SessionService()
    file_service = FileService()
    parser_service = ParserService()
    rag_service = RAGService()
    
    try:
        # Create session
        session_id = session_service.create_session()
        logger.info(f"Created session {session_id} for ZIP upload")
        
        # Read file content
        file_content = await file.read()
        
        # Extract and get code files
        temp_folder, code_files = await file_service.handle_zip_upload(
            file_content,
            session_id
        )
        
        # Update session
        session_service.update_session(session_id, {
            "status": "parsing",
            "metadata": {
                "upload_type": "zip",
                "filename": file.filename,
                "file_count": len(code_files)
            }
        })
        
        # Parse codebase
        chunks = await parser_service.parse_codebase(code_files, temp_folder)
        
        # Get language statistics
        lang_stats = file_service.get_language_stats(code_files)
        
        # Update session
        session_service.update_session(session_id, {
            "status": "indexing",
            "metadata": {
                "chunk_count": len(chunks),
                **lang_stats
            }
        })
        
        # Index codebase (generate embeddings and store)
        await rag_service.index_codebase(session_id, chunks)
        
        # Final update
        session_service.update_session(session_id, {"status": "ready"})
        
        processing_time = time.time() - start_time
        
        return UploadResponse(
            session_id=session_id,
            message="Codebase uploaded and indexed successfully",
            metadata=UploadMetadata(
                file_count=len(code_files),
                primary_language=lang_stats['primary_language'],
                chunk_count=len(chunks),
                processing_time=round(processing_time, 2),
                languages=lang_stats['languages']
            )
        )
        
    except Exception as e:
        logger.error(f"Error uploading ZIP: {e}", exc_info=True)
        
        # Cleanup on error
        try:
            await file_service.cleanup_temp_files(session_id)
            session_service.delete_session(session_id)
        except:
            pass
        
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/github", response_model=UploadResponse)
async def upload_github(request: UploadGitHubRequest):
    """
    Clone GitHub repository and index it.
    
    - Creates temporary session
    - Clones repository
    - Parses code
    - Generates embeddings
    - Stores in vector database
    """
    start_time = time.time()
    
    session_service = SessionService()
    file_service = FileService()
    parser_service = ParserService()
    rag_service = RAGService()
    
    try:
        # Create session
        session_id = session_service.create_session()
        logger.info(f"Created session {session_id} for GitHub repo: {request.repo_url}")
        
        # Clone repository
        temp_folder, code_files = await file_service.clone_github_repo(
            request.repo_url,
            session_id,
            request.branch
        )
        
        # Extract repo name
        repo_name = request.repo_url.rstrip('/').split('/')[-1].replace('.git', '')
        
        # Update session
        session_service.update_session(session_id, {
            "status": "parsing",
            "metadata": {
                "upload_type": "github",
                "repo_url": request.repo_url,
                "repo_name": repo_name,
                "branch": request.branch,
                "file_count": len(code_files)
            }
        })
        
        # Parse codebase
        chunks = await parser_service.parse_codebase(code_files, temp_folder)
        
        # Get language statistics
        lang_stats = file_service.get_language_stats(code_files)
        
        # Update session
        session_service.update_session(session_id, {
            "status": "indexing",
            "metadata": {
                "chunk_count": len(chunks),
                **lang_stats
            }
        })
        
        # Index codebase
        await rag_service.index_codebase(session_id, chunks)
        
        # Final update
        session_service.update_session(session_id, {"status": "ready"})
        
        processing_time = time.time() - start_time
        
        return UploadResponse(
            session_id=session_id,
            message="Repository cloned and indexed successfully",
            metadata=UploadMetadata(
                file_count=len(code_files),
                primary_language=lang_stats['primary_language'],
                chunk_count=len(chunks),
                processing_time=round(processing_time, 2),
                languages=lang_stats['languages']
            )
        )
        
    except Exception as e:
        logger.error(f"Error cloning GitHub repo: {e}", exc_info=True)
        
        # Cleanup on error
        try:
            await file_service.cleanup_temp_files(session_id)
            session_service.delete_session(session_id)
        except:
            pass
        
        raise HTTPException(status_code=500, detail=str(e))