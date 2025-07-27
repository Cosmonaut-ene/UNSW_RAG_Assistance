"""
Custom exceptions for scrapers module
"""

class ScraperError(Exception):
    """Base exception for all scraper-related errors"""
    pass

class WebDriverError(ScraperError):
    """Exception raised when WebDriver operations fail"""
    pass

class ContentParsingError(ScraperError):
    """Exception raised when content parsing fails"""
    pass

class FileOperationError(ScraperError):
    """Exception raised when file operations fail"""
    pass

class NetworkError(ScraperError):
    """Exception raised when network requests fail"""
    pass