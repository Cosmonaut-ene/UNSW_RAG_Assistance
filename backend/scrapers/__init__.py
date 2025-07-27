"""
UNSW Handbook Scrapers Module

This module provides functionality for:
1. Link discovery from UNSW handbook browse pages
2. Single page content scraping
3. Link change monitoring
4. Integration with RAG vector store

Restructured into services, utils, and core modules for better maintainability.
All existing APIs remain backward compatible.

Author: AI Assistant
"""

# Import from new structured modules for backward compatibility
from .services.discovery_service import (
    discover_cse_links,
    discover_cse_links_with_preview,
    discover_and_save_cse_links
)
from .services.scraping_service import (
    scrape_single_page,
    scrape_urls_batch,
    start_scraping_with_progress,
    get_scraping_progress,
    cancel_scraping_session
)
from .services.monitoring_service import (
    check_links_changed,
    get_new_links,
    get_scraping_status,
    monitor_and_scrape,
    cleanup_orphaned_content,
    update_scraping_metadata
)
from .utils.file_utils import (
    save_links_to_file,
    load_links_from_file,
    save_document_to_file as save_page_content,
    load_document_from_file as load_page_content
)
from .config import config as ScraperConfig

__all__ = [
    # Discovery functions
    'discover_cse_links',
    'discover_cse_links_with_preview',
    'discover_and_save_cse_links',
    
    # Scraping functions
    'scrape_single_page',
    'scrape_urls_batch',
    'start_scraping_with_progress',
    'get_scraping_progress',
    'cancel_scraping_session',
    
    # Monitoring functions
    'check_links_changed',
    'get_new_links',
    'get_scraping_status',
    'monitor_and_scrape',
    'cleanup_orphaned_content',
    'update_scraping_metadata',
    
    # File operations
    'save_links_to_file', 
    'load_links_from_file',
    'save_page_content',
    'load_page_content',
    
    # Configuration
    'ScraperConfig'
]