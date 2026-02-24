# rag/incremental_vectorstore.py
"""
Incremental vector store operations to avoid ChromaDB rebuild issues
"""

import os
from typing import List, Dict, Optional
from langchain_core.documents import Document
from langchain_chroma import Chroma
from .vector_store import VECTOR_STORE_DIR, validate_vector_database_exists

def add_documents_to_vectorstore(documents: List[Document], source_path: str) -> bool:
    """
    Add documents to existing vector store without rebuilding
    
    Args:
        documents: List of document chunks to add
        source_path: Source file path for tracking
        
    Returns:
        bool: True if successful
    """
    try:
        if not validate_vector_database_exists():
            print("[IncrementalVS] No existing vector store found")
            return False
        
        from ai.llm_client import get_embeddings_client
        embeddings = get_embeddings_client()
        
        # Load existing vector store
        vectorstore = Chroma(
            persist_directory=VECTOR_STORE_DIR,
            embedding_function=embeddings,
            collection_name="knowledge_base"
        )
        
        # Add new documents in batches to avoid ChromaDB limits
        batch_size = 1000  # Conservative batch size
        total_docs = len(documents)
        
        for i in range(0, total_docs, batch_size):
            batch = documents[i:i + batch_size]
            vectorstore.add_documents(batch)
            print(f"[IncrementalVS] Added batch {i//batch_size + 1}/{(total_docs + batch_size - 1)//batch_size}: {len(batch)} documents")
        
        # Update source tracking
        _update_source_tracking_add(source_path, len(documents))
        
        print(f"[IncrementalVS] Added {len(documents)} documents from {source_path}")
        return True
        
    except Exception as e:
        print(f"[IncrementalVS] Error adding documents: {e}")
        return False

def remove_documents_from_vectorstore(source_path: str) -> int:
    """
    Remove documents by source path from vector store
    
    Args:
        source_path: Source file path to remove
        
    Returns:
        int: Number of documents removed, -1 if error
    """
    try:
        if not validate_vector_database_exists():
            print("[IncrementalVS] No existing vector store found")
            return -1
        
        from ai.llm_client import get_embeddings_client
        embeddings = get_embeddings_client()
        
        # Load existing vector store
        vectorstore = Chroma(
            persist_directory=VECTOR_STORE_DIR,
            embedding_function=embeddings,
            collection_name="knowledge_base"
        )
        
        collection = vectorstore._collection
        
        # Get all documents with metadata
        all_data = collection.get(include=['metadatas'])
        
        if not all_data['ids']:
            print("[IncrementalVS] No documents found in vector store")
            return 0
        
        # Find documents matching the source path
        ids_to_delete = []
        filename = os.path.basename(source_path)
        
        for i, metadata in enumerate(all_data['metadatas']):
            if metadata and metadata.get('source', '').endswith(filename):
                ids_to_delete.append(all_data['ids'][i])
        
        if not ids_to_delete:
            print(f"[IncrementalVS] No documents found with source: {filename}")
            return 0
        
        # Delete documents
        collection.delete(ids=ids_to_delete)
        
        # Update source tracking
        _update_source_tracking_remove(filename)
        
        print(f"[IncrementalVS] Removed {len(ids_to_delete)} documents from {filename}")
        return len(ids_to_delete)
        
    except Exception as e:
        print(f"[IncrementalVS] Error removing documents: {e}")
        return -1

def update_documents_in_vectorstore(documents: List[Document], source_path: str) -> bool:
    """
    Update documents for a source (remove old + add new)
    
    Args:
        documents: New document chunks
        source_path: Source file path
        
    Returns:
        bool: True if successful
    """
    try:
        # Remove existing documents
        removed_count = remove_documents_from_vectorstore(source_path)
        if removed_count >= 0:
            print(f"[IncrementalVS] Removed {removed_count} old documents for {source_path}")
        
        # Add new documents
        success = add_documents_to_vectorstore(documents, source_path)
        
        if success:
            print(f"[IncrementalVS] Successfully updated {len(documents)} documents for {source_path}")
            return True
        else:
            print(f"[IncrementalVS] Failed to add new documents for {source_path}")
            return False
            
    except Exception as e:
        print(f"[IncrementalVS] Error updating documents: {e}")
        return False

def process_file_operation(operation: str, file_path: str) -> bool:
    """
    Process file operation incrementally
    
    Args:
        operation: 'added', 'deleted', or 'modified'
        file_path: Path to the file
        
    Returns:
        bool: True if successful
    """
    try:
        filename = os.path.basename(file_path)
        
        if operation == 'deleted':
            # Remove documents for deleted file
            removed_count = remove_documents_from_vectorstore(file_path)
            return removed_count >= 0
            
        elif operation in ['added', 'modified']:
            # Process the file and add/update documents
            if not os.path.exists(file_path):
                print(f"[IncrementalVS] File not found: {file_path}")
                return False
            
            # Load and process the document
            from .document_loader import load_pdf_documents
            from .text_splitter import split_documents_by_content_type
            
            # Load the specific file
            docs = []
            if file_path.endswith('.pdf'):
                # Create a temporary directory with just this file for loading
                import tempfile
                import shutil
                
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_file = os.path.join(temp_dir, filename)
                    shutil.copy2(file_path, temp_file)
                    docs = load_pdf_documents(temp_dir)
            
            if not docs:
                print(f"[IncrementalVS] No documents loaded from {file_path}")
                return False
            
            # Split documents
            chunks = split_documents_by_content_type(docs)
            
            if operation == 'added':
                return add_documents_to_vectorstore(chunks, file_path)
            else:  # modified
                return update_documents_in_vectorstore(chunks, file_path)
        
        return False
        
    except Exception as e:
        print(f"[IncrementalVS] Error processing file operation: {e}")
        return False

def _update_source_tracking_add(source_path: str, doc_count: int):
    """Update source tracking file when adding documents"""
    try:
        filename = os.path.basename(source_path)
        source_record_file = os.path.join(VECTOR_STORE_DIR, "source_files.txt")
        
        # Read existing sources
        existing_sources = set()
        if os.path.exists(source_record_file):
            with open(source_record_file, 'r', encoding='utf-8') as f:
                existing_sources = set(line.strip() for line in f if line.strip())
        
        # Add new source
        existing_sources.add(filename)
        
        # Write back
        os.makedirs(VECTOR_STORE_DIR, exist_ok=True)
        with open(source_record_file, 'w', encoding='utf-8') as f:
            for source in sorted(existing_sources):
                f.write(f"{source}\n")
                
        print(f"[IncrementalVS] Updated source tracking: added {filename}")
        
    except Exception as e:
        print(f"[IncrementalVS] Error updating source tracking (add): {e}")

def _update_source_tracking_remove(filename: str):
    """Update source tracking file when removing documents"""
    try:
        source_record_file = os.path.join(VECTOR_STORE_DIR, "source_files.txt")
        
        if not os.path.exists(source_record_file):
            return
        
        # Read existing sources
        existing_sources = set()
        with open(source_record_file, 'r', encoding='utf-8') as f:
            existing_sources = set(line.strip() for line in f if line.strip())
        
        # Remove the source
        existing_sources.discard(filename)
        
        # Write back
        with open(source_record_file, 'w', encoding='utf-8') as f:
            for source in sorted(existing_sources):
                f.write(f"{source}\n")
                
        print(f"[IncrementalVS] Updated source tracking: removed {filename}")
        
    except Exception as e:
        print(f"[IncrementalVS] Error updating source tracking (remove): {e}")

def get_vectorstore_stats() -> Dict:
    """Get statistics about the vector store"""
    try:
        if not validate_vector_database_exists():
            return {"available": False, "error": "Vector store not found"}
        
        from ai.llm_client import get_embeddings_client
        embeddings = get_embeddings_client()
        
        vectorstore = Chroma(
            persist_directory=VECTOR_STORE_DIR,
            embedding_function=embeddings,
            collection_name="knowledge_base"
        )
        
        collection = vectorstore._collection
        all_data = collection.get(include=['metadatas'])
        
        total_docs = len(all_data['ids']) if all_data['ids'] else 0
        
        # Count by source
        sources = {}
        if all_data['metadatas']:
            for metadata in all_data['metadatas']:
                if metadata and 'source' in metadata:
                    source = os.path.basename(metadata['source'])
                    sources[source] = sources.get(source, 0) + 1
        
        return {
            "available": True,
            "total_documents": total_docs,
            "sources": sources,
            "source_count": len(sources)
        }
        
    except Exception as e:
        return {"available": False, "error": f"Error getting stats: {e}"}