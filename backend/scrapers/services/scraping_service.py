"""
Content scraping service - extracting and processing content from UNSW handbook pages
"""

import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from threading import Thread
from bs4 import BeautifulSoup
from langchain.docstore.document import Document

from ..core.base import BaseScraper, BaseDocumentProcessor
from ..core.exceptions import ContentParsingError, NetworkError
from ..core.types import ScrapingResult, ProcessingOptions, ProgressInfo, ScrapingStatus
from ..config import config
from ..utils.web_utils import make_request_with_retry, add_random_delay
from ..utils.content_utils import (
    build_semantic_document,
    chunk_structured_content
)
from ..utils.file_utils import save_document_to_file

class UNSWContentScrapingService(BaseScraper, BaseDocumentProcessor):
    """Service for scraping content from UNSW handbook pages"""
    
    def scrape_links(self, root_url: str) -> Dict[str, List[str]]:
        """Not implemented for scraping service"""
        raise NotImplementedError("Scraping service doesn't discover links")
    
    def scrape_content(self, url: str, options: ProcessingOptions) -> Optional[ScrapingResult]:
        """Scrape content from a single URL"""
        print(f"🔍 Scraping structured page: {url}")

        # Use robust request function with retries
        response = make_request_with_retry(url, max_retries=options.max_retries)
        if not response:
            return ScrapingResult(
                url=url,
                success=False,
                error_message="Failed to fetch page after retries"
            )

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            script_tag = soup.find("script", id="__NEXT_DATA__")
            if not script_tag:
                raise ContentParsingError("__NEXT_DATA__ script tag not found")
        except Exception as e:
            return ScrapingResult(
                url=url,
                success=False,
                error_message=f"HTML parsing failed: {e}"
            )

        try:
            next_data = json.loads(script_tag.string)
            page_props = next_data.get("props", {}).get("pageProps", {})

            # Merge multiple possible content fields
            merged_content = {}

            # 1. pageContent
            pc = page_props.get("pageContent")
            if isinstance(pc, dict):
                merged_content.update(pc)
            elif isinstance(pc, str):
                print("⚠️ pageContent is string, possibly error message:", pc[:100])

            # 2. program (some page structures)
            pg = page_props.get("program")
            if isinstance(pg, dict):
                merged_content.update(pg)

            # 3. programData (some pages)
            pd = page_props.get("programData")
            if isinstance(pd, dict):
                merged_content.update(pd)

            # 4. metadata (supplementary information)
            meta = page_props.get("metadata")
            if isinstance(meta, dict):
                merged_content.update(meta)

            if not merged_content:
                return ScrapingResult(
                    url=url,
                    success=False,
                    error_message="No structured content found"
                )

            if options.use_chunking:
                # Process into chunks
                chunks = self.process_into_chunks(merged_content, url)
                if options.save_content:
                    for doc in chunks:
                        save_document_to_file(doc)
                return ScrapingResult(
                    url=url,
                    success=True,
                    chunks_count=len(chunks)
                )
            else:
                # Process as single document
                doc = self.process_structured_data(merged_content, url)
                if not doc:
                    return ScrapingResult(
                        url=url,
                        success=False,
                        error_message="Failed to generate semantic document"
                    )
                
                if options.save_content:
                    save_document_to_file(doc)
                
                return ScrapingResult(
                    url=url,
                    success=True,
                    content_data={
                        "url": url,
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "content_length": len(doc.page_content),
                        "scraped_at": datetime.utcnow().isoformat()
                    }
                )

        except Exception as e:
            return ScrapingResult(
                url=url,
                success=False,
                error_message=f"Content processing failed: {e}"
            )
    
    def batch_scrape(self, urls: List[str], options: ProcessingOptions) -> List[ScrapingResult]:
        """Scrape content from multiple URLs"""
        results = []
        failed = []

        print(f"🚀 Scraping {len(urls)} UNSW handbook pages with anti-blocking measures")
        print(f"⏱️ Using random delays between {options.delay_range[0]}-{options.delay_range[1]}s")

        for i, url in enumerate(urls):
            print(f"\n[{i+1}/{len(urls)}] {url}")
            
            # Add delay between requests (except for first request)
            if i > 0:
                add_random_delay(options.delay_range[0], options.delay_range[1])
            
            result = self.scrape_content(url, options)
            if result and result.success:
                results.append(result)
                if options.use_chunking:
                    print(f"✅ Successfully scraped {result.chunks_count} chunks from: {url}")
                else:
                    print(f"✅ Successfully scraped: {url}")
            else:
                failed.append(url)
                results.append(result)  # Include failed results too
                print(f"❌ Failed to scrape: {url}")

        print(f"\n🎯 Batch Results: {len([r for r in results if r.success])} success, ❌ {len(failed)} failed")
        
        if failed:
            print("\n❌ Failed URLs:")
            for url in failed:
                print(f"   - {url}")
        
        return results
    
    def process_structured_data(self, data: Dict[str, Any], url: str) -> Optional[Document]:
        """Process structured data into a single document"""
        from ..utils.content_utils import rename_top_level_keys
        data = rename_top_level_keys(data)
        doc = build_semantic_document(data, [], url)
        if not doc:
            return None
        
        # Add essential metadata
        doc.metadata.update({
            "source": url,
            "title": data.get("title", ""),
            "code": data.get("code", ""),
            "content_type": data.get("contentTypeLabel", ""),
            "scraped_at": datetime.utcnow().isoformat(),
            "content_length": len(doc.page_content),
        })
        
        return doc
    
    def process_into_chunks(self, data: Dict[str, Any], url: str) -> List[Document]:
        """Process structured data into multiple document chunks"""
        return chunk_structured_content(data, url)
    
    def clean_content(self, content: Any) -> str:
        """Clean and normalize content - handled by content_utils"""
        from ..utils.content_utils import clean_text
        return clean_text(str(content))

# Global storage for scraping progress (in production, use Redis or database)
_scraping_sessions = {}

def start_scraping_with_progress(urls: List[str], auto_update_vector_store: bool = True) -> str:
    """
    Start scraping with progress tracking and return a session ID
    """
    scraping_id = str(uuid.uuid4())[:8]
    
    # Initialize progress tracking
    _scraping_sessions[scraping_id] = {
        "status": "starting",
        "total_urls": len(urls),
        "completed": 0,
        "failed": 0,
        "current_url": None,
        "completed_urls": [],
        "failed_urls": [],
        "start_time": datetime.now().isoformat(),
        "estimated_completion": None,
        "cancelled": False,
        "statistics": {
            "success_rate": 0,
            "average_content_length": 0
        }
    }
    
    # Start scraping in background thread
    def scrape_with_progress():
        try:
            session = _scraping_sessions[scraping_id]
            session["status"] = "running"
            
            service = UNSWContentScrapingService()
            options = ProcessingOptions(save_content=True)
            total_content_length = 0
            
            for i, url in enumerate(urls):
                # Check if cancelled
                if session.get("cancelled"):
                    session["status"] = "cancelled"
                    return
                
                # Update current progress
                session["current_url"] = url
                session["status"] = f"scraping_{i+1}_of_{len(urls)}"
                
                # Estimate completion time
                if i > 0:
                    elapsed = (datetime.now() - datetime.fromisoformat(session["start_time"])).total_seconds()
                    avg_time_per_url = elapsed / i
                    remaining_time = avg_time_per_url * (len(urls) - i)
                    session["estimated_completion"] = (datetime.now().timestamp() + remaining_time)
                
                # Add delay between requests
                if i > 0:
                    add_random_delay(2.0, 4.0)
                
                # Scrape single page
                result = service.scrape_content(url, options)
                if result and result.success:
                    session["completed_urls"].append({
                        "url": url,
                        "title": result.content_data.get("metadata", {}).get("title", "Unknown") if result.content_data else "Unknown",
                        "content_length": result.content_data.get("content_length", 0) if result.content_data else 0
                    })
                    if result.content_data:
                        total_content_length += result.content_data.get("content_length", 0)
                else:
                    session["failed_urls"].append(url)
                
                # Update counters
                session["completed"] = len(session["completed_urls"])
                session["failed"] = len(session["failed_urls"])
                session["statistics"]["success_rate"] = (session["completed"] / (i + 1)) * 100
                
                if session["completed"] > 0:
                    session["statistics"]["average_content_length"] = total_content_length // session["completed"]
            
            # Final status
            if not session.get("cancelled"):
                session["status"] = "completed"
                session["current_url"] = None
                
                # Auto-update vector store if requested
                if auto_update_vector_store and session["completed"] > 0:
                    session["status"] = "updating_vector_store"
                    try:
                        from rag import update_knowledge_base
                        update_knowledge_base(include_scraped=True)
                        session["vector_store_updated"] = True
                    except Exception as e:
                        print(f"Vector store update failed: {e}")
                        session["vector_store_updated"] = False
                
                session["status"] = "finished"
                
        except Exception as e:
            session["status"] = "error"
            session["error"] = str(e)
            print(f"Scraping error: {e}")
    
    # Start background thread
    thread = Thread(target=scrape_with_progress, daemon=True)
    thread.start()
    
    return scraping_id

def get_scraping_progress(scraping_id: str) -> Optional[Dict]:
    """Get current progress for a scraping session"""
    return _scraping_sessions.get(scraping_id)

def cancel_scraping_session(scraping_id: str) -> bool:
    """Cancel an ongoing scraping session"""
    if scraping_id in _scraping_sessions:
        _scraping_sessions[scraping_id]["cancelled"] = True
        _scraping_sessions[scraping_id]["status"] = "cancelling"
        return True
    return False

# Convenience functions for backward compatibility
def scrape_single_page(url: str, use_chunking: bool = False):
    """Scrape single page using the service"""
    service = UNSWContentScrapingService()
    options = ProcessingOptions(use_chunking=use_chunking, save_content=False)
    result = service.scrape_content(url, options)
    
    if not result or not result.success:
        return None if not use_chunking else []
    
    if use_chunking:
        # Return list of documents for chunking mode
        return service.process_into_chunks(result.content_data, url) if result.content_data else []
    else:
        # Return single document for non-chunking mode
        if result.content_data:
            return Document(
                page_content=result.content_data["content"],
                metadata=result.content_data["metadata"]
            )
        return None

def scrape_urls_batch(urls: List[str], save_content: bool = True, delay_range: tuple = (2.0, 5.0), use_chunking: bool = False) -> List[Document]:
    """Batch scrape URLs with anti-blocking measures"""
    service = UNSWContentScrapingService()
    options = ProcessingOptions(
        use_chunking=use_chunking,
        save_content=save_content,
        delay_range=delay_range
    )
    
    results = service.batch_scrape(urls, options)
    
    # Convert results back to Document list for backward compatibility
    docs = []
    for result in results:
        if result.success:
            if use_chunking:
                # For chunking, need to process again to get documents
                # This is a bit inefficient but maintains compatibility
                chunks = service.process_into_chunks(result.content_data, result.url) if result.content_data else []
                docs.extend(chunks)
            else:
                if result.content_data:
                    doc = Document(
                        page_content=result.content_data["content"],
                        metadata=result.content_data["metadata"]
                    )
                    docs.append(doc)
    
    return docs