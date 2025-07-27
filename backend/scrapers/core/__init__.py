"""
Core module for scrapers - base classes, exceptions, and types
"""

from .base import BaseScraper, BaseDocumentProcessor, BaseFileManager
from .exceptions import (
    ScraperError,
    WebDriverError,
    ContentParsingError,
    FileOperationError,
    NetworkError
)
from .types import (
    ScrapingResult,
    LinkData,
    ContentData,
    ScrapingStatus,
    ProcessingOptions,
    ProgressInfo
)

__all__ = [
    # Base classes
    'BaseScraper',
    'BaseDocumentProcessor', 
    'BaseFileManager',
    
    # Exceptions
    'ScraperError',
    'WebDriverError',
    'ContentParsingError',
    'FileOperationError',
    'NetworkError',
    
    # Types
    'ScrapingResult',
    'LinkData',
    'ContentData', 
    'ScrapingStatus',
    'ProcessingOptions',
    'ProgressInfo'
]