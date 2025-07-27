"""
Type definitions and data classes for scrapers module
"""

from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum

class ScrapingStatus(Enum):
    """Status of scraping operations"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class LinkData:
    """Data structure for link information"""
    url: str
    category: str  # programs, specialisations, courses
    title: Optional[str] = None
    accessible: bool = True

@dataclass
class ContentData:
    """Data structure for scraped content"""
    url: str
    content: str
    metadata: Dict[str, Any]
    content_length: int
    scraped_at: str

@dataclass
class ScrapingResult:
    """Result of a scraping operation"""
    url: str
    success: bool
    content_data: Optional[ContentData] = None
    error_message: Optional[str] = None
    chunks_count: int = 0

@dataclass
class ProcessingOptions:
    """Options for content processing"""
    use_chunking: bool = False
    save_content: bool = True
    delay_range: tuple = (2.0, 5.0)
    max_retries: int = 3

@dataclass
class ProgressInfo:
    """Progress tracking information"""
    session_id: str
    status: ScrapingStatus
    total_urls: int
    completed: int
    failed: int
    current_url: Optional[str] = None
    start_time: Optional[str] = None
    estimated_completion: Optional[float] = None