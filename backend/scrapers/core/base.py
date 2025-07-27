"""
Base classes and interfaces for scrapers module
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Set
from langchain.docstore.document import Document

from .types import LinkData, ContentData, ScrapingResult, ProcessingOptions, ProgressInfo

class BaseScraper(ABC):
    """Abstract base class for all scrapers"""
    
    @abstractmethod
    def scrape_links(self, root_url: str) -> Dict[str, List[str]]:
        """Discover links from a root URL"""
        pass
    
    @abstractmethod
    def scrape_content(self, url: str, options: ProcessingOptions) -> Optional[ScrapingResult]:
        """Scrape content from a single URL"""
        pass
    
    @abstractmethod
    def batch_scrape(self, urls: List[str], options: ProcessingOptions) -> List[ScrapingResult]:
        """Scrape content from multiple URLs"""
        pass

class BaseDocumentProcessor(ABC):
    """Abstract base class for document processing"""
    
    @abstractmethod
    def process_structured_data(self, data: Dict[str, Any], url: str) -> Optional[Document]:
        """Process structured data into a document"""
        pass
    
    @abstractmethod
    def process_into_chunks(self, data: Dict[str, Any], url: str) -> List[Document]:
        """Process structured data into multiple document chunks"""
        pass
    
    @abstractmethod
    def clean_content(self, content: Any) -> str:
        """Clean and normalize content"""
        pass

class BaseFileManager(ABC):
    """Abstract base class for file operations"""
    
    @abstractmethod
    def save_links(self, links: Any, filepath: str) -> None:
        """Save links to file"""
        pass
    
    @abstractmethod
    def load_links(self, filepath: str) -> List[str]:
        """Load links from file"""
        pass
    
    @abstractmethod
    def save_content(self, document: Document, content_dir: str) -> str:
        """Save document content to file"""
        pass
    
    @abstractmethod
    def load_content(self, filepath: str) -> Optional[Document]:
        """Load document content from file"""
        pass
    
    @abstractmethod
    def get_file_hash(self, filepath: str) -> Optional[str]:
        """Get hash of file for change detection"""
        pass