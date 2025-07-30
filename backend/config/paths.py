# config/paths.py
"""
Centralized path configuration for the UNSW CSE Chatbot system
"""

import os
from pathlib import Path

class PathConfig:
    """
    Centralized path configuration
    """
    
    # Base directories
    BACKEND_ROOT = Path(__file__).parent.parent.absolute()
    PROJECT_ROOT = BACKEND_ROOT.parent
    
    # Data root directory (can be overridden by environment variable)
    DATA_ROOT = Path(os.getenv('KNOWLEDGE_BASE_ROOT', PROJECT_ROOT / 'data' / 'knowledge_base'))
    
    # Knowledge base directories
    DOCUMENTS_DIR = Path(os.getenv('RAG_DOCUMENTS_DIR', DATA_ROOT / 'documents'))
    SCRAPED_CONTENT_DIR = Path(os.getenv('RAG_SCRAPED_CONTENT_DIR', DATA_ROOT / 'scraped_content'))
    VECTOR_STORE_DIR = Path(os.getenv('RAG_VECTOR_STORE_DIR', DATA_ROOT / 'vector_store'))
    LOGS_DIR = Path(os.getenv('RAG_LOGS_DIR', DATA_ROOT / 'logs'))
    
    # Scraped content subdirectories
    SCRAPED_CONTENT_FILES_DIR = SCRAPED_CONTENT_DIR / 'content'
    SCRAPED_METADATA_FILE = SCRAPED_CONTENT_DIR / 'metadata.json'
    SCRAPED_URLS_FILE = SCRAPED_CONTENT_DIR / 'urls.txt'
    
    # Vector store files
    VECTOR_STORE_SOURCE_TRACKING_FILE = VECTOR_STORE_DIR / 'source_files.txt'
    
    @classmethod
    def ensure_directories(cls) -> None:
        """Create all necessary directories"""
        directories = [
            cls.DATA_ROOT,
            cls.DOCUMENTS_DIR,
            cls.SCRAPED_CONTENT_DIR,
            cls.SCRAPED_CONTENT_FILES_DIR,
            cls.VECTOR_STORE_DIR,
            cls.LOGS_DIR
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def get_config_summary(cls) -> dict:
        """Get path configuration summary"""
        return {
            'data_root': str(cls.DATA_ROOT),
            'documents_dir': str(cls.DOCUMENTS_DIR),
            'scraped_content_dir': str(cls.SCRAPED_CONTENT_DIR),
            'vector_store_dir': str(cls.VECTOR_STORE_DIR),
            'logs_dir': str(cls.LOGS_DIR)
        }