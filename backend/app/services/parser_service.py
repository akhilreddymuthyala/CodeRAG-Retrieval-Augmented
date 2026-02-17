"""Code parsing service using AST for different languages."""

import ast
import os
from pathlib import Path
from typing import List, Dict, Any
import logging

from app.config import settings
from app.core.exceptions import ParsingException

logger = logging.getLogger(__name__)


class CodeChunk:
    """Represents a parsed code chunk."""
    
    def __init__(
        self,
        id: str,
        type: str,
        name: str,
        code: str,
        file_path: str,
        start_line: int,
        end_line: int,
        language: str,
        docstring: str = "",
        imports: List[str] = None
    ):
        self.id = id
        self.type = type  # function, class, module
        self.name = name
        self.code = code
        self.file_path = file_path
        self.start_line = start_line
        self.end_line = end_line
        self.language = language
        self.docstring = docstring
        self.imports = imports or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "code": self.code,
            "file_path": self.file_path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "language": self.language,
            "docstring": self.docstring,
            "imports": self.imports
        }
    
    def get_context_text(self) -> str:
        """Get text representation with context for embedding."""
        context_parts = [
            f"File: {self.file_path}",
            f"Language: {self.language}",
            f"{self.type.capitalize()}: {self.name}",
        ]
        
        if self.docstring:
            context_parts.append(f"Documentation: {self.docstring}")
        
        context_parts.append(f"Code:\n{self.code}")
        
        return "\n".join(context_parts)


class ParserService:
    """Parse code files into chunks."""
    
    def __init__(self):
        self.chunk_counter = 0
    
    async def parse_codebase(self, file_paths: List[str], base_path: str) -> List[CodeChunk]:
        """
        Parse all code files in codebase.
        
        Args:
            file_paths: List of absolute file paths
            base_path: Base directory path for relative paths
        
        Returns:
            List of CodeChunk objects
        """
        all_chunks = []
        
        for file_path in file_paths:
            try:
                chunks = await self.parse_file(file_path, base_path)
                all_chunks.extend(chunks)
            except Exception as e:
                logger.warning(f"Failed to parse {file_path}: {e}")
                continue
        
        logger.info(f"Parsed {len(all_chunks)} chunks from {len(file_paths)} files")
        return all_chunks
    
    async def parse_file(self, file_path: str, base_path: str) -> List[CodeChunk]:
        """Parse a single file based on its extension."""
        ext = Path(file_path).suffix.lower()
        
        parsers = {
            ".py": self.parse_python_file,
            ".js": self.parse_javascript_file,
            ".jsx": self.parse_javascript_file,
            ".ts": self.parse_javascript_file,
            ".tsx": self.parse_javascript_file,
        }
        
        parser = parsers.get(ext, self.parse_generic_file)
        return await parser(file_path, base_path)
    
    async def parse_python_file(self, file_path: str, base_path: str) -> List[CodeChunk]:
        """Parse Python file using AST."""
        chunks = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
            
            tree = ast.parse(content)
            relative_path = os.path.relpath(file_path, base_path)
            
            # Parse module-level code
            module_chunk = self._create_chunk(
                type="module",
                name=Path(file_path).stem,
                code=content[:min(1000, len(content))],  # First 1000 chars
                file_path=relative_path,
                start_line=1,
                end_line=len(lines),
                language="python"
            )
            chunks.append(module_chunk)
            
            # Parse functions and classes
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    chunks.append(self._parse_python_function(node, lines, relative_path))
                elif isinstance(node, ast.ClassDef):
                    chunks.append(self._parse_python_class(node, lines, relative_path))
            
        except SyntaxError as e:
            logger.warning(f"Syntax error in {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error parsing Python file {file_path}: {e}")
        
        return chunks
    
    def _parse_python_function(self, node: ast.FunctionDef, lines: List[str], file_path: str) -> CodeChunk:
        """Parse Python function node."""
        start_line = node.lineno
        end_line = node.end_lineno or start_line
        
        code_lines = lines[start_line - 1:end_line]
        code = "\n".join(code_lines)
        
        # Extract docstring
        docstring = ast.get_docstring(node) or ""
        
        return self._create_chunk(
            type="function",
            name=node.name,
            code=code,
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            language="python",
            docstring=docstring
        )
    
    def _parse_python_class(self, node: ast.ClassDef, lines: List[str], file_path: str) -> CodeChunk:
        """Parse Python class node."""
        start_line = node.lineno
        end_line = node.end_lineno or start_line
        
        code_lines = lines[start_line - 1:end_line]
        code = "\n".join(code_lines)
        
        # Extract docstring
        docstring = ast.get_docstring(node) or ""
        
        return self._create_chunk(
            type="class",
            name=node.name,
            code=code,
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            language="python",
            docstring=docstring
        )
    
    async def parse_javascript_file(self, file_path: str, base_path: str) -> List[CodeChunk]:
        """Parse JavaScript/TypeScript file (simplified without tree-sitter)."""
        chunks = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
            
            relative_path = os.path.relpath(file_path, base_path)
            language = "typescript" if file_path.endswith(('.ts', '.tsx')) else "javascript"
            
            # Simple regex-based parsing for functions
            # Note: In production, use tree-sitter for proper parsing
            import re
            
            # Match function declarations
            func_pattern = r'(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\([^)]*\)\s*{'
            matches = re.finditer(func_pattern, content)
            
            for match in matches:
                func_name = match.group(1)
                start_pos = match.start()
                start_line = content[:start_pos].count('\n') + 1
                
                # Find end of function (simplified)
                brace_count = 1
                pos = match.end()
                while pos < len(content) and brace_count > 0:
                    if content[pos] == '{':
                        brace_count += 1
                    elif content[pos] == '}':
                        brace_count -= 1
                    pos += 1
                
                end_line = content[:pos].count('\n') + 1
                code_lines = lines[start_line - 1:end_line]
                code = "\n".join(code_lines)
                
                chunks.append(self._create_chunk(
                    type="function",
                    name=func_name,
                    code=code,
                    file_path=relative_path,
                    start_line=start_line,
                    end_line=end_line,
                    language=language
                ))
            
            # Also add module-level chunk
            module_chunk = self._create_chunk(
                type="module",
                name=Path(file_path).stem,
                code=content[:min(1000, len(content))],
                file_path=relative_path,
                start_line=1,
                end_line=len(lines),
                language=language
            )
            chunks.append(module_chunk)
            
        except Exception as e:
            logger.error(f"Error parsing JavaScript file {file_path}: {e}")
        
        return chunks
    
    async def parse_generic_file(self, file_path: str, base_path: str) -> List[CodeChunk]:
        """Parse generic code file (fallback)."""
        chunks = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
            
            relative_path = os.path.relpath(file_path, base_path)
            ext = Path(file_path).suffix.lower()
            language = ext[1:] if ext else "unknown"
            
            # Split into chunks by size
            chunk_size = settings.max_chunk_size
            
            for i in range(0, len(content), chunk_size):
                chunk_content = content[i:i + chunk_size]
                start_line = content[:i].count('\n') + 1
                end_line = content[:i + len(chunk_content)].count('\n') + 1
                
                chunks.append(self._create_chunk(
                    type="module",
                    name=f"{Path(file_path).stem}_part_{i // chunk_size + 1}",
                    code=chunk_content,
                    file_path=relative_path,
                    start_line=start_line,
                    end_line=end_line,
                    language=language
                ))
        
        except Exception as e:
            logger.error(f"Error parsing generic file {file_path}: {e}")
        
        return chunks
    
    def _create_chunk(self, **kwargs) -> CodeChunk:
        """Create a CodeChunk with auto-incrementing ID."""
        self.chunk_counter += 1
        chunk_id = f"chunk_{self.chunk_counter:06d}"
        return CodeChunk(id=chunk_id, **kwargs)