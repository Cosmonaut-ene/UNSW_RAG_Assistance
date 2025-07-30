# rag/vector_store.py
"""
Vector Store - Manages ChromaDB operations and vector storage
"""

import os
import shutil
from datetime import datetime
from typing import List, Dict, Optional
from langchain.docstore.document import Document
from langchain_chroma import Chroma
# Remove direct import to avoid circular dependency
# from ai.llm_client import get_embeddings_client

# Import centralized path configuration
from config.paths import PathConfig

# Vector store configuration
VECTOR_STORE_DIR = str(PathConfig.VECTOR_STORE_DIR)
KNOWLEDGE_BASE_DIR = str(PathConfig.DOCUMENTS_DIR)
SCRAPED_CONTENT_DIR = str(PathConfig.SCRAPED_CONTENT_DIR)

def validate_vector_database_exists() -> bool:
    """
    Check if vector database files exist and are accessible.
    
    Returns:
        bool: True if database exists and appears valid, False otherwise
    """
    if not os.path.exists(VECTOR_STORE_DIR):
        print("[VectorStore] Vector store directory does not exist")
        return False
    
    # Look for ChromaDB collection directories
    chroma_dirs = [d for d in os.listdir(VECTOR_STORE_DIR) 
                   if os.path.isdir(os.path.join(VECTOR_STORE_DIR, d)) and 
                   d != "__pycache__" and not d.startswith('.')]
    
    if not chroma_dirs:
        print("[VectorStore] No ChromaDB collection directories found")
        return False
    
    # Check if any collection has essential ChromaDB files
    essential_files = ['header.bin', 'data_level0.bin']
    for chroma_dir in chroma_dirs:
        chroma_path = os.path.join(VECTOR_STORE_DIR, chroma_dir)
        has_essential_files = all(
            os.path.exists(os.path.join(chroma_path, f)) 
            for f in essential_files
        )
        if has_essential_files:
            print(f"[VectorStore] Valid vector database found in {chroma_dir}")
            return True
    
    print("[VectorStore] Vector database files appear to be missing or corrupted")
    return False

def create_vector_store(documents: List[Document]) -> Chroma:
    """
    Create ChromaDB vector store from document chunks.
    
    Args:
        documents: List of chunked documents
        
    Returns:
        Chroma: ChromaDB vector store instance
    """
    if not documents:
        raise ValueError("No documents provided for vector store creation")
    
    from ai.llm_client import get_embeddings_client
    embeddings = get_embeddings_client()
    
    # Remove existing vector store directory to ensure clean rebuild
    if os.path.exists(VECTOR_STORE_DIR):
        shutil.rmtree(VECTOR_STORE_DIR)
        print("[VectorStore] Removed existing vector store directory")
    
    db = Chroma.from_documents(documents, embeddings, persist_directory=VECTOR_STORE_DIR)
    print(f"[VectorStore] Created ChromaDB vector store with {len(documents)} documents")
    return db

def load_vector_store() -> Chroma:
    """
    Load existing ChromaDB vector store.
    
    Returns:
        Chroma: Loaded vector store instance
        
    Raises:
        ValueError: If vector store doesn't exist
    """
    if not validate_vector_database_exists():
        raise ValueError("Vector store does not exist or is invalid")
    
    from ai.llm_client import get_embeddings_client
    embeddings = get_embeddings_client()
    vectorstore = Chroma(
        persist_directory=VECTOR_STORE_DIR,
        embedding_function=embeddings
    )
    print("[VectorStore] Loaded existing ChromaDB vector store")
    return vectorstore

def update_vector_store_with_documents(documents: List[Document], include_scraped: bool = True) -> bool:
    """
    Update vector store with new documents, checking for changes first.
    
    Args:
        documents: All documents to include
        include_scraped: Whether to include scraped content (for compatibility)
        
    Returns:
        bool: True if update was performed, False if no update needed
    """
    source_record_file = os.path.join(VECTOR_STORE_DIR, "source_files.txt")
    
    # Calculate current file signatures
    current_files = []
    current_scraped_files = []
    
    for doc in documents:
        if doc.metadata.get('content_type') == 'pdf':
            source = doc.metadata.get('source', '')
            if source:
                filename = source.split('/')[-1] if '/' in source else source
                if filename.endswith('.pdf') and filename not in current_files:
                    current_files.append(filename)
        elif doc.metadata.get('content_type') == 'scraped_web':
            scraped_file = doc.metadata.get('scraped_from_file', '')
            if scraped_file and scraped_file not in current_scraped_files:
                current_scraped_files.append(scraped_file)
    
    current_files = sorted(current_files)
    current_scraped_files = sorted(current_scraped_files)
    
    # Read last sources
    last_files = []
    last_scraped_files = []
    if os.path.exists(source_record_file):
        try:
            with open(source_record_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    lines = content.split('\n')
                    for line in lines:
                        if line.startswith('scraped:'):
                            last_scraped_files.append(line[8:])
                        else:
                            last_files.append(line)
                    last_files = sorted(last_files)
                    last_scraped_files = sorted(last_scraped_files)
        except Exception as e:
            print(f"[VectorStore] Error reading source record file: {e}")
    
    # Check if sources changed
    files_changed = current_files != last_files
    scraped_changed = current_scraped_files != last_scraped_files
    db_exists = validate_vector_database_exists()
    
    # Rebuild if sources changed OR database is missing
    rebuild_needed = files_changed or scraped_changed or not db_exists
    
    if rebuild_needed:
        # Log specific reasons for rebuild
        reasons = []
        if files_changed:
            reasons.append(f"PDF files changed (was: {len(last_files)}, now: {len(current_files)})")
        if scraped_changed:
            reasons.append(f"Scraped content changed (was: {len(last_scraped_files)}, now: {len(current_scraped_files)})")
        if not db_exists:
            reasons.append("Vector database files missing or corrupted")
        
        print(f"[VectorStore] Rebuilding vector store. Reasons: {'; '.join(reasons)}")
        
        try:
            # Create new vector store
            create_vector_store(documents)
            
            # Update source tracking after successful creation
            os.makedirs(VECTOR_STORE_DIR, exist_ok=True)
            with open(source_record_file, 'w', encoding='utf-8') as f:
                for filename in current_files:
                    f.write(f"{filename}\n")
                for scraped_file in current_scraped_files:
                    f.write(f"scraped:{scraped_file}\n")
            
            print(f"[VectorStore] Successfully rebuilt with {len(current_files)} PDFs and {len(current_scraped_files)} scraped documents")
            return True
            
        except Exception as e:
            print(f"[VectorStore] Error during vector store rebuild: {e}")
            raise
    else:
        print("[VectorStore] Vector store is up-to-date")
        return False

def remove_documents_by_source(source_url: str) -> int:
    """
    Remove all documents from vector store that match the given source URL.
    
    Args:
        source_url: The source URL to match against document metadata
    
    Returns:
        int: Number of documents removed
    """
    try:
        vectorstore = load_vector_store()
        collection = vectorstore._collection
        all_data = collection.get(include=['metadatas', 'documents'])
        
        if not all_data['ids']:
            print(f"[VectorStore] No documents found in vector store")
            return 0
        
        # Find documents with matching source
        ids_to_delete = []
        for i, metadata in enumerate(all_data['metadatas']):
            if metadata and metadata.get('source') == source_url:
                ids_to_delete.append(all_data['ids'][i])
        
        if not ids_to_delete:
            print(f"[VectorStore] No documents found with source: {source_url}")
            return 0
        
        # Delete documents
        collection.delete(ids=ids_to_delete)
        
        print(f"[VectorStore] Removed {len(ids_to_delete)} documents with source: {source_url}")
        return len(ids_to_delete)
        
    except Exception as e:
        print(f"[VectorStore] Error removing documents by source: {e}")
        return 0

def get_vector_store_info() -> Dict:
    """
    Get information about the current vector store state.
    
    Returns:
        Dict with vector store statistics and status
    """
    try:
        if not validate_vector_database_exists():
            return {
                "available": False,
                "error": "Vector store not found or invalid"
            }
        
        vectorstore = load_vector_store()
        collection = vectorstore._collection
        all_data = collection.get(include=['metadatas'])
        
        total_documents = len(all_data['ids']) if all_data['ids'] else 0
        
        # Count by content type
        content_types = {}
        sources = set()
        
        if all_data['metadatas']:
            for metadata in all_data['metadatas']:
                if metadata:
                    # Count content types
                    content_type = metadata.get('content_type', 'unknown')
                    content_types[content_type] = content_types.get(content_type, 0) + 1
                    
                    # Collect unique sources
                    source = metadata.get('source')
                    if source:
                        sources.add(source)
        
        return {
            "available": True,
            "total_documents": total_documents,
            "unique_sources": len(sources),
            "content_types": content_types,
            "sources": list(sources),
            "vector_store_dir": VECTOR_STORE_DIR
        }
        
    except Exception as e:
        return {
            "available": False,
            "error": f"Error accessing vector store: {str(e)}"
        }

def get_content_sources_summary() -> Dict:
    """
    Get summary of all content sources in the vector store.
    
    Returns:
        Dictionary with content source statistics
    """
    # PDF files
    pdf_files = []
    if os.path.exists(KNOWLEDGE_BASE_DIR):
        pdf_files = [f for f in os.listdir(KNOWLEDGE_BASE_DIR) if f.endswith('.pdf')]
    
    # Scraped content
    scraped_files = []
    scraped_content_dir = os.path.join(SCRAPED_CONTENT_DIR, "content")
    if os.path.exists(scraped_content_dir):
        scraped_files = [f for f in os.listdir(scraped_content_dir) if f.endswith('.json')]
    
    # Load source tracking file
    source_record_file = os.path.join(VECTOR_STORE_DIR, "source_files.txt")
    last_updated = None
    if os.path.exists(source_record_file):
        stat = os.stat(source_record_file)
        last_updated = datetime.fromtimestamp(stat.st_mtime).isoformat()
    
    return {
        "pdf_sources": {
            "count": len(pdf_files),
            "files": pdf_files
        },
        "scraped_sources": {
            "count": len(scraped_files),
            "files": scraped_files[:10]  # Show first 10 for preview
        },
        "total_sources": len(pdf_files) + len(scraped_files),
        "vector_store_last_updated": last_updated,
        "vector_store_exists": validate_vector_database_exists()
    }

# ========== Backward Compatibility Functions ==========

def update_vector_store_with_scraped():
    """
    Legacy function - Convenience wrapper for updating vector store with scraped content.
    Use rag.update_knowledge_base(include_scraped=True) instead.
    """
    from . import update_knowledge_base
    return update_knowledge_base(include_scraped=True)

def force_rebuild_vector_store():
    """
    Legacy function - Force rebuild of vector store regardless of changes.
    Use rag.force_rebuild_knowledge_base(include_scraped=True) instead.
    """
    from . import force_rebuild_knowledge_base
    return force_rebuild_knowledge_base(include_scraped=True)