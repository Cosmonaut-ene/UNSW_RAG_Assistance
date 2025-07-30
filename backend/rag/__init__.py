# rag/__init__.py
"""
RAG Module - Handles document processing, vector storage, and retrieval
"""

from .document_loader import load_pdf_documents, load_scraped_documents
from .text_splitter import split_documents_by_content_type
# Import vector_store functions dynamically to avoid circular dependency
# from .vector_store import (functions imported on demand)
from .search_engine import search_similar_documents, search_documents_with_scores
from .chain_builder import build_rag_qa_chain

# Import centralized path configuration
from config.paths import PathConfig

# Configuration constants
VECTOR_STORE_DIR = str(PathConfig.VECTOR_STORE_DIR)
KNOWLEDGE_BASE_DIR = str(PathConfig.DOCUMENTS_DIR)
SCRAPED_CONTENT_DIR = str(PathConfig.SCRAPED_CONTENT_DIR)

# High-level API functions
def search_documents(query: str, k: int = 5):
    """
    Search for similar documents using vector similarity
    
    Args:
        query: Search query string
        k: Number of documents to retrieve
        
    Returns:
        List of similar documents
    """
    return search_similar_documents(query, k)

def update_knowledge_base(include_scraped: bool = True) -> bool:
    """
    Update the vector store with latest content
    
    Args:
        include_scraped: Whether to include scraped content
        
    Returns:
        bool: True if update was performed, False if no update needed
    """
    # Dynamic import to avoid circular dependency
    from .vector_store import update_vector_store_with_documents
    
    # Load all documents
    all_docs = []
    
    # Load PDF documents
    pdf_docs = load_pdf_documents(KNOWLEDGE_BASE_DIR)
    all_docs.extend(pdf_docs)
    
    # Load scraped documents
    if include_scraped:
        scraped_docs = load_scraped_documents(SCRAPED_CONTENT_DIR)
        all_docs.extend(scraped_docs)
    
    if not all_docs:
        print("[RAG] No documents found to process")
        return False
    
    # Split documents using appropriate strategies
    chunks = split_documents_by_content_type(all_docs)
    
    # Update vector store
    return update_vector_store_with_documents(chunks, include_scraped)

def force_rebuild_knowledge_base(include_scraped: bool = True) -> bool:
    """
    Force rebuild of vector store regardless of changes
    
    Args:
        include_scraped: Whether to include scraped content
        
    Returns:
        bool: True if rebuild successful, False otherwise
    """
    try:
        # Load all documents
        all_docs = []
        
        # Load PDF documents
        pdf_docs = load_pdf_documents(KNOWLEDGE_BASE_DIR)
        all_docs.extend(pdf_docs)
        print(f"[RAG] Loaded {len(pdf_docs)} PDF documents")
        
        # Load scraped documents
        if include_scraped:
            scraped_docs = load_scraped_documents(SCRAPED_CONTENT_DIR)
            all_docs.extend(scraped_docs)
            print(f"[RAG] Loaded {len(scraped_docs)} scraped documents")
        
        if not all_docs:
            print("[RAG] No documents found to process")
            return False
        
        # Split documents using appropriate strategies
        chunks = split_documents_by_content_type(all_docs)
        
        # Create new vector store (this will remove existing one)
        from .vector_store import create_vector_store
        create_vector_store(chunks)
        
        # Update source tracking
        from .vector_store import VECTOR_STORE_DIR
        import os
        source_record_file = os.path.join(VECTOR_STORE_DIR, "source_files.txt")
        os.makedirs(VECTOR_STORE_DIR, exist_ok=True)
        
        with open(source_record_file, 'w', encoding='utf-8') as f:
            # Write PDF files
            if os.path.exists(KNOWLEDGE_BASE_DIR):
                pdf_files = [f for f in os.listdir(KNOWLEDGE_BASE_DIR) if f.endswith('.pdf')]
                for filename in sorted(pdf_files):
                    f.write(f"{filename}\n")
            
            # Write scraped files
            if include_scraped:
                scraped_content_dir = os.path.join(SCRAPED_CONTENT_DIR, "content")
                if os.path.exists(scraped_content_dir):
                    scraped_files = [f for f in os.listdir(scraped_content_dir) if f.endswith('.json')]
                    for scraped_file in sorted(scraped_files):
                        f.write(f"scraped:{scraped_file}\n")
        
        print("[RAG] Force rebuild completed successfully")
        return True
        
    except Exception as e:
        print(f"[RAG] Force rebuild failed: {e}")
        return False

# Dynamic imports to avoid circular dependencies
def create_vector_store(documents):
    """Create vector store - dynamic import to avoid circular dependency"""
    from .vector_store import create_vector_store as _create
    return _create(documents)

def load_vector_store():
    """Load vector store - dynamic import to avoid circular dependency"""
    from .vector_store import load_vector_store as _load
    return _load()

def update_vector_store_with_documents(documents, include_scraped=True):
    """Update vector store - dynamic import to avoid circular dependency"""
    from .vector_store import update_vector_store_with_documents as _update
    return _update(documents, include_scraped)

def remove_documents_by_source(source_url):
    """Remove documents by source - dynamic import to avoid circular dependency"""
    from .vector_store import remove_documents_by_source as _remove
    return _remove(source_url)

def get_vector_store_info():
    """Get vector store info - dynamic import to avoid circular dependency"""
    from .vector_store import get_vector_store_info as _info
    return _info()

def get_content_sources_summary():
    """Get content sources summary - dynamic import to avoid circular dependency"""
    from .vector_store import get_content_sources_summary as _summary
    return _summary()

# Backward compatibility functions (delegating to AI module for complete processing)
def process_with_rag_detailed(question: str, conversation_history: list = None) -> dict:
    """
    Process question with RAG retrieval only (no AI generation)
    Returns search results for the service layer to process with AI
    """
    try:
        # Perform document search
        search_results = search_similar_documents(question, k=5)
        
        print(f"[RAG] Processing {len(search_results)} retrieved chunks for query: {question[:50]}...")
        
        # Convert to dict format
        result_docs = []
        matched_files = []
        
        for i, doc in enumerate(search_results, 1):
            # Log individual chunk details
            metadata = doc.metadata if hasattr(doc, 'metadata') else {}
            source_file = metadata.get('source', 'Unknown')
            content_type = metadata.get('content_type', 'Unknown')
            chunk_preview = doc.page_content[:100].replace('\n', ' ') if hasattr(doc, 'page_content') else 'No content'
            
            print(f"[RAG] Chunk {i}: {source_file} ({content_type}) - {chunk_preview}...")
            
            result_docs.append({
                'page_content': doc.page_content,
                'metadata': metadata
            })
            
            # Extract file info
            if source_file != 'Unknown':
                filename = source_file.split('/')[-1] if '/' in source_file else source_file
                if filename not in matched_files:
                    matched_files.append(filename)
        
        return {
            "search_results": result_docs,
            "matched_files": matched_files,
            "search_type": "rag_only",
            "query": question
        }
        
    except Exception as e:
        print(f"[RAG] Document search error: {e}")
        return {
            "search_results": [],
            "matched_files": [],
            "search_type": "rag_only",
            "query": question,
            "error": str(e)
        }

def process_with_rag_only(question: str, conversation_history: list = None) -> dict:
    """
    Process question with RAG only (backward compatibility)
    """
    return process_with_rag_detailed(question, conversation_history)

def process_with_rag(question: str) -> str:
    """
    Simple RAG processing - returns raw search results as string
    Note: This now returns search results instead of generated answers
    """
    result = process_with_rag_detailed(question)
    search_results = result.get("search_results", [])
    
    if not search_results:
        return "No relevant documents found."
    
    # Return concatenated content from search results
    content_parts = []
    for doc in search_results[:3]:  # Limit to top 3 results
        content_parts.append(doc.get('page_content', ''))
    
    return '\n\n---\n\n'.join(content_parts)

# Legacy search functions - delegate to AI module
def ask_with_hybrid_search(question: str, qa_chain, conversation_history: list = None) -> dict:
    """Legacy function - use ai.ask_with_hybrid_search instead"""
    try:
        from ai import ask_with_hybrid_search as ai_hybrid_search
        return ai_hybrid_search(question, qa_chain, conversation_history)
    except ImportError as e:
        print(f"[RAG] AI module not available: {e}")
        return {
            "answer": "Hybrid search is currently unavailable. Please check the AI module.",
            "sources": [],
            "matched_files": [],
            "safety_blocked": False
        }

def ask_with_rag_and_fallback(question: str, qa_chain, conversation_history: list = None) -> dict:
    """Legacy function - now returns RAG search results for service layer processing"""
    # This is essentially the same as ask_with_hybrid_search now
    return ask_with_hybrid_search(question, qa_chain, conversation_history)

# Legacy function aliases for existing code
def update_vector_store_with_scraped():
    """Legacy function - use update_knowledge_base instead"""
    return update_knowledge_base(include_scraped=True)

def force_rebuild_vector_store():
    """Legacy function - use force_rebuild_knowledge_base instead"""
    return force_rebuild_knowledge_base(include_scraped=True)

# Export key functions and classes
__all__ = [
    # Core functions
    'search_documents',
    'update_knowledge_base', 
    'force_rebuild_knowledge_base',
    
    # Document processing
    'load_pdf_documents',
    'load_scraped_documents',
    'split_documents_by_content_type',
    
    # Vector store operations
    'create_vector_store',
    'load_vector_store',
    'update_vector_store_with_documents',
    'remove_documents_by_source',
    'get_vector_store_info',
    'get_content_sources_summary',
    
    # Search operations
    'search_similar_documents',
    'search_documents_with_scores',
    
    # Chain building
    'build_rag_qa_chain',
    
    # Backward compatibility
    'process_with_rag',
    'process_with_rag_detailed', 
    'process_with_rag_only',
    'ask_with_hybrid_search',
    'ask_with_rag_and_fallback',
    'update_vector_store_with_scraped',
    'force_rebuild_vector_store',
    
    # Configuration
    'VECTOR_STORE_DIR',
    'KNOWLEDGE_BASE_DIR',
    'SCRAPED_CONTENT_DIR'
]