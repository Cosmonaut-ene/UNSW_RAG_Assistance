# rag/search_engine.py
"""
Search Engine - Handles vector similarity search and document retrieval
"""

from typing import List, Optional
import threading
from langchain.docstore.document import Document
from .vector_store import load_vector_store, validate_vector_database_exists

# Global flag to prevent multiple simultaneous rebuilds
_rebuild_in_progress = False
_rebuild_lock = threading.Lock()

def _start_background_rebuild(operation_name: str = "search"):
    """
    Start background vector store rebuild if not already in progress
    
    Args:
        operation_name: Name of the operation that triggered the rebuild
    """
    global _rebuild_in_progress
    
    with _rebuild_lock:
        if _rebuild_in_progress:
            print(f"[SearchEngine] Background rebuild already in progress, skipping for {operation_name}")
            return
        
        _rebuild_in_progress = True
        print(f"[SearchEngine] Starting background rebuild triggered by {operation_name}")
    
    def background_rebuild():
        global _rebuild_in_progress
        try:
            from . import update_knowledge_base
            print(f"[SearchEngine] Background rebuild ({operation_name}): Initializing vector store...")
            result = update_knowledge_base(include_scraped=True)
            if result and validate_vector_database_exists():
                print(f"[SearchEngine] Background rebuild ({operation_name}): Vector store ready for future queries")
            else:
                print(f"[SearchEngine] Background rebuild ({operation_name}): Failed or not needed")
        except Exception as e:
            print(f"[SearchEngine] Background rebuild ({operation_name}) failed: {e}")
        finally:
            with _rebuild_lock:
                _rebuild_in_progress = False
            print(f"[SearchEngine] Background rebuild ({operation_name}) completed")
    
    rebuild_thread = threading.Thread(target=background_rebuild, daemon=True)
    rebuild_thread.start()

def search_similar_documents(query: str, k: int = 20) -> List[Document]:
    """
    Search for similar documents using vector similarity
    
    Args:
        query: Search query string
        k: Number of documents to retrieve
        
    Returns:
        List of similar documents
    """
    try:
        if not validate_vector_database_exists():
            print("[SearchEngine] Vector store not available, starting background rebuild...")
            _start_background_rebuild("similarity_search")
            print("[SearchEngine] Returning empty results for fast LLM fallback while rebuilding in background")
            return []
        
        vectorstore = load_vector_store()
        retriever = vectorstore.as_retriever(search_kwargs={"k": k})
        
        # Perform similarity search
        documents = retriever.get_relevant_documents(query)
        
        print(f"[SearchEngine] Found {len(documents)} similar documents for query: {query[:50]}...")
        
        # Log chunk details
        for i, doc in enumerate(documents, 1):
            metadata = doc.metadata if hasattr(doc, 'metadata') else {}
            source = metadata.get('source', 'Unknown')
            content_type = metadata.get('content_type', 'Unknown')
            chunk_preview = doc.page_content[:500] if hasattr(doc, 'page_content') else 'No content'
            
            print(f"[SearchEngine] Chunk {i}: {chunk_preview}...")
        
        return documents
        
    except Exception as e:
        print(f"[SearchEngine] Error during similarity search: {e}")
        return []

def search_documents_with_scores(query: str, k: int = 20) -> List[tuple]:
    """
    Search for similar documents with similarity scores
    
    Args:
        query: Search query string  
        k: Number of documents to retrieve
        
    Returns:
        List of (document, score) tuples
    """
    try:
        if not validate_vector_database_exists():
            print("[SearchEngine] Vector store not available for scored search, using background rebuild")
            _start_background_rebuild("scored_search")
            return []
        
        vectorstore = load_vector_store()
        
        # Perform similarity search with scores
        results = vectorstore.similarity_search_with_score(query, k=k)
        
        print(f"[SearchEngine] Found {len(results)} documents with scores for query: {query[:50]}...")
        
        # Log chunk details with scores
        for i, (doc, score) in enumerate(results, 1):
            metadata = doc.metadata if hasattr(doc, 'metadata') else {}
            source = metadata.get('source', 'Unknown')
            content_type = metadata.get('content_type', 'Unknown')
            chunk_preview = doc.page_content[:100].replace('\n', ' ') if hasattr(doc, 'page_content') else 'No content'
            
            print(f"[SearchEngine] Chunk {i} (score: {score:.4f}): {source} ({content_type}) - {chunk_preview}...")
        
        return results
        
    except Exception as e:
        print(f"[SearchEngine] Error during scored similarity search: {e}")
        return []

def search_documents_by_metadata(metadata_filter: dict, k: int = 20) -> List[Document]:
    """
    Search for documents by metadata criteria
    
    Args:
        metadata_filter: Dictionary of metadata criteria to match
        k: Maximum number of documents to retrieve
        
    Returns:
        List of matching documents
    """
    try:
        if not validate_vector_database_exists():
            print("[SearchEngine] Vector store not available for metadata search, using background rebuild")
            _start_background_rebuild("metadata_search")
            return []
        
        vectorstore = load_vector_store()
        
        # ChromaDB metadata filtering (basic implementation)
        # Note: ChromaDB has specific syntax for metadata filtering
        retriever = vectorstore.as_retriever(
            search_kwargs={
                "k": k,
                "filter": metadata_filter
            }
        )
        
        # Use a dummy query since we're filtering by metadata
        documents = retriever.get_relevant_documents("")
        
        # Additional filtering if ChromaDB filtering didn't work as expected
        filtered_docs = []
        for doc in documents:
            if all(doc.metadata.get(key) == value for key, value in metadata_filter.items()):
                filtered_docs.append(doc)
                if len(filtered_docs) >= k:
                    break
        
        print(f"[SearchEngine] Found {len(filtered_docs)} documents matching metadata filter")
        return filtered_docs
        
    except Exception as e:
        print(f"[SearchEngine] Error during metadata search: {e}")
        return []