"""Vector database service using ChromaDB."""

import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any
import logging
import numpy as np

from app.config import settings
from app.core.exceptions import VectorDBException
from app.services.parser_service import CodeChunk

logger = logging.getLogger(__name__)


class VectorService:
    """Manage ChromaDB operations."""
    
    def __init__(self):
        """Initialize ChromaDB client."""
        self.client = chromadb.PersistentClient(
            path=settings.chroma_persist_directory,
            settings=ChromaSettings(
                anonymized_telemetry=False
            )
        )
    
    async def create_collection(self, session_id: str) -> None:
        """Create a new collection for session."""
        try:
            collection_name = f"session_{session_id}"
            
            # Delete if exists (cleanup from previous failed attempts)
            try:
                self.client.delete_collection(name=collection_name)
            except:
                pass
            
            # Create new collection
            self.client.create_collection(
                name=collection_name,
                metadata={"session_id": session_id}
            )
            
            logger.info(f"Created collection: {collection_name}")
            
        except Exception as e:
            logger.error(f"Error creating collection: {e}")
            raise VectorDBException(f"Failed to create collection: {str(e)}")
    
    async def insert_embeddings(
        self,
        session_id: str,
        chunks: List[CodeChunk],
        embeddings: List[np.ndarray]
    ) -> None:
        """Insert embeddings into collection."""
        try:
            collection_name = f"session_{session_id}"
            collection = self.client.get_collection(name=collection_name)
            
            # Prepare data
            ids = [chunk.id for chunk in chunks]
            documents = [chunk.code for chunk in chunks]
            metadatas = [
                {
                    "file_path": chunk.file_path,
                    "type": chunk.type,
                    "name": chunk.name,
                    "language": chunk.language,
                    "lines": f"{chunk.start_line}-{chunk.end_line}",
                    "docstring": chunk.docstring
                }
                for chunk in chunks
            ]
            embeddings_list = [emb.tolist() for emb in embeddings]
            
            # Insert in batches (ChromaDB recommends batches of 41666)
            batch_size = 1000
            for i in range(0, len(ids), batch_size):
                collection.add(
                    ids=ids[i:i + batch_size],
                    documents=documents[i:i + batch_size],
                    metadatas=metadatas[i:i + batch_size],
                    embeddings=embeddings_list[i:i + batch_size]
                )
            
            logger.info(f"Inserted {len(ids)} embeddings into collection {collection_name}")
            
        except Exception as e:
            logger.error(f"Error inserting embeddings: {e}")
            raise VectorDBException(f"Failed to insert embeddings: {str(e)}")
    
    async def search_similar(
        self,
        session_id: str,
        query_embedding: np.ndarray,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for similar code chunks."""
        try:
            collection_name = f"session_{session_id}"
            collection = self.client.get_collection(name=collection_name)
            
            # Query collection
            results = collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=top_k,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results
            chunks = []
            for i in range(len(results['ids'][0])):
                chunks.append({
                    "id": results['ids'][0][i],
                    "code": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "distance": results['distances'][0][i]
                })
            
            logger.debug(f"Found {len(chunks)} similar chunks")
            return chunks
            
        except Exception as e:
            logger.error(f"Error searching similar chunks: {e}")
            raise VectorDBException(f"Failed to search: {str(e)}")
    
    async def delete_collection(self, session_id: str) -> None:
        """Delete collection for session."""
        try:
            collection_name = f"session_{session_id}"
            self.client.delete_collection(name=collection_name)
            logger.info(f"Deleted collection: {collection_name}")
            
        except Exception as e:
            logger.warning(f"Error deleting collection: {e}")
            # Don't raise exception, collection might not exist
    
    def get_collection_count(self, session_id: str) -> int:
        """Get number of documents in collection."""
        try:
            collection_name = f"session_{session_id}"
            collection = self.client.get_collection(name=collection_name)
            return collection.count()
        except:
            return 0