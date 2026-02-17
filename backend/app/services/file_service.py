"""File handling service for uploads and extraction."""

import os
import shutil
import zipfile
import tempfile
import aiofiles
from pathlib import Path
from typing import List, Tuple
import logging
from git import Repo
from git.exc import GitCommandError

from app.config import settings
from app.core.exceptions import InvalidFileException

logger = logging.getLogger(__name__)


class FileService:
    """Handle file operations for code uploads."""
    
    SUPPORTED_EXTENSIONS = {
        ".py", ".js", ".jsx", ".ts", ".tsx",
        ".java", ".cpp", ".c", ".h", ".hpp",
        ".go", ".rs", ".rb", ".php", ".cs",
        ".swift", ".kt", ".scala", ".md"
    }
    
    async def handle_zip_upload(self, file_content: bytes, session_id: str) -> Tuple[str, List[str]]:
        """
        Handle ZIP file upload.
        
        Returns:
            Tuple of (temp_folder_path, list_of_code_files)
        """
        temp_folder = f"{settings.temp_folder}/{session_id}"
        
        # Clean up existing folder if it exists
        if os.path.exists(temp_folder):
            logger.warning(f"Cleaning up existing folder: {temp_folder}")
            try:
                shutil.rmtree(temp_folder)
            except Exception as e:
                logger.error(f"Failed to clean up existing folder: {e}")
        
        os.makedirs(temp_folder, exist_ok=True)
        
        try:
            # Save uploaded file temporarily
            temp_zip_path = f"{temp_folder}/upload.zip"
            async with aiofiles.open(temp_zip_path, 'wb') as f:
                await f.write(file_content)
            
            # Extract ZIP
            with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_folder)
            
            # Remove ZIP file after extraction
            os.remove(temp_zip_path)
            
            # Get all code files
            code_files = self.get_all_code_files(temp_folder)
            
            if not code_files:
                raise InvalidFileException(
                    "No code files found in ZIP",
                    "ZIP must contain at least one supported code file"
                )
            
            logger.info(f"Extracted {len(code_files)} code files from ZIP for session {session_id}")
            return temp_folder, code_files
            
        except zipfile.BadZipFile:
            shutil.rmtree(temp_folder, ignore_errors=True)
            raise InvalidFileException("Invalid ZIP file", "File is corrupted or not a ZIP archive")
        except Exception as e:
            shutil.rmtree(temp_folder, ignore_errors=True)
            raise InvalidFileException(f"Error processing ZIP file: {str(e)}")
    
    async def clone_github_repo(self, repo_url: str, session_id: str, branch: str = "main") -> Tuple[str, List[str]]:
        """
        Clone GitHub repository.
        
        Returns:
            Tuple of (temp_folder_path, list_of_code_files)
        """
        temp_folder = f"{settings.temp_folder}/{session_id}"
        
        # CRITICAL: Force cleanup BEFORE doing anything
        # Git will create the directory during clone, so we must ensure it doesn't exist
        if os.path.exists(temp_folder):
            logger.warning(f"Directory already exists, forcing cleanup: {temp_folder}")
            
            max_cleanup_attempts = 5
            for attempt in range(max_cleanup_attempts):
                try:
                    # Method 1: Python shutil with readonly handler
                    def remove_readonly(func, path, _):
                        """Remove readonly attribute and retry."""
                        import stat
                        try:
                            os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
                            func(path)
                        except Exception:
                            pass
                    
                    shutil.rmtree(temp_folder, onerror=remove_readonly)
                    
                    # Double check with Windows command
                    if os.path.exists(temp_folder):
                        import subprocess
                        subprocess.run(
                            ['cmd', '/c', 'rmdir', '/S', '/Q', temp_folder],
                            capture_output=True
                        )
                    
                    # Wait for filesystem
                    import time
                    time.sleep(0.3)
                    
                    # Check if really gone
                    if not os.path.exists(temp_folder):
                        logger.info(f"Cleanup successful after {attempt + 1} attempts")
                        break
                    
                except Exception as e:
                    logger.debug(f"Cleanup attempt {attempt + 1} error: {e}")
                
                # Wait before retry
                if attempt < max_cleanup_attempts - 1:
                    import time
                    time.sleep(0.5)
            
            # Final check
            if os.path.exists(temp_folder):
                logger.error(f"Could not remove directory after {max_cleanup_attempts} attempts")
                # Use alternative unique path
                import uuid
                temp_folder = f"{settings.temp_folder}/{session_id}_{uuid.uuid4().hex[:8]}"
                logger.info(f"Using alternative path: {temp_folder}")
        
        # DO NOT create directory - let Git create it during clone!
        # Ensure parent directory exists
        parent_dir = os.path.dirname(temp_folder)
        os.makedirs(parent_dir, exist_ok=True)
        logger.info(f"Target clone path: {temp_folder}")
        
        try:
            # Clone repository - Git will create the directory
            logger.info(f"Cloning repository: {repo_url} (branch: {branch})")
            
            try:
                Repo.clone_from(
                    repo_url, 
                    temp_folder, 
                    branch=branch, 
                    depth=1,
                    single_branch=True
                )
                logger.info(f"Repository cloned successfully to {temp_folder}")
                
            except GitCommandError as e:
                # If branch doesn't exist, try 'master'
                if branch == "main" and ("not found" in str(e).lower() or "couldn't find remote ref" in str(e).lower()):
                    logger.warning(f"Branch 'main' not found, trying 'master'")
                    
                    # Clean up failed attempt
                    if os.path.exists(temp_folder):
                        shutil.rmtree(temp_folder, ignore_errors=True)
                    
                    branch = "master"
                    Repo.clone_from(
                        repo_url, 
                        temp_folder, 
                        branch=branch, 
                        depth=1,
                        single_branch=True
                    )
                    logger.info(f"Repository cloned successfully using branch: {branch}")
                else:
                    raise
            
            # Get all code files
            code_files = self.get_all_code_files(temp_folder)
            
            if not code_files:
                raise InvalidFileException(
                    "No code files found in repository",
                    "Repository must contain at least one supported code file"
                )
            
            logger.info(f"Found {len(code_files)} code files in repository")
            return temp_folder, code_files
            
        except GitCommandError as e:
            # Cleanup on error
            try:
                if os.path.exists(temp_folder):
                    shutil.rmtree(temp_folder, ignore_errors=True)
            except:
                pass
            
            # Parse git error for user-friendly message
            error_msg = str(e)
            
            if "already exists and is not an empty directory" in error_msg.lower():
                raise InvalidFileException(
                    "Directory conflict - please try again",
                    "The temporary directory could not be cleaned. Try uploading again."
                )
            elif "not found" in error_msg.lower() or "repository not found" in error_msg.lower():
                raise InvalidFileException(
                    "Repository not found",
                    "Please check the repository URL and ensure it's public"
                )
            elif "authentication" in error_msg.lower() or "could not read" in error_msg.lower():
                raise InvalidFileException(
                    "Access denied",
                    "This appears to be a private repository. Please use a public repository"
                )
            else:
                # Return first 300 chars of error
                raise InvalidFileException(
                    "Git clone failed",
                    error_msg[:300]
                )
                
        except Exception as e:
            # Cleanup on error
            try:
                if os.path.exists(temp_folder):
                    shutil.rmtree(temp_folder, ignore_errors=True)
            except:
                pass
            
            raise InvalidFileException(
                "Error cloning repository",
                str(e)[:300]
            )
    
    def get_all_code_files(self, directory: str) -> List[str]:
        """
        Recursively get all code files from directory.
        
        Returns:
            List of absolute file paths
        """
        code_files = []
        
        for root, dirs, files in os.walk(directory):
            # Skip common non-code directories
            dirs[:] = [d for d in dirs if d not in {
                '.git', '.svn', 'node_modules', '__pycache__',
                '.venv', 'venv', 'env', 'build', 'dist', 
                '.idea', '.vscode', 'target', 'bin', 'obj'
            }]
            
            for file in files:
                file_path = Path(root) / file
                if file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                    # Skip very large files (>1MB)
                    try:
                        if file_path.stat().st_size > 1048576:  # 1MB
                            logger.warning(f"Skipping large file: {file_path}")
                            continue
                    except Exception:
                        pass
                    
                    code_files.append(str(file_path))
        
        return code_files
    
    async def cleanup_temp_files(self, session_id: str) -> None:
        """Delete temporary files for a session."""
        temp_folder = f"{settings.temp_folder}/{session_id}"
        
        try:
            if os.path.exists(temp_folder):
                # Force remove read-only files (Windows issue with .git)
                def remove_readonly(func, path, _):
                    """Clear the readonly bit and reattempt the removal."""
                    os.chmod(path, 0o777)
                    func(path)
                
                shutil.rmtree(temp_folder, onerror=remove_readonly)
                logger.info(f"Cleaned up temp files for session: {session_id}")
        except Exception as e:
            logger.error(f"Error cleaning up temp files for session {session_id}: {e}")
            # Try force delete on Windows
            if os.name == 'nt':
                try:
                    os.system(f'rmdir /S /Q "{temp_folder}"')
                except Exception:
                    pass
    
    def get_language_stats(self, file_paths: List[str]) -> dict:
        """Get statistics about programming languages in codebase."""
        lang_count = {}
        
        ext_to_lang = {
            ".py": "Python",
            ".js": "JavaScript",
            ".jsx": "JavaScript",
            ".ts": "TypeScript",
            ".tsx": "TypeScript",
            ".java": "Java",
            ".cpp": "C++",
            ".c": "C",
            ".go": "Go",
            ".rs": "Rust",
            ".rb": "Ruby",
            ".php": "PHP",
            ".cs": "C#",
            ".swift": "Swift",
            ".kt": "Kotlin",
            ".scala": "Scala",
        }
        
        for file_path in file_paths:
            ext = Path(file_path).suffix.lower()
            lang = ext_to_lang.get(ext, "Other")
            lang_count[lang] = lang_count.get(lang, 0) + 1
        
        # Determine primary language
        primary_lang = max(lang_count.items(), key=lambda x: x[1])[0] if lang_count else "Unknown"
        
        return {
            "primary_language": primary_lang,
            "languages": lang_count
        }