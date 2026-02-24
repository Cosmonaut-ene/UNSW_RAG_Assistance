# rag/document_loader.py
"""
Document Loader - Handles loading of PDF and scraped JSON documents
"""

import os
import json
from typing import List
from langchain_core.documents import Document
from langchain_community.document_loaders import PyMuPDFLoader

def load_pdf_documents(folder_path: str) -> List[Document]:
    """
    Load PDF documents from folder.
    
    Args:
        folder_path: Path to folder containing PDF files
        
    Returns:
        List of LangChain Documents
    """
    documents = []
    
    if not os.path.exists(folder_path):
        print(f"[DocumentLoader] PDF folder not found: {folder_path}")
        return []
    
    for filename in os.listdir(folder_path):
        if filename.endswith(".pdf"):
            try:
                loader = PyMuPDFLoader(os.path.join(folder_path, filename))
                doc_chunks = loader.load()
                
                # Mark PDF documents with content_type
                for doc in doc_chunks:
                    doc.metadata["content_type"] = "pdf"
                    
                print(f"[DocumentLoader] Loaded {len(doc_chunks)} pages from {filename}")
                documents.extend(doc_chunks)
                
            except Exception as e:
                print(f"[DocumentLoader] Error loading PDF {filename}: {e}")
                
    return documents

def load_scraped_documents(scraped_content_dir: str) -> List[Document]:
    """
    Load documents from scraped content directory.
    Returns LangChain Documents from JSON files created by the scrapers module.
    
    Args:
        scraped_content_dir: Path to scraped content directory
        
    Returns:
        List of LangChain Documents
    """
    scraped_docs = []
    content_dir = os.path.join(scraped_content_dir, "content")
    
    if not os.path.exists(content_dir):
        print("[DocumentLoader] No scraped content directory found")
        return []
    
    # Load all JSON files from content directory
    json_files = [f for f in os.listdir(content_dir) if f.endswith('.json')]
    
    if not json_files:
        print("[DocumentLoader] No scraped content files found")
        return []
    
    print(f"[DocumentLoader] Loading {len(json_files)} scraped documents...")
    
    for filename in json_files:
        filepath = os.path.join(content_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Create Document from scraped data
                document = Document(
                    page_content=data.get("page_content", ""),
                    metadata=data.get("metadata", {})
                )
                
                # Add scraping metadata
                document.metadata["scraped_from_file"] = filename
                document.metadata["type"] = document.metadata["content_type"]
                document.metadata["content_type"] = "scraped_web"
                
                scraped_docs.append(document)
                
        except Exception as e:
            print(f"[DocumentLoader] Error loading scraped file {filename}: {e}")
            continue
    
    print(f"[DocumentLoader] Successfully loaded {len(scraped_docs)} scraped documents")
    return scraped_docs