# services/async_vectorstore_updater.py
"""
Asynchronous vector store updater for handling ChromaDB operations in background
"""

import threading
import time
import queue
from typing import Optional, Dict, Any, List
from datetime import datetime
import traceback
from langchain.docstore.document import Document

class AsyncVectorStoreUpdater:
    """
    Background thread manager specifically for vector store operations
    Handles ChromaDB updates asynchronously to avoid WSL2 permission conflicts
    """
    
    def __init__(self):
        self.update_queue = queue.Queue()
        self.worker_thread = None
        self.is_running = False
        self.current_update = None
        self.update_history = []
        self.max_history = 10
        
    def start(self):
        """Start the background vector store updater thread"""
        if self.is_running:
            return
            
        self.is_running = True
        self.worker_thread = threading.Thread(target=self._update_worker_loop, daemon=True)
        self.worker_thread.start()
        print("[AsyncVectorStore] Vector store updater started")
    
    def stop(self):
        """Stop the background updater thread"""
        self.is_running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=10)
        print("[AsyncVectorStore] Vector store updater stopped")
    
    def schedule_update(self, trigger_reason: str, include_scraped: bool = True) -> str:
        """
        Schedule a vector store update for background execution
        
        Args:
            trigger_reason: Reason for the update (e.g., "file_uploaded", "file_deleted")
            include_scraped: Whether to include scraped content
            
        Returns:
            str: Update task ID
        """
        update_id = f"vectorstore_update_{int(time.time())}"
        update_task = {
            'id': update_id,
            'trigger_reason': trigger_reason,
            'include_scraped': include_scraped,
            'scheduled_at': datetime.now(),
            'status': 'queued'
        }
        
        self.update_queue.put(update_task)
        print(f"[AsyncVectorStore] Scheduled update: {trigger_reason} (ID: {update_id})")
        return update_id
    
    def get_update_status(self, update_id: str) -> Optional[Dict]:
        """Get status of a specific vector store update"""
        # Check current update
        if self.current_update and self.current_update['id'] == update_id:
            return {
                'status': 'running',
                'trigger_reason': self.current_update['trigger_reason'],
                'started_at': self.current_update.get('started_at')
            }
        
        # Check history
        for update in self.update_history:
            if update['id'] == update_id:
                return {
                    'status': update['status'],
                    'trigger_reason': update['trigger_reason'],
                    'completed_at': update.get('completed_at'),
                    'error': update.get('error')
                }
        
        return None
    
    def get_queue_status(self) -> Dict:
        """Get overall vector store update queue status"""
        return {
            'queue_size': self.update_queue.qsize(),
            'current_update': self.current_update['trigger_reason'] if self.current_update else None,
            'is_running': self.is_running,
            'recent_updates': [
                {
                    'trigger_reason': u['trigger_reason'],
                    'status': u['status'],
                    'completed_at': u.get('completed_at')
                } for u in self.update_history[-5:]
            ] if self.update_history else []
        }
    
    def _update_worker_loop(self):
        """Main worker thread loop for vector store updates"""
        while self.is_running:
            try:
                # Get next update task (with timeout to allow clean shutdown)
                update_task = self.update_queue.get(timeout=1.0)
                self._execute_vector_store_update(update_task)
                self.update_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[AsyncVectorStore] Worker loop error: {e}")
                traceback.print_exc()
    
    def _execute_vector_store_update(self, update_task: Dict):
        """Execute a vector store update with WSL2 compatibility measures"""
        self.current_update = update_task
        update_task['started_at'] = datetime.now()
        update_task['status'] = 'running'
        
        try:
            print(f"[AsyncVectorStore] Starting update: {update_task['trigger_reason']}")
            
            # WSL2 filesystem sync delay - critical for avoiding readonly database errors
            print("[AsyncVectorStore] Waiting for filesystem sync...")
            time.sleep(3)
            
            # Force cleanup of any existing ChromaDB connections
            print("[AsyncVectorStore] Cleaning up existing connections...")
            try:
                import gc
                gc.collect()  # Force garbage collection to close any lingering connections
            except:
                pass
            
            # Use incremental updates to avoid ChromaDB rebuild issues
            result = self._execute_incremental_update(update_task)
            
            update_task['status'] = 'completed'
            update_task['completed_at'] = datetime.now()
            update_task['result'] = result
            
            print(f"[AsyncVectorStore] Update completed: {update_task['trigger_reason']}")
            
        except Exception as e:
            update_task['status'] = 'failed'
            update_task['completed_at'] = datetime.now()
            update_task['error'] = str(e)
            
            print(f"[AsyncVectorStore] Update failed: {update_task['trigger_reason']} - {e}")
            
            # For readonly database errors, retry only if not already a retry
            if "readonly database" in str(e).lower() and not update_task['trigger_reason'].startswith('retry_'):
                print("[AsyncVectorStore] Readonly database detected, scheduling ONE retry...")
                retry_id = self.schedule_update(f"retry_{update_task['trigger_reason']}", update_task['include_scraped'])
                update_task['retry_scheduled'] = retry_id
            else:
                print("[AsyncVectorStore] Max retries reached or non-retryable error, stopping retries")
        
        finally:
            # Move to history
            self._add_to_history(update_task)
            self.current_update = None
    
    def _execute_incremental_update(self, update_task: Dict) -> bool:
        """
        Execute incremental vector store update based on trigger reason
        
        Args:
            update_task: Task dictionary with trigger reason and metadata
            
        Returns:
            bool: True if successful
        """
        trigger_reason = update_task['trigger_reason']
        
        try:
            # Parse the trigger reason to determine operation and file
            if trigger_reason.startswith('file_uploaded_'):
                filename = trigger_reason[len('file_uploaded_'):]
                return self._handle_file_upload(filename)
                
            elif trigger_reason.startswith('file_deleted_'):
                filename = trigger_reason[len('file_deleted_'):]
                return self._handle_file_deletion(filename)
                
            elif trigger_reason.startswith('scraped_content_added_'):
                # Handle scraped content addition
                urls_info = trigger_reason[len('scraped_content_added_'):]
                return self._handle_scraped_content_added(urls_info)
                
            elif trigger_reason.startswith('scraped_content_removed_'):
                # Handle scraped content removal  
                urls_info = trigger_reason[len('scraped_content_removed_'):]
                return self._handle_scraped_content_removed(urls_info)
                
            elif trigger_reason.startswith('scraped_content_updated_'):
                # Handle scraped content update
                urls_info = trigger_reason[len('scraped_content_updated_'):]
                return self._handle_scraped_content_updated(urls_info)
                
            elif trigger_reason.startswith('retry_'):
                # Handle retry cases
                original_reason = trigger_reason[len('retry_'):]
                return self._execute_incremental_update({
                    'trigger_reason': original_reason,
                    'include_scraped': update_task['include_scraped']
                })
                
            else:
                # Fallback to incremental update of all content instead of full rebuild
                print(f"[AsyncVectorStore] Unknown trigger, attempting incremental update: {trigger_reason}")
                return self._handle_general_incremental_update()
                
        except Exception as e:
            print(f"[AsyncVectorStore] Incremental update failed: {e}")
            return False
    
    def _handle_file_upload(self, filename: str) -> bool:
        """Handle file upload with incremental update"""
        try:
            from rag.incremental_vectorstore import process_file_operation
            from config.paths import PathConfig
            
            file_path = PathConfig.DOCUMENTS_DIR / filename
            
            if not file_path.exists():
                print(f"[AsyncVectorStore] Uploaded file not found: {file_path}")
                return False
            
            # Check if vector store exists, create if not
            from rag.vector_store import validate_vector_database_exists
            if not validate_vector_database_exists():
                print("[AsyncVectorStore] No vector store exists, creating initial store...")
                return self._create_initial_vectorstore()
            
            # Incremental add
            success = process_file_operation('added', str(file_path))
            print(f"[AsyncVectorStore] File upload processed: {filename} - {'Success' if success else 'Failed'}")
            return success
            
        except Exception as e:
            print(f"[AsyncVectorStore] Error handling file upload: {e}")
            return False
    
    def _handle_file_deletion(self, filename: str) -> bool:
        """Handle file deletion with incremental update"""
        try:
            from rag.incremental_vectorstore import process_file_operation
            from config.paths import PathConfig
            
            file_path = PathConfig.DOCUMENTS_DIR / filename
            
            # Check if vector store exists
            from rag.vector_store import validate_vector_database_exists
            if not validate_vector_database_exists():
                print("[AsyncVectorStore] No vector store exists, nothing to delete")
                return True  # Nothing to delete is considered success
            
            # Incremental delete
            success = process_file_operation('deleted', str(file_path))
            print(f"[AsyncVectorStore] File deletion processed: {filename} - {'Success' if success else 'Failed'}")
            return success
            
        except Exception as e:
            print(f"[AsyncVectorStore] Error handling file deletion: {e}")
            return False
    
    def _handle_scraped_content_added(self, urls_info: str) -> bool:
        """Handle scraped content addition with URL-specific processing"""
        try:
            from rag.vector_store import validate_vector_database_exists
            from rag.text_splitter import split_documents_by_content_type
            from rag.incremental_vectorstore import add_documents_to_vectorstore
            
            # Check if vector store exists, create if not
            if not validate_vector_database_exists():
                print("[AsyncVectorStore] No vector store exists, creating initial store...")
                return self._create_initial_vectorstore()
            
            # Parse URL list from trigger
            if '|' in urls_info:
                # Multiple URLs separated by |
                target_urls = [url.strip() for url in urls_info.split('|') if url.strip()]
            elif urls_info.strip():
                # Single URL
                target_urls = [urls_info.strip()]
            else:
                print(f"[AsyncVectorStore] Empty URL info in trigger: {urls_info}")
                return False
            
            print(f"[AsyncVectorStore] Processing {len(target_urls)} specific URLs for addition")
            
            # Load documents only for these specific URLs
            target_docs = self._load_documents_by_urls(target_urls)
            
            if not target_docs:
                print("[AsyncVectorStore] No documents found for target URLs")
                return True
            
            # Split documents into chunks
            chunks = split_documents_by_content_type(target_docs)
            
            # Add incrementally to vector store
            success = add_documents_to_vectorstore(chunks, f"scraped_urls_batch_{len(target_urls)}")
            
            print(f"[AsyncVectorStore] Scraped content addition: {'Success' if success else 'Failed'} - Added {len(chunks)} chunks from {len(target_urls)} URLs")
            return success
            
        except Exception as e:
            print(f"[AsyncVectorStore] Error handling scraped content addition: {e}")
            return False
    
    def _handle_scraped_content_removed(self, urls_info: str) -> bool:
        """Handle scraped content removal with URL-specific processing"""
        try:
            from rag.vector_store import validate_vector_database_exists, remove_documents_by_source
            
            if not validate_vector_database_exists():
                print("[AsyncVectorStore] No vector store exists, nothing to remove")
                return True
            
            # Parse URL list from trigger
            if '|' in urls_info:
                # Multiple URLs separated by |
                target_urls = [url.strip() for url in urls_info.split('|') if url.strip()]
            elif urls_info.strip():
                # Single URL
                target_urls = [urls_info.strip()]
            else:
                print(f"[AsyncVectorStore] Empty URL info in trigger: {urls_info}")
                return False
            
            print(f"[AsyncVectorStore] Processing removal of {len(target_urls)} specific URLs")
            
            # Remove documents for each specific URL
            removed_count = 0
            for url in target_urls:
                count = remove_documents_by_source(url)
                removed_count += count
                print(f"[AsyncVectorStore] Removed {count} documents for URL: {url}")
            
            print(f"[AsyncVectorStore] Scraped content removal completed: removed {removed_count} documents from {len(target_urls)} URLs")
            return True
            
        except Exception as e:
            print(f"[AsyncVectorStore] Error handling scraped content removal: {e}")
            return False
    
    def _handle_scraped_content_updated(self, urls_info: str = None) -> bool:
        """Handle scraped content update with incremental update"""
        try:
            from rag.vector_store import validate_vector_database_exists, remove_documents_by_source
            from rag.document_loader import load_scraped_documents
            from rag.text_splitter import split_documents_by_content_type
            from rag.incremental_vectorstore import add_documents_to_vectorstore
            from config.paths import PathConfig
            
            if not validate_vector_database_exists():
                print("[AsyncVectorStore] No vector store exists, creating initial store...")
                return self._create_initial_vectorstore()
            
            # Remove all existing scraped content from vector store
            print("[AsyncVectorStore] Removing existing scraped content...")
            # Get all scraped documents to find their sources
            scraped_docs = load_scraped_documents(str(PathConfig.SCRAPED_CONTENT_DIR))
            
            removed_count = 0
            processed_sources = set()
            for doc in scraped_docs:
                source = doc.metadata.get('source')
                if source and source not in processed_sources:
                    count = remove_documents_by_source(source)
                    removed_count += count
                    processed_sources.add(source)
            
            print(f"[AsyncVectorStore] Removed {removed_count} existing scraped documents")
            
            # Re-add current scraped content
            if scraped_docs:
                chunks = split_documents_by_content_type(scraped_docs)
                success = add_documents_to_vectorstore(chunks, "scraped_content_update")
                print(f"[AsyncVectorStore] Re-added {len(chunks)} scraped content chunks")
                return success
            else:
                print("[AsyncVectorStore] No scraped content to re-add")
                return True
            
        except Exception as e:
            print(f"[AsyncVectorStore] Error handling scraped content update: {e}")
            return False
    
    def _handle_general_incremental_update(self) -> bool:
        """Handle general incremental update without full rebuild"""
        try:
            print("[AsyncVectorStore] Performing general incremental update...")
            # For unknown triggers, just update scraped content incrementally
            return self._handle_scraped_content_updated()
            
        except Exception as e:
            print(f"[AsyncVectorStore] Error in general incremental update: {e}")
            return False

    def _load_documents_by_urls(self, target_urls: List[str]) -> List[Document]:
        """Load scraped documents only for specific URLs"""
        try:
            from rag.document_loader import load_scraped_documents
            from config.paths import PathConfig
            
            # Load all scraped documents
            all_docs = load_scraped_documents(str(PathConfig.SCRAPED_CONTENT_DIR))
            
            # Filter out only documents matching target URLs
            target_docs = []
            target_urls_set = set(target_urls)
            
            for doc in all_docs:
                source = doc.metadata.get('source')
                if source in target_urls_set:
                    target_docs.append(doc)
            
            print(f"[AsyncVectorStore] Loaded {len(target_docs)} documents for {len(target_urls)} target URLs")
            return target_docs
            
        except Exception as e:
            print(f"[AsyncVectorStore] Error loading documents by URLs: {e}")
            return []

    def _create_initial_vectorstore(self) -> bool:
        """Create initial vector store when none exists"""
        try:
            print("[AsyncVectorStore] Creating initial vector store...")
            from rag import update_knowledge_base
            return update_knowledge_base(include_scraped=True)
            
        except Exception as e:
            print(f"[AsyncVectorStore] Error creating initial vector store: {e}")
            return False

    def _add_to_history(self, update_task: Dict):
        """Add completed update to history"""
        self.update_history.append(update_task)
        
        # Limit history size
        if len(self.update_history) > self.max_history:
            self.update_history.pop(0)

# Global updater instance
vector_store_updater = AsyncVectorStoreUpdater()

def init_async_vectorstore_updater():
    """Initialize the async vector store updater"""
    vector_store_updater.start()

def shutdown_async_vectorstore_updater():
    """Shutdown the async vector store updater"""
    vector_store_updater.stop()

def schedule_vectorstore_update(trigger_reason: str, include_scraped: bool = True) -> str:
    """
    Schedule an asynchronous vector store update
    
    Args:
        trigger_reason: Reason for update (e.g., "file_uploaded", "file_deleted")
        include_scraped: Whether to include scraped content
        
    Returns:
        str: Update task ID for tracking
    """
    return vector_store_updater.schedule_update(trigger_reason, include_scraped)

def get_vectorstore_update_status(update_id: str) -> Optional[Dict]:
    """Get status of a vector store update"""
    return vector_store_updater.get_update_status(update_id)

def get_vectorstore_queue_status() -> Dict:
    """Get vector store update queue status"""
    return vector_store_updater.get_queue_status()