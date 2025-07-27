"""
Utility modules for scrapers - common functionality
"""

from .web_utils import (
    get_chrome_driver,
    make_request_with_retry,
    get_random_headers,
    add_random_delay,
    normalize_url,
    is_valid_link
)

from .content_utils import (
    clean_text,
    is_meaningful,
    should_ignore_key,
    extract_key_value,
    extract_list_values,
    beautify_field_name,
    extract_all_meaningful_fields,
    build_semantic_document,
    chunk_structured_content,
    slugify_url
)

from .file_utils import (
    get_file_hash,
    save_metadata,
    load_metadata,
    save_document_to_file,
    load_document_from_file,
    save_links_to_file,
    load_links_from_file
)

__all__ = [
    # Web utilities
    'get_chrome_driver',
    'make_request_with_retry', 
    'get_random_headers',
    'add_random_delay',
    'normalize_url',
    'is_valid_link',
    
    # Content utilities
    'clean_text',
    'is_meaningful',
    'should_ignore_key',
    'extract_key_value',
    'extract_list_values',
    'beautify_field_name',
    'extract_all_meaningful_fields',
    'build_semantic_document',
    'chunk_structured_content',
    'slugify_url',
    
    # File utilities
    'get_file_hash',
    'save_metadata',
    'load_metadata',
    'save_document_to_file',
    'load_document_from_file',
    'save_links_to_file',
    'load_links_from_file'
]