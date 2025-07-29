# rag/search_engine.py
"""
Search Engine - Handles vector similarity search and document retrieval
"""

from typing import List, Optional
from langchain.docstore.document import Document
from .vector_store import load_vector_store, validate_vector_database_exists

def search_similar_documents(query: str, k: int = 5) -> List[Document]:
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
            print("[SearchEngine] Vector store not available, attempting lazy initialization...")
            
            # Try to initialize vector store on-demand
            try:
                from . import update_knowledge_base
                print("[SearchEngine] Attempting to initialize vector store...")
                result = update_knowledge_base(include_scraped=True)
                
                if result and validate_vector_database_exists():
                    print("[SearchEngine] Vector store initialized successfully")
                else:
                    print("[SearchEngine] Vector store initialization failed or not needed")
                    return []
                    
            except Exception as init_error:
                print(f"[SearchEngine] Failed to initialize vector store: {init_error}")
                return []
        
        vectorstore = load_vector_store()
        retriever = vectorstore.as_retriever(search_kwargs={"k": k})
        
        # Perform similarity search
        documents = retriever.get_relevant_documents(query)
        
        print(f"[SearchEngine] Found {len(documents)} similar documents for query: {query[:50]}...")
        return documents
        
    except Exception as e:
        print(f"[SearchEngine] Error during similarity search: {e}")
        return []

def search_documents_with_scores(query: str, k: int = 5) -> List[tuple]:
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
            print("[SearchEngine] Vector store not available for search")
            return []
        
        vectorstore = load_vector_store()
        
        # Perform similarity search with scores
        results = vectorstore.similarity_search_with_score(query, k=k)
        
        print(f"[SearchEngine] Found {len(results)} documents with scores for query: {query[:50]}...")
        return results
        
    except Exception as e:
        print(f"[SearchEngine] Error during scored similarity search: {e}")
        return []

def search_documents_by_metadata(metadata_filter: dict, k: int = 10) -> List[Document]:
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
            print("[SearchEngine] Vector store not available for search")
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