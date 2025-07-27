"""
Service modules for scrapers - business logic and main functionality
"""

from .discovery_service import (
    UNSWLinkDiscoveryService,
    discover_cse_links,
    discover_cse_links_with_preview
)

from .scraping_service import (
    UNSWContentScrapingService,
    scrape_single_page,
    scrape_urls_batch,
    start_scraping_with_progress,
    get_scraping_progress,
    cancel_scraping_session
)

from .monitoring_service import (
    ScrapingMonitoringService,
    check_links_changed,
    get_new_links,
    get_scraping_status,
    monitor_and_scrape,
    cleanup_orphaned_content,
    update_scraping_metadata
)

__all__ = [
    # Discovery service
    'UNSWLinkDiscoveryService',
    'discover_cse_links',
    'discover_cse_links_with_preview',
    
    # Scraping service
    'UNSWContentScrapingService',
    'scrape_single_page',
    'scrape_urls_batch',
    'start_scraping_with_progress',
    'get_scraping_progress',
    'cancel_scraping_session',
    
    # Monitoring service
    'ScrapingMonitoringService',
    'check_links_changed',
    'get_new_links',
    'get_scraping_status',
    'monitor_and_scrape',
    'cleanup_orphaned_content',
    'update_scraping_metadata'
]