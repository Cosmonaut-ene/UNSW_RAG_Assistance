"""
File operation utilities - file I/O, metadata management, document persistence
"""

import os
import json
import hashlib
from typing import Optional, List, Dict, Any
from datetime import datetime
from langchain.docstore.document import Document

from ..config import config
from ..core.exceptions import FileOperationError
from .content_utils import slugify_url

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
        raise FileOperationError(f"Error saving metadata: {e}")

def save_document_to_file(doc: Document, content_dir: str = None) -> str:
    """Save document content to JSON file"""
    if content_dir is None:
        content_dir = config.CONTENT_DIR
    os.makedirs(content_dir, exist_ok=True)

    # Use source URL to generate filename
    url = doc.metadata.get("source", "")
    slug = slugify_url(url)
    filename = f"{slug}.json"
    filepath = os.path.join(content_dir, filename)

    data = {
        "page_content": doc.page_content,
        "metadata": doc.metadata,
        "saved_at": datetime.utcnow().isoformat()
    }

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"💾 Saved content to: {filepath}")
        return filepath
    except Exception as e:
        raise FileOperationError(f"Error saving document to {filepath}: {e}")

def load_document_from_file(filepath: str) -> Optional[Document]:
    """Load document content from JSON file"""
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return None

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return Document(
            page_content=data["page_content"],
            metadata=data["metadata"]
        )
    except Exception as e:
        raise FileOperationError(f"Error loading document from {filepath}: {e}")

def save_links_to_file(links, filepath: str = None) -> None:
    """
    Save links to file. Accepts either Dict[str, List[str]] or List[str]
    """
    if filepath is None:
        filepath = config.URLS_FILE
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# UNSW Handbook Links\n")
            f.write(f"# Updated on {datetime.now():%Y-%m-%d %H:%M:%S}\n\n")
            
            if isinstance(links, dict):
                # Original format: categorized links
                for category in ["programs", "specialisations", "courses"]:
                    f.write(f"# === {category.upper()} ===\n")
                    for url in links.get(category, []):
                        f.write(f"{url}\n")
                    f.write("\n")
            elif isinstance(links, list):
                # New format: flat list of confirmed links
                f.write("# === CONFIRMED LINKS ===\n")
                for url in links:
                    f.write(f"{url}\n")
                f.write("\n")
        print(f"Successfully saved all links to: {filepath}")
    except Exception as e:
        raise FileOperationError(f"Error saving links to {filepath}: {e}")

def load_links_from_file(filepath: str = None) -> List[str]:
    """Load links from file, using default config path if none provided"""
    if filepath is None:
        filepath = config.URLS_FILE
    
    if not os.path.exists(filepath):
        return []
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
    except Exception as e:
        raise FileOperationError(f"Error loading links from {filepath}: {e}")