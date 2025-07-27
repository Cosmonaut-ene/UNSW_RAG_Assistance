"""
Monitoring service - change detection, progress tracking, and status management
"""

import os
from typing import List, Set, Dict, Optional
from datetime import datetime

from ..core.base import BaseFileManager
from ..config import config
from ..utils.file_utils import (
    get_file_hash,
    load_metadata,
    save_metadata,
    load_links_from_file
)

class ScrapingMonitoringService(BaseFileManager):
    """Service for monitoring scraping progress and detecting changes"""
    
    def save_links(self, links, filepath: str) -> None:
        """Save links to file"""
        from ..utils.file_utils import save_links_to_file
        save_links_to_file(links, filepath)
    
    def load_links(self, filepath: str) -> List[str]:
        """Load links from file"""
        return load_links_from_file(filepath)
    
    def save_content(self, document, content_dir: str) -> str:
        """Save document content to file"""
        from ..utils.file_utils import save_document_to_file
        return save_document_to_file(document, content_dir)
    
    def load_content(self, filepath: str):
        """Load document content from file"""
        from ..utils.file_utils import load_document_from_file
        return load_document_from_file(filepath)
    
    def get_file_hash(self, filepath: str) -> Optional[str]:
        """Get hash of file for change detection"""
        return get_file_hash(filepath)
    
    def check_links_changed(self, urls_file: str = None) -> bool:
        """Check if the links file has changed since last check"""
        if urls_file is None:
            urls_file = config.URLS_FILE
        
        # Get current file hash
        current_hash = self.get_file_hash(urls_file)
        if current_hash is None:
            print(f"⚠️  URLs file not found: {urls_file}")
            return False
        
        # Load metadata to get stored hash
        metadata = load_metadata()
        stored_hash = metadata.get("urls_file_hash")
        
        # Check if hash changed
        changed = current_hash != stored_hash
        
        if changed:
            print(f"🔄 URLs file has changed")
            # Update stored hash
            metadata["urls_file_hash"] = current_hash
            metadata["last_checked"] = datetime.now().isoformat()
            save_metadata(metadata)
        else:
            print(f"✅ URLs file unchanged")
        
        return changed
    
    def get_scraped_urls(self) -> Set[str]:
        """Get set of URLs that have already been scraped"""
        scraped_urls = set()
        
        if not os.path.exists(config.CONTENT_DIR):
            return scraped_urls
        
        # Check all JSON files in content directory
        for filename in os.listdir(config.CONTENT_DIR):
            if filename.endswith('.json'):
                filepath = os.path.join(config.CONTENT_DIR, filename)
                try:
                    import json
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        source_url = data.get("metadata", {}).get("source")
                        if source_url:
                            scraped_urls.add(source_url)
                except Exception as e:
                    print(f"⚠️  Error reading {filename}: {e}")
        
        return scraped_urls
    
    def get_new_links(self, urls_file: str = None) -> List[str]:
        """Get list of URLs that need to be scraped"""
        if urls_file is None:
            urls_file = config.URLS_FILE
        
        # Load all URLs from file
        all_urls = self.load_links(urls_file)
        if not all_urls:
            print("⚠️  No URLs found in file")
            return []
        
        # Get already scraped URLs
        scraped_urls = self.get_scraped_urls()
        
        # Find new URLs
        new_urls = [url for url in all_urls if url not in scraped_urls]
        
        print(f"📊 URL Status:")
        print(f"   Total URLs: {len(all_urls)}")
        print(f"   Already scraped: {len(scraped_urls)}")
        print(f"   New/pending: {len(new_urls)}")
        
        return new_urls
    
    def get_scraping_status(self) -> Dict:
        """Get comprehensive status of scraping progress"""
        all_urls = self.load_links()
        scraped_urls = self.get_scraped_urls()
        new_urls = self.get_new_links()
        metadata = load_metadata()
        
        # Categorize URLs by type
        url_types = {"programs": [], "specialisations": [], "courses": [], "other": []}
        for url in all_urls:
            if "/programs/" in url:
                url_types["programs"].append(url)
            elif "/specialisations/" in url:
                url_types["specialisations"].append(url)
            elif "/courses/" in url:
                url_types["courses"].append(url)
            else:
                url_types["other"].append(url)
        
        status = {
            "total_urls": len(all_urls),
            "scraped_count": len(scraped_urls),
            "pending_count": len(new_urls),
            "completion_rate": (len(scraped_urls) / len(all_urls) * 100) if all_urls else 0,
            "url_types": {
                "programs": {"total": len(url_types["programs"]), 
                            "scraped": len([u for u in url_types["programs"] if u in scraped_urls])},
                "specialisations": {"total": len(url_types["specialisations"]), 
                                   "scraped": len([u for u in url_types["specialisations"] if u in scraped_urls])},
                "courses": {"total": len(url_types["courses"]), 
                           "scraped": len([u for u in url_types["courses"] if u in scraped_urls])},
                "other": {"total": len(url_types["other"]), 
                         "scraped": len([u for u in url_types["other"] if u in scraped_urls])}
            },
            "last_checked": metadata.get("last_checked"),
            "urls_file_exists": os.path.exists(config.URLS_FILE),
            "content_dir_exists": os.path.exists(config.CONTENT_DIR)
        }
        
        return status
    
    def cleanup_orphaned_content(self) -> List[str]:
        """Remove content files for URLs that are no longer in the links file"""
        if not os.path.exists(config.CONTENT_DIR):
            return []
        
        current_urls = set(self.load_links())
        scraped_urls = self.get_scraped_urls()
        
        # Find orphaned files (scraped but not in current URL list)
        orphaned_urls = scraped_urls - current_urls
        removed_files = []
        
        for url in orphaned_urls:
            filepath = config.get_content_filepath(url)
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    removed_files.append(filepath)
                    print(f"🗑️  Removed orphaned content: {filepath}")
                except Exception as e:
                    print(f"❌ Error removing {filepath}: {e}")
        
        if removed_files:
            print(f"✅ Cleaned up {len(removed_files)} orphaned files")
        else:
            print("✅ No orphaned files found")
        
        return removed_files
    
    def update_scraping_metadata(self, scraped_urls: List[str]):
        """Update metadata with information about newly scraped URLs"""
        metadata = load_metadata()
        
        # Update scraped URLs list
        if "scraped_urls" not in metadata:
            metadata["scraped_urls"] = []
        
        for url in scraped_urls:
            if url not in metadata["scraped_urls"]:
                metadata["scraped_urls"].append(url)
        
        # Update timestamps
        metadata["last_scraping"] = datetime.now().isoformat()
        metadata["total_scraped"] = len(metadata["scraped_urls"])
        
        save_metadata(metadata)
        print(f"📝 Updated metadata: {len(scraped_urls)} new URLs scraped")
    
    def monitor_and_scrape(self, auto_scrape: bool = False) -> Dict:
        """Main monitoring function that checks for changes and optionally triggers scraping"""
        print("🔍 Starting link monitoring...")
        
        # Check if links file changed
        links_changed = self.check_links_changed()
        
        # Get current status
        status = self.get_scraping_status()
        
        # Get new URLs to scrape
        new_urls = self.get_new_links()
        
        result = {
            "links_changed": links_changed,
            "status": status,
            "new_urls_count": len(new_urls),
            "auto_scrape_enabled": auto_scrape,
            "scraping_triggered": False
        }
        
        if new_urls:
            print(f"📋 Found {len(new_urls)} URLs to scrape")
            
            if auto_scrape:
                print("🚀 Auto-scraping enabled, starting scrape...")
                try:
                    from .scraping_service import scrape_urls_batch
                    documents = scrape_urls_batch(new_urls, save_content=True)
                    successful_urls = [doc.metadata["source"] for doc in documents]
                    self.update_scraping_metadata(successful_urls)
                    
                    result["scraping_triggered"] = True
                    result["scraped_count"] = len(successful_urls)
                    result["failed_count"] = len(new_urls) - len(successful_urls)
                    
                    print(f"✅ Auto-scraping completed: {len(successful_urls)}/{len(new_urls)} successful")
                    
                except Exception as e:
                    print(f"❌ Auto-scraping failed: {e}")
                    result["scraping_error"] = str(e)
        else:
            print("✅ No new URLs to scrape")
        
        # Cleanup orphaned files if links changed
        if links_changed:
            self.cleanup_orphaned_content()
        
        return result

# Convenience functions for backward compatibility
def check_links_changed(urls_file: str = None) -> bool:
    """Check if the links file has changed since last check"""
    service = ScrapingMonitoringService()
    return service.check_links_changed(urls_file)

def get_new_links(urls_file: str = None) -> List[str]:
    """Get list of URLs that need to be scraped"""
    service = ScrapingMonitoringService()
    return service.get_new_links(urls_file)

def get_scraping_status() -> Dict:
    """Get comprehensive status of scraping progress"""
    service = ScrapingMonitoringService()
    return service.get_scraping_status()

def monitor_and_scrape(auto_scrape: bool = False) -> Dict:
    """Main monitoring function"""
    service = ScrapingMonitoringService()
    return service.monitor_and_scrape(auto_scrape)

def cleanup_orphaned_content() -> List[str]:
    """Remove content files for URLs that are no longer in the links file"""
    service = ScrapingMonitoringService()
    return service.cleanup_orphaned_content()

def update_scraping_metadata(scraped_urls: List[str]):
    """Update metadata with information about newly scraped URLs"""
    service = ScrapingMonitoringService()
    return service.update_scraping_metadata(scraped_urls)