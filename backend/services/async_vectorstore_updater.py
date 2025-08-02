# services/async_vectorstore_updater.py
"""
Asynchronous vector store updater for handling ChromaDB operations in background
"""

import threading
import time
import queue
from typing import Optional, Dict, Any
from datetime import datetime
import traceback

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
            
            # Execute the vector store update
            from rag import update_knowledge_base
            result = update_knowledge_base(include_scraped=update_task['include_scraped'])
            
            update_task['status'] = 'completed'
            update_task['completed_at'] = datetime.now()
            update_task['result'] = result
            
            print(f"[AsyncVectorStore] Update completed: {update_task['trigger_reason']}")
            
        except Exception as e:
            update_task['status'] = 'failed'
            update_task['completed_at'] = datetime.now()
            update_task['error'] = str(e)
            
            print(f"[AsyncVectorStore] Update failed: {update_task['trigger_reason']} - {e}")
            
            # For readonly database errors, we might want to retry once
            if "readonly database" in str(e).lower():
                print("[AsyncVectorStore] Readonly database detected, scheduling retry...")
                retry_id = self.schedule_update(f"retry_{update_task['trigger_reason']}", update_task['include_scraped'])
                update_task['retry_scheduled'] = retry_id
        
        finally:
            # Move to history
            self._add_to_history(update_task)
            self.current_update = None
    
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