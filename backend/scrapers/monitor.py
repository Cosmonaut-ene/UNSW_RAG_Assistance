"""
Link Change Monitor Module

Monitors changes in the links file and tracks scraping progress.
Provides functions to detect new links and manage incremental updates.
"""

import os
import json
import hashlib
from typing import List, Set, Dict, Tuple, Optional
from datetime import datetime

from .config import config

def get_file_hash(filepath: str) -> Optional[str]:
    """
    Get MD5 hash of a file for change detection.
    
    Args:
        filepath: Path to file
        
    Returns:
        MD5 hash string or None if file doesn't exist
    """
    if not os.path.exists(filepath):
        return None
    
    try:
        with open(filepath, 'rb') as f:
            content = f.read()
            return hashlib.md5(content).hexdigest()
    except Exception as e:
        print(f"❌ Error reading file {filepath}: {e}")
        return None


def load_metadata() -> Dict:
    """
    Load scraping metadata from JSON file.
    
    Returns:
        Dictionary with metadata or empty dict if file doesn't exist
    """
    if not os.path.exists(config.METADATA_FILE):
        return {}
    
    try:
        with open(config.METADATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading metadata: {e}")
        return {}


def save_metadata(metadata: Dict):
    """
    Save scraping metadata to JSON file.
    
    Args:
        metadata: Dictionary with metadata to save
    """
    # Ensure directory exists
    os.makedirs(os.path.dirname(config.METADATA_FILE), exist_ok=True)
    
    try:
        with open(config.METADATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"❌ Error saving metadata: {e}")


def check_links_changed(urls_file: str = None) -> bool:
    """
    Check if the links file has changed since last check.
    
    Args:
        urls_file: Path to URLs file (defaults to config.URLS_FILE)
        
    Returns:
        True if file has changed or is new, False otherwise
    """
    if urls_file is None:
        urls_file = config.URLS_FILE
    
    # Get current file hash
    current_hash = get_file_hash(urls_file)
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


def get_scraped_urls() -> Set[str]:
    """
    Get set of URLs that have already been scraped by checking content directory.
    
    Returns:
        Set of URLs that have been scraped
    """
    scraped_urls = set()
    
    if not os.path.exists(config.CONTENT_DIR):
        return scraped_urls
    
    # Check all JSON files in content directory
    for filename in os.listdir(config.CONTENT_DIR):
        if filename.endswith('.json'):
            filepath = os.path.join(config.CONTENT_DIR, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    source_url = data.get("metadata", {}).get("source")
                    if source_url:
                        scraped_urls.add(source_url)
            except Exception as e:
                print(f"⚠️  Error reading {filename}: {e}")
    
    return scraped_urls

def load_links_from_file(filepath: str = None) -> list:
    """Load links from file, using default config path if none provided"""
    if filepath is None:
        filepath = config.URLS_FILE
    
    if not os.path.exists(filepath):
        return []
        
    with open(filepath, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]

def get_new_links(urls_file: str = None) -> List[str]:
    """
    Get list of URLs that need to be scraped (new or not yet scraped).
    
    Args:
        urls_file: Path to URLs file (defaults to config.URLS_FILE)
        
    Returns:
        List of URLs that need scraping
    """
    if urls_file is None:
        urls_file = config.URLS_FILE
    
    # Load all URLs from file
    all_urls = load_links_from_file(urls_file)
    if not all_urls:
        print("⚠️  No URLs found in file")
        return []
    
    # Get already scraped URLs
    scraped_urls = get_scraped_urls()
    
    # Find new URLs
    new_urls = [url for url in all_urls if url not in scraped_urls]
    
    print(f"📊 URL Status:")
    print(f"   Total URLs: {len(all_urls)}")
    print(f"   Already scraped: {len(scraped_urls)}")
    print(f"   New/pending: {len(new_urls)}")
    
    return new_urls


def get_scraping_status() -> Dict:
    """
    Get comprehensive status of scraping progress.
    
    Returns:
        Dictionary with scraping status information
    """
    all_urls = load_links_from_file()
    scraped_urls = get_scraped_urls()
    new_urls = get_new_links()
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


def cleanup_orphaned_content() -> List[str]:
    """
    Remove content files for URLs that are no longer in the links file.
    
    Returns:
        List of removed file paths
    """
    if not os.path.exists(config.CONTENT_DIR):
        return []
    
    current_urls = set(load_links_from_file())
    scraped_urls = get_scraped_urls()
    
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


def update_scraping_metadata(scraped_urls: List[str]):
    """
    Update metadata with information about newly scraped URLs.
    
    Args:
        scraped_urls: List of URLs that were just scraped
    """
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


def monitor_and_scrape(auto_scrape: bool = False) -> Dict:
    """
    Main monitoring function that checks for changes and optionally triggers scraping.
    
    Args:
        auto_scrape: Whether to automatically scrape new URLs
        
    Returns:
        Dictionary with monitoring results
    """
    print("🔍 Starting link monitoring...")
    
    # Check if links file changed
    links_changed = check_links_changed()
    
    # Get current status
    status = get_scraping_status()
    
    # Get new URLs to scrape
    new_urls = get_new_links()
    
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
            # Import here to avoid circular imports
            from .page_scraper import scrape_urls_batch
            
            try:
                documents = scrape_urls_batch(new_urls, headless=True, save_content=True)
                successful_urls = [doc.metadata["source"] for doc in documents]
                update_scraping_metadata(successful_urls)
                
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
        cleanup_orphaned_content()
    
    return result


if __name__ == "__main__":
    # Example usage
    result = monitor_and_scrape(auto_scrape=False)
    print(f"\n📊 Monitoring Result:")
    print(json.dumps(result, indent=2, default=str))