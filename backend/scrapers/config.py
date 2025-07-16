"""
Scraper Configuration Module

Contains all configuration settings for the UNSW handbook scrapers.
"""

import os
from typing import Dict, List

class ScraperConfig:
    """Central configuration for all scraper components"""
    
    # Base directories
    BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    RAG_DIR = os.path.join(BACKEND_DIR, "rag")
    SCRAPED_CONTENT_DIR = os.path.join(RAG_DIR, "scraped_content")
    
    # File paths
    URLS_FILE = os.path.join(SCRAPED_CONTENT_DIR, "urls.txt")
    CONTENT_DIR = os.path.join(SCRAPED_CONTENT_DIR, "content")
    METADATA_FILE = os.path.join(SCRAPED_CONTENT_DIR, "metadata.json")
    
    # Chrome WebDriver settings
    CHROME_OPTIONS = {
        "headless": True,
        "no_sandbox": True,
        "disable_dev_shm_usage": True,
        "disable_gpu": True,
        "window_size": "1920,1080"
    }
    
    # Scraping settings
    PAGE_LOAD_TIMEOUT = 10
    ELEMENT_WAIT_TIMEOUT = 5
    REQUEST_DELAY = 2  # seconds between requests
    RETRY_ATTEMPTS = 3
    
    # URL patterns for UNSW handbook
    UNSW_BASE_URL = "https://www.handbook.unsw.edu.au"
    CSE_BROWSE_URLS = [
        "https://www.handbook.unsw.edu.au/browse/By%20Area%20of%20Interest/InformationTechnology"
    ]
    
    # Content filtering settings
    MIN_CONTENT_LENGTH = 50
    MAX_CONTENT_LENGTH = 50000
    EXCLUDED_SECTIONS = [
        "navigation", "breadcrumb", "footer", "header",
        "sidebar", "menu", "search", "filter"
    ]
    
    # File management
    BACKUP_ENABLED = True
    MAX_BACKUP_FILES = 5
    
    @classmethod
    def ensure_directories(cls):
        """Ensure all necessary directories exist"""
        for directory in [cls.SCRAPED_CONTENT_DIR, cls.CONTENT_DIR]:
            os.makedirs(directory, exist_ok=True)
    
    @classmethod
    def get_content_filepath(cls, url: str) -> str:
        """Generate filepath for content based on URL"""
        # Create a safe filename from URL
        safe_name = url.replace("https://", "").replace("http://", "")
        safe_name = safe_name.replace("/", "_").replace("?", "_").replace("=", "_")
        safe_name = safe_name.strip("_")[:100]  # Limit filename length
        return os.path.join(cls.CONTENT_DIR, f"{safe_name}.json")

# Global config instance
config = ScraperConfig()