"""
UNSW Handbook Scrapers Module

This module provides functionality for:
1. Link discovery from UNSW handbook browse pages
2. Single page content scraping
3. Link change monitoring
4. Integration with RAG vector store

Author: AI Assistant
"""

from .link_discovery import discover_cse_links, save_links_to_file, load_links_from_file
from .page_scraper import scrape_single_page, save_page_content, load_page_content
from .monitor import check_links_changed, get_new_links
from .config import ScraperConfig

__all__ = [
    'discover_cse_links',
    'save_links_to_file', 
    'load_links_from_file',
    'scrape_single_page',
    'save_page_content',
    'load_page_content',
    'check_links_changed',
    'get_new_links',
    'ScraperConfig'
]