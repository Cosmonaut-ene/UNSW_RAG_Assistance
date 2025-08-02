"""
Scraped Content Manager - 统一管理scraped content的增删改查
Manages the lifecycle of scraped content including URLs, JSON files, and vector store chunks
"""

import os
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Set
from urllib.parse import urlparse

from scrapers.services.scraping_service import start_scraping_with_progress, get_scraping_progress
from scrapers.utils.file_utils import slugify_url


class ScrapedContentManager:
    """统一管理scraped content的增删改查"""
    
    def __init__(self, base_path: str = None):
        """Initialize with scraped content base path"""
        if base_path is None:
            # Use centralized path configuration
            from config.paths import PathConfig
            base_path = PathConfig.SCRAPED_CONTENT_DIR
        
        self.base_path = Path(base_path)
        self.urls_file = self.base_path / "urls.txt"
        self.metadata_file = self.base_path / "metadata.json"
        self.content_dir = self.base_path / "content"
        
        # Ensure directories exist
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.content_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_urls(self) -> Set[str]:
        """Load URLs from urls.txt"""
        if not self.urls_file.exists():
            return set()
        
        urls = set()
        with open(self.urls_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    urls.add(line)
        return urls
    
    def _save_urls(self, urls: Set[str]) -> None:
        """Save URLs to urls.txt"""
        with open(self.urls_file, 'w', encoding='utf-8') as f:
            f.write("# UNSW Handbook URLs for scraping\n")
            f.write(f"# Updated: {datetime.now().isoformat()}\n\n")
            for url in sorted(urls):
                f.write(f"{url}\n")
    
    def _load_metadata(self) -> Dict:
        """Load metadata.json"""
        if not self.metadata_file.exists():
            return {
                "scraped_urls": [],
                "last_scraping": None,
                "total_scraped": 0
            }
        
        with open(self.metadata_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_metadata(self, metadata: Dict) -> None:
        """Save metadata.json"""
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    def _get_json_filename(self, url: str) -> str:
        """Get JSON filename for a given URL"""
        return f"{slugify_url(url)}.json"
    
    def _remove_json_files(self, urls: List[str]) -> List[str]:
        """Remove JSON files for given URLs, return list of removed files"""
        removed_files = []
        
        for url in urls:
            json_filename = self._get_json_filename(url)
            json_path = self.content_dir / json_filename
            
            if json_path.exists():
                json_path.unlink()
                removed_files.append(json_filename)
        
        return removed_files
    
    def _remove_from_vector_store(self, urls: List[str]) -> Dict:
        """Remove chunks from vector store based on source URLs"""
        try:
            # Import here to avoid circular dependencies
            from rag import remove_documents_by_source
            
            removed_count = 0
            for url in urls:
                count = remove_documents_by_source(url)
                removed_count += count
            
            return {
                "success": True,
                "removed_chunks": removed_count,
                "removed_urls": urls
            }
        except ImportError:
            return {
                "success": False,
                "error": "Vector store removal function not available",
                "removed_chunks": 0
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Vector store removal failed: {str(e)}",
                "removed_chunks": 0
            }
    
    def add_links(self, urls: List[str], auto_update_vector_store: bool = True) -> Dict:
        """
        添加新链接并爬取内容
        
        Args:
            urls: List of URLs to add
            auto_update_vector_store: Whether to automatically update vector store
        
        Returns:
            Dict with operation status and results
        """
        if not urls:
            return {"success": False, "error": "No URLs provided"}
        
        # Validate URLs
        valid_urls = []
        invalid_urls = []
        
        for url in urls:
            try:
                parsed = urlparse(url)
                if parsed.scheme and parsed.netloc:
                    valid_urls.append(url.strip())
                else:
                    invalid_urls.append(url)
            except Exception:
                invalid_urls.append(url)
        
        if not valid_urls:
            return {
                "success": False,
                "error": "No valid URLs provided",
                "invalid_urls": invalid_urls
            }
        
        # Load current URLs
        current_urls = self._load_urls()
        
        # Find new URLs (not already present)
        new_urls = [url for url in valid_urls if url not in current_urls]
        existing_urls = [url for url in valid_urls if url in current_urls]
        
        if not new_urls:
            return {
                "success": True,
                "message": "All URLs already exist",
                "existing_urls": existing_urls,
                "new_urls": []
            }
        
        # Update urls.txt
        updated_urls = current_urls.union(set(new_urls))
        self._save_urls(updated_urls)
        
        # Start scraping process with vector store update flag
        scraping_id = start_scraping_with_progress(new_urls, auto_update_vector_store)
        
        return {
            "success": True,
            "message": f"Added {len(new_urls)} new URLs, scraping started",
            "new_urls": new_urls,
            "existing_urls": existing_urls,
            "invalid_urls": invalid_urls,
            "scraping_id": scraping_id,
            "auto_update_vector_store": auto_update_vector_store,
            "total_urls": len(updated_urls)
        }
    
    def remove_links(self, urls: List[str], update_vector_store: bool = True) -> Dict:
        """
        删除链接及相关内容
        
        Args:
            urls: List of URLs to remove
            update_vector_store: Whether to remove from vector store
        
        Returns:
            Dict with operation status and results
        """
        if not urls:
            return {"success": False, "error": "No URLs provided"}
        
        # Load current URLs
        current_urls = self._load_urls()
        
        # Find URLs that actually exist
        existing_urls = [url for url in urls if url in current_urls]
        non_existing_urls = [url for url in urls if url not in current_urls]
        
        if not existing_urls:
            return {
                "success": True,
                "message": "No URLs to remove",
                "removed_urls": [],
                "non_existing_urls": non_existing_urls
            }
        
        # Remove from urls.txt
        updated_urls = current_urls - set(existing_urls)
        self._save_urls(updated_urls)
        
        # Remove JSON files
        removed_files = self._remove_json_files(existing_urls)
        
        # Schedule async incremental vector store update if requested
        vector_update_task_id = None
        if update_vector_store:
            from services.async_vectorstore_updater import schedule_vectorstore_update
            vector_update_task_id = schedule_vectorstore_update(
                f"scraped_content_removed_{len(existing_urls)}_urls", 
                include_scraped=True
            )
        
        # Update metadata
        metadata = self._load_metadata()
        metadata["scraped_urls"] = [url for url in metadata.get("scraped_urls", []) 
                                   if url not in existing_urls]
        metadata["total_scraped"] = len(metadata["scraped_urls"])
        self._save_metadata(metadata)
        
        return {
            "success": True,
            "message": f"Removed {len(existing_urls)} URLs and their content",
            "removed_urls": existing_urls,
            "non_existing_urls": non_existing_urls,
            "removed_files": removed_files,
            "vector_update_task_id": vector_update_task_id,
            "remaining_urls": len(updated_urls)
        }
    
    def update_links(self, urls: List[str] = None, auto_update_vector_store: bool = True) -> Dict:
        """
        重新爬取指定链接（或所有链接）
        
        Args:
            urls: List of URLs to update (None = update all)
            auto_update_vector_store: Whether to automatically update vector store
        
        Returns:
            Dict with operation status and results
        """
        current_urls = self._load_urls()
        
        if urls is None:
            # Update all URLs
            urls_to_update = list(current_urls)
        else:
            # Update only specified URLs that exist
            urls_to_update = [url for url in urls if url in current_urls]
        
        if not urls_to_update:
            return {
                "success": False,
                "error": "No valid URLs to update",
                "available_urls": list(current_urls)
            }
        
        # Remove existing content for these URLs
        self._remove_json_files(urls_to_update)
        
        # Start scraping process with vector store update flag
        scraping_id = start_scraping_with_progress(urls_to_update, auto_update_vector_store)
        
        return {
            "success": True,
            "message": f"Started updating {len(urls_to_update)} URLs",
            "updated_urls": urls_to_update,
            "scraping_id": scraping_id,
            "auto_update_vector_store": auto_update_vector_store
        }
    
    def get_content_status(self) -> Dict:
        """
        获取当前内容状态统计
        
        Returns:
            Dict with comprehensive status information
        """
        # Load current data
        current_urls = self._load_urls()
        metadata = self._load_metadata()
        
        # Check JSON files
        json_files = []
        total_content_size = 0
        
        if self.content_dir.exists():
            for json_file in self.content_dir.glob("*.json"):
                try:
                    file_size = json_file.stat().st_size
                    total_content_size += file_size
                    
                    # Try to extract URL from filename or content
                    with open(json_file, 'r', encoding='utf-8') as f:
                        content = json.load(f)
                        source_url = content.get("metadata", {}).get("source", "")
                    
                    json_files.append({
                        "filename": json_file.name,
                        "size": file_size,
                        "source_url": source_url,
                        "modified": datetime.fromtimestamp(json_file.stat().st_mtime).isoformat()
                    })
                except Exception as e:
                    json_files.append({
                        "filename": json_file.name,
                        "error": str(e)
                    })
        
        # Check for orphaned files (JSON files without corresponding URL)
        scraped_urls = set(metadata.get("scraped_urls", []))
        json_source_urls = {f.get("source_url") for f in json_files if f.get("source_url")}
        orphaned_json = json_source_urls - scraped_urls
        missing_json = scraped_urls - json_source_urls
        
        # Vector store status (if available)
        vector_store_status = self._get_vector_store_status()
        
        return {
            "urls": {
                "total_in_urls_txt": len(current_urls),
                "total_scraped": metadata.get("total_scraped", 0),
                "last_scraping": metadata.get("last_scraping"),
                "urls_list": list(current_urls)
            },
            "files": {
                "total_json_files": len(json_files),
                "total_content_size": total_content_size,
                "content_directory": str(self.content_dir),
                "json_files": json_files
            },
            "consistency": {
                "orphaned_json_files": len(orphaned_json),
                "missing_json_files": len(missing_json),
                "orphaned_sources": list(orphaned_json),
                "missing_sources": list(missing_json)
            },
            "vector_store": vector_store_status,
            "paths": {
                "urls_file": str(self.urls_file),
                "metadata_file": str(self.metadata_file),
                "content_directory": str(self.content_dir)
            }
        }
    
    def _get_vector_store_status(self) -> Dict:
        """Get vector store status if available"""
        try:
            from rag import get_vector_store_info
            return get_vector_store_info()
        except ImportError:
            return {"available": False, "error": "Vector store functions not available"}
        except Exception as e:
            return {"available": False, "error": str(e)}
    
    def get_scraping_status(self, scraping_id: str) -> Optional[Dict]:
        """Get status of ongoing scraping operation"""
        return get_scraping_progress(scraping_id)
    
    def cleanup_orphaned_content(self) -> Dict:
        """Clean up orphaned JSON files and inconsistencies"""
        status = self.get_content_status()
        
        # Remove orphaned JSON files
        orphaned_sources = status["consistency"]["orphaned_sources"]
        removed_files = []
        
        for source_url in orphaned_sources:
            json_filename = self._get_json_filename(source_url)
            json_path = self.content_dir / json_filename
            
            if json_path.exists():
                json_path.unlink()
                removed_files.append(json_filename)
        
        # Schedule async incremental vector store update to clean up orphaned chunks
        vector_update_task_id = None
        if orphaned_sources:
            from services.async_vectorstore_updater import schedule_vectorstore_update
            vector_update_task_id = schedule_vectorstore_update(
                f"scraped_content_cleanup_{len(orphaned_sources)}_sources", 
                include_scraped=True
            )
        
        return {
            "success": True,
            "removed_files": removed_files,
            "vector_update_task_id": vector_update_task_id,
            "message": f"Cleaned up {len(removed_files)} orphaned files"
        }


# Convenience functions for backward compatibility and easy access
def add_scraped_links(urls: List[str]) -> Dict:
    """Add new links to scraping list"""
    manager = ScrapedContentManager()
    return manager.add_links(urls)

def remove_scraped_links(urls: List[str]) -> Dict:
    """Remove links and their content"""
    manager = ScrapedContentManager()
    return manager.remove_links(urls)

def update_scraped_content(urls: List[str] = None) -> Dict:
    """Update scraped content for specified URLs"""
    manager = ScrapedContentManager()
    return manager.update_links(urls)

def get_scraped_content_status() -> Dict:
    """Get current scraped content status"""
    manager = ScrapedContentManager()
    return manager.get_content_status()