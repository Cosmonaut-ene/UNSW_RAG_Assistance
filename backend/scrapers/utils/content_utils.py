"""
Content processing utilities - text cleaning, document building, data extraction
"""

import re
from typing import Optional, List, Dict, Any
from bs4 import BeautifulSoup
from langchain.docstore.document import Document

IGNORED_KEYS = {"key", "cl_id", "state", "linking_id", "order", "active", "hbeorder"}

def slugify_url(url: str) -> str:
    """Convert URL to safe filename"""
    return re.sub(r'\W+', '_', url.strip()).strip('_')

def clean_text(text: str) -> str:
    """Clean and normalize text content, removing redundant newlines and meaningless values"""
    if not text:
        return ""
    
    # Convert to string and check for meaningless values first
    text_str = str(text).strip()
    if not text_str or text_str.lower() in ["none", "null", "undefined"]:
        return ""
    
    # Remove HTML tags and decode entities
    text = BeautifulSoup(text_str, "html.parser").get_text(separator=" ")
    
    # Remove redundant newlines and normalize whitespace
    text = re.sub(r'\n+', ' ', text)  # Replace multiple newlines with single space
    text = re.sub(r'\s+', ' ', text).strip()  # Normalize all whitespace
    
    # Remove common HTML artifacts
    text = re.sub(r'&[a-zA-Z0-9#]+;', '', text)
    
    # Final check for meaningless content after cleaning
    if not text or text.lower() in ["none", "null", "undefined"]:
        return ""
    
    return text

def is_meaningful(val: Any) -> bool:
    """Check if value contains meaningful content"""
    if not val:
        return False
    if isinstance(val, str):
        return val.strip().lower() not in ["", "null", "none", "n/a", "undefined"]
    return True

def should_ignore_key(k: str) -> bool:
    """Check if key should be ignored during processing"""
    return any(x in k.lower() for x in IGNORED_KEYS)

def extract_key_value(obj: Dict[str, Any], key: str, default: str = "") -> str:
    """Extract value from nested dictionary structures, filtering out meaningless values"""
    if not obj or not isinstance(obj, dict):
        return default
    
    value = obj.get(key, default)
    
    # Handle different value formats from UNSW API
    if isinstance(value, dict):
        if "value" in value and is_meaningful(value["value"]):
            return str(value["value"])
        elif "label" in value and is_meaningful(value["label"]):
            return str(value["label"])
    elif isinstance(value, list) and value:
        # For arrays, take the first meaningful item's value/label
        for item in value:
            if isinstance(item, dict):
                if "value" in item and is_meaningful(item["value"]):
                    return str(item["value"])
                elif "label" in item and is_meaningful(item["label"]):
                    return str(item["label"])
    elif is_meaningful(value):
        return str(value)
    
    return default

def extract_list_values(obj: List[Dict[str, Any]], key: str = "value") -> List[str]:
    """Extract meaningful values from list of objects, filtering out empty/useless values"""
    if not obj or not isinstance(obj, list):
        return []
    
    values = []
    for item in obj:
        if isinstance(item, dict):
            if key in item and is_meaningful(item[key]):
                values.append(str(item[key]))
            elif "label" in item and is_meaningful(item["label"]):
                values.append(str(item["label"]))
    
    return values

def beautify_field_name(s: str) -> str:
    """Convert field name to human-readable format"""
    s = s.replace("_", " ")
    s = re.sub(r"\b0\b", "", s)
    return s.strip().title()

def is_simple_object(obj: Any) -> tuple:
    """
    Check if object is a simple pattern that can be displayed more concisely.
    Returns (is_simple: bool, format_type: str, display_text: str)
    """
    if not isinstance(obj, dict):
        return False, "", ""
    
    # Filter out ignored keys and get meaningful fields
    meaningful_fields = {}
    for key, value in obj.items():
        if not should_ignore_key(key) and is_meaningful(value):
            meaningful_fields[key] = value
    
    # Check for label + value pattern
    if len(meaningful_fields) == 2 and 'label' in meaningful_fields and 'value' in meaningful_fields:
        label = clean_text(str(meaningful_fields['label']))
        value = clean_text(str(meaningful_fields['value']))
        if label and value:
            return True, "label_value", f"{label} ({value})"
    
    # Check for single value pattern
    if len(meaningful_fields) == 1 and 'value' in meaningful_fields:
        value = clean_text(str(meaningful_fields['value']))
        if value:
            return True, "value_only", value
    
    # Check for single label pattern
    if len(meaningful_fields) == 1 and 'label' in meaningful_fields:
        label = clean_text(str(meaningful_fields['label']))
        if label:
            return True, "label_only", label
    
    # Check for single description pattern
    if len(meaningful_fields) == 1 and 'description' in meaningful_fields:
        desc = clean_text(str(meaningful_fields['description']))
        if desc:
            return True, "description_only", desc
    
    return False, "", ""

def extract_all_meaningful_fields(obj: Any, prefix: str = "") -> Dict[str, str]:
    """
    Recursively extract all meaningful fields from a nested object structure.
    This ensures no valuable data is lost during content cleaning.
    """
    result = {}
    
    if isinstance(obj, dict):
        for key, value in obj.items():
            field_name = f"{prefix}_{key}" if prefix else key
            
            # Skip obviously technical/meaningless fields
            skip_fields = {
                'id', 'uuid', 'href', 'links', 'uri', 'url', 'path', 'slug', 
                'created', 'updated', 'modified', 'timestamp', 'last_modified',
                'meta', 'metadata', 'seo', 'canonical', 'redirect'
            }
            if should_ignore_key(key) or key.lower() in skip_fields or key.startswith('_'):
                continue
            
            if isinstance(value, (dict, list)):
                # Recursively process nested structures
                nested_fields = extract_all_meaningful_fields(value, field_name)
                result.update(nested_fields)
            else:
                # Extract scalar values
                if is_meaningful(value):
                    result[field_name] = str(value)
                    
    elif isinstance(obj, list):
        # Handle lists by extracting meaningful values
        meaningful_values = []
        for i, item in enumerate(obj):
            if isinstance(item, dict):
                # For objects in list, try to extract key meaningful fields
                if "value" in item and is_meaningful(item["value"]):
                    meaningful_values.append(str(item["value"]))
                elif "label" in item and is_meaningful(item["label"]):
                    meaningful_values.append(str(item["label"]))
                elif "description" in item and is_meaningful(item["description"]):
                    meaningful_values.append(clean_text(item["description"]))
                else:
                    # Extract all meaningful fields from object
                    nested_fields = extract_all_meaningful_fields(item, f"{prefix}_{i}" if prefix else str(i))
                    result.update(nested_fields)
            elif is_meaningful(item):
                meaningful_values.append(str(item))
        
        if meaningful_values:
            result[prefix or "values"] = ", ".join(meaningful_values)
    
    return result

def build_semantic_document(
    data: Any,
    path: List[str] = [],
    source_url: str = ""
) -> Optional[Document]:
    """
    Build semantic document from nested structure, converting to meaningful Markdown hierarchy
    """
    if not is_meaningful(data):
        return None
    
    content_parts = []
    
    def build_hierarchical_content(obj: Any, current_path: List[str], level: int = 1) -> List[str]:
        parts = []
        
        if isinstance(obj, dict):
            # Add heading for current level (if has path)
            if current_path and level <= 6:
                title = beautify_field_name(current_path[-1])
                parts.append(f"{'#' * level} {title}")
                parts.append("")  # Empty line
            
            # Process each key-value pair in dictionary
            for key, value in obj.items():
                if should_ignore_key(key):
                    continue
                
                new_path = current_path + [key]
                
                if isinstance(value, dict):
                    # Skip empty dictionaries
                    if not value:
                        continue
                    
                    # Check if dictionary has any meaningful content after filtering
                    has_meaningful_content = False
                    for dict_key, dict_value in value.items():
                        if not should_ignore_key(dict_key) and is_meaningful(dict_value):
                            has_meaningful_content = True
                            break
                    
                    # Skip dictionaries with no meaningful content
                    if not has_meaningful_content:
                        continue
                        
                    # Check if this dictionary is a simple object that can be displayed inline
                    is_simple, format_type, display_text = is_simple_object(value)
                    if is_simple:
                        # Display simple object inline
                        field_name = beautify_field_name(key)
                        if level + 1 <= 6:
                            parts.append(f"{'#' * (level + 1)} {field_name}")
                            parts.append(display_text)
                        else:
                            parts.append(f"**{field_name}:** {display_text}")
                        parts.append("")  # Empty line
                    else:
                        # Nested dictionary: recursive processing
                        nested_parts = build_hierarchical_content(value, new_path, level + 1)
                        # Only add parts if the recursive call generated content
                        if nested_parts:
                            parts.extend(nested_parts)
                elif isinstance(value, list):
                    # Skip empty lists entirely
                    if not value:
                        continue
                        
                    # List: check if all items are simple objects that can be displayed concisely
                    simple_items = []
                    complex_items = []
                    
                    for idx, item in enumerate(value):
                        if isinstance(item, dict):
                            is_simple, format_type, display_text = is_simple_object(item)
                            if is_simple:
                                simple_items.append(display_text)
                            else:
                                complex_items.append((idx, item))
                        elif is_meaningful(item):
                            simple_items.append(clean_text(str(item)))
                    
                    # Only create content if we have meaningful items
                    if simple_items or complex_items:
                        # Special handling: if list has only one complex item, treat it as direct content
                        if len(complex_items) == 1 and not simple_items:
                            # Single complex item: expand directly without extra heading
                            idx, item = complex_items[0]
                            item_parts = build_hierarchical_content(item, new_path, level + 1)
                            parts.extend(item_parts)
                        else:
                            # Multiple items or mixed content: create subheading for the list
                            if level + 1 <= 6:
                                list_title = beautify_field_name(key)
                                parts.append(f"{'#' * (level + 1)} {list_title}")
                                parts.append("")
                            
                            # Display simple items as a clean list
                            if simple_items:
                                for item_text in simple_items:
                                    parts.append(f"- {item_text}")
                                parts.append("")  # Empty line after simple items
                            
                            # Display complex items with full hierarchy
                            if complex_items:
                                for idx, item in complex_items:
                                    item_parts = build_hierarchical_content(item, new_path + [str(idx)], level + 1)
                                    parts.extend(item_parts)
                else:
                    # Simple value: display as field
                    if is_meaningful(value):
                        field_name = beautify_field_name(key)
                        clean_value = clean_text(str(value))
                        if level + 1 <= 6:
                            parts.append(f"{'#' * (level + 1)} {field_name}")
                            parts.append(clean_value)
                        else:
                            parts.append(f"**{field_name}:** {clean_value}")
                        parts.append("")  # Empty line
        
        elif isinstance(obj, list):
            # Process top-level list
            for idx, item in enumerate(obj):
                if isinstance(item, dict):
                    item_parts = build_hierarchical_content(item, current_path + [str(idx)], level)
                    parts.extend(item_parts)
                elif is_meaningful(item):
                    parts.append(f"- {clean_text(str(item))}")
            if obj:  # If list not empty, add empty line
                parts.append("")
        
        else:
            # Simple value
            if is_meaningful(obj):
                clean_value = clean_text(str(obj))
                parts.append(clean_value)
                parts.append("")
        
        return parts
    
    # Generate content
    content_parts = build_hierarchical_content(data, path, 1)
    
    if not content_parts:
        return None
    
    # Combine final content
    full_content = "\n".join(content_parts).strip()
    
    # Build metadata
    field_path = " -> ".join(path) if path else "root"
    
    return Document(
        page_content=full_content,
        metadata={
            # "field": field_path,
            "source": source_url,
            "content_type": "semantic_hierarchical"
        }
    )

def flatten_structure(
    data: Any,
    prefix: str = "",
    chunks: List[Document] = [],
    source_url: str = "",
    level: int = 1
) -> None:
    """
    Semantically flatten nested structure, generating complete semantic document for each meaningful substructure
    """
    if isinstance(data, dict):
        # Create semantic document for entire dictionary structure
        path = prefix.split(" -> ") if prefix else []
        doc = build_semantic_document(data, path, source_url)
        if doc:
            chunks.append(doc)
        
        # Also create independent documents for each subfield (if complex enough)
        for key, value in data.items():
            if should_ignore_key(key):
                continue
            
            new_prefix = f"{prefix} -> {key}" if prefix else key
            
            # Only create independent documents for complex structures (dict/list)
            if isinstance(value, (dict, list)) and value:
                flatten_structure(value, new_prefix, chunks, source_url, level + 1)
    
    elif isinstance(data, list) and data:
        # Create semantic document for entire list
        path = prefix.split(" -> ") if prefix else []
        doc = build_semantic_document(data, path, source_url)
        if doc:
            chunks.append(doc)
        
        # Create independent documents for complex elements in list
        for idx, item in enumerate(data):
            if isinstance(item, (dict, list)) and item:
                new_prefix = f"{prefix} -> {idx}" if prefix else str(idx)
                flatten_structure(item, new_prefix, chunks, source_url, level)
    
    else:
        # Simple value: create simple document
        if is_meaningful(data):
            path = prefix.split(" -> ") if prefix else []
            doc = build_semantic_document(data, path, source_url)
            if doc:
                chunks.append(doc)

def chunk_structured_content(content: Dict[str, Any], source_url: str) -> List[Document]:
    """Convert structured content into individual document chunks"""
    chunks = []
    flatten_structure(content, "", chunks, source_url)
    return chunks