import requests
import json
import os
import re
import time
import random
from datetime import datetime
from typing import Optional, List, Dict, Any
from bs4 import BeautifulSoup
from langchain.docstore.document import Document
from .config import config

def slugify_url(url: str) -> str:
    """transfer url to filename"""
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


IGNORED_KEYS = {"key", "cl_id", "state", "linking_id", "order", "active", "hbeorder"}

def is_meaningful(val: Any) -> bool:
    if not val:
        return False
    if isinstance(val, str):
        return val.strip().lower() not in ["", "null", "none", "n/a", "undefined"]
    return True

def should_ignore_key(k: str) -> bool:
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
    s = s.replace("_", " ")
    s = re.sub(r"\b0\b", "", s)
    return s.strip().title()


def build_semantic_document(
    data: Any,
    path: List[str] = [],
    source_url: str = ""
) -> Optional[Document]:
    """
    构建语义化的文档块，将嵌套结构转换为有意义的Markdown层次结构
    """
    if not is_meaningful(data):
        return None
    
    # 构建完整的markdown内容
    content_parts = []
    
    # 构建层次化标题
    def build_hierarchical_content(obj: Any, current_path: List[str], level: int = 1) -> List[str]:
        parts = []
        
        if isinstance(obj, dict):
            # 为当前层级添加标题（如果有路径）
            if current_path and level <= 6:
                title = beautify_field_name(current_path[-1])
                parts.append(f"{'#' * level} {title}")
                parts.append("")  # 空行
            
            # 处理字典中的每个键值对
            for key, value in obj.items():
                if should_ignore_key(key):
                    continue
                
                new_path = current_path + [key]
                
                if isinstance(value, dict):
                    # 嵌套字典：递归处理
                    nested_parts = build_hierarchical_content(value, new_path, level + 1)
                    parts.extend(nested_parts)
                elif isinstance(value, list):
                    # 列表：创建子标题并处理每个元素
                    if level + 1 <= 6:
                        list_title = beautify_field_name(key)
                        parts.append(f"{'#' * (level + 1)} {list_title}")
                        parts.append("")
                    
                    for idx, item in enumerate(value):
                        if isinstance(item, dict):
                            # 列表中的字典项
                            item_parts = build_hierarchical_content(item, new_path + [str(idx)], level + 2)
                            parts.extend(item_parts)
                        elif is_meaningful(item):
                            # 列表中的простой值
                            parts.append(f"- {clean_text(str(item))}")
                    parts.append("")  # 空行
                else:
                    # 简单值：作为字段显示
                    if is_meaningful(value):
                        field_name = beautify_field_name(key)
                        clean_value = clean_text(str(value))
                        if level + 1 <= 6:
                            parts.append(f"{'#' * (level + 1)} {field_name}")
                            parts.append(clean_value)
                        else:
                            parts.append(f"**{field_name}:** {clean_value}")
                        parts.append("")  # 空行
        
        elif isinstance(obj, list):
            # 处理顶层列表
            for idx, item in enumerate(obj):
                if isinstance(item, dict):
                    item_parts = build_hierarchical_content(item, current_path + [str(idx)], level)
                    parts.extend(item_parts)
                elif is_meaningful(item):
                    parts.append(f"- {clean_text(str(item))}")
            if obj:  # 如果列表不为空，添加空行
                parts.append("")
        
        else:
            # 简单值
            if is_meaningful(obj):
                clean_value = clean_text(str(obj))
                parts.append(clean_value)
                parts.append("")
        
        return parts
    
    # 生成内容
    content_parts = build_hierarchical_content(data, path, 1)
    
    if not content_parts:
        return None
    
    # 组合最终内容
    full_content = "\n".join(content_parts).strip()
    
    # 构建元数据
    field_path = " -> ".join(path) if path else "root"
    
    return Document(
        page_content=full_content,
        metadata={
            "field": field_path,
            "source": source_url,
            "depth": len(path),
            "field_path": path,
            "content_type": "semantic_hierarchical"
        }
    )


def flatten_structure(
    data: Any,
    prefix: str = "",
    chunks: List[Document] = [],
    source_url: str = "",
    depth: int = 1,
    level: int = 1
) -> None:
    """
    语义化递归展开嵌套结构，每个有意义的子结构生成一个完整的语义文档
    """
    if isinstance(data, dict):
        # 为整个字典结构创建一个语义文档
        path = prefix.split(" -> ") if prefix else []
        doc = build_semantic_document(data, path, source_url)
        if doc:
            chunks.append(doc)
        
        # 同时为每个子字段创建独立文档（如果它们足够复杂）
        for key, value in data.items():
            if should_ignore_key(key):
                continue
            
            new_prefix = f"{prefix} -> {key}" if prefix else key
            
            # 只为复杂结构（dict/list）创建独立文档
            if isinstance(value, (dict, list)) and value:
                flatten_structure(value, new_prefix, chunks, source_url, depth + 1, level + 1)
    
    elif isinstance(data, list) and data:
        # 为整个列表创建一个语义文档
        path = prefix.split(" -> ") if prefix else []
        doc = build_semantic_document(data, path, source_url)
        if doc:
            chunks.append(doc)
        
        # 为列表中的复杂元素创建独立文档
        for idx, item in enumerate(data):
            if isinstance(item, (dict, list)) and item:
                new_prefix = f"{prefix} -> {idx}" if prefix else str(idx)
                flatten_structure(item, new_prefix, chunks, source_url, depth + 1, level)
    
    else:
        # 简单值：创建简单文档
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


def clean_academic_content(content: Dict[str, Any]) -> Dict[str, Any]:
    """
    Dynamically extract ALL meaningful fields from UNSW API content.
    This approach preserves maximum information instead of filtering to predefined fields.
    """
    # Extract all meaningful fields dynamically
    all_fields = extract_all_meaningful_fields(content)
    
    # Clean all extracted fields and beautify field names
    cleaned = {}
    for field_name, field_value in all_fields.items():
        # Beautify field name for better readability
        clean_field_name = beautify_field_name(field_name)
        
        if isinstance(field_value, str):
            cleaned_value = clean_text(field_value)
            if cleaned_value:  # Only keep non-empty values
                cleaned[clean_field_name] = cleaned_value
        else:
            # For non-string values, try to extract meaningful content
            extracted_value = extract_key_value(field_value if isinstance(field_value, dict) else {"value": field_value}, "value")
            if extracted_value:
                cleaned[clean_field_name] = extracted_value
    
    # Handle special complex fields that need custom processing
    
    # Learning outcomes - format as strict markdown numbered list
    learning_outcomes = content.get("learning_outcomes", [])
    if learning_outcomes:
        outcomes_text = []
        for i, outcome in enumerate(learning_outcomes):
            if isinstance(outcome, dict):
                # Extract all meaningful fields from each outcome
                outcome_fields = extract_all_meaningful_fields(outcome, f"learning_outcome_{i}")
                cleaned.update(outcome_fields)
                
                # Create numbered list format for each outcome
                if "description" in outcome:
                    clean_outcome = clean_text(outcome["description"])
                    if clean_outcome:
                        outcomes_text.append(f"{i+1}. {clean_outcome}")
                elif "value" in outcome:
                    clean_outcome = clean_text(outcome["value"])
                    if clean_outcome:
                        outcomes_text.append(f"{i+1}. {clean_outcome}")
                elif isinstance(outcome, str):
                    clean_outcome = clean_text(outcome)
                    if clean_outcome:
                        outcomes_text.append(f"{i+1}. {clean_outcome}")
        
        if outcomes_text:
            # Join with newlines to create proper markdown numbered list
            cleaned["learning_outcomes_formatted"] = "\n".join(outcomes_text)
    
    # Course structure - extract detailed structure information
    if "course_structure" in content:
        structure_data = content["course_structure"]
        structure_fields = extract_all_meaningful_fields(structure_data, "course_structure")
        cleaned.update(structure_fields)
    
    # Program structure - extract detailed program information  
    if "program_structure" in content:
        program_data = content["program_structure"]
        program_fields = extract_all_meaningful_fields(program_data, "program_structure")
        cleaned.update(program_fields)
        
    # Requirements - ensure all requirement types are captured
    requirement_fields = [
        "requirements", "entry_requirements", "admission_requirements",
        "prerequisites", "corequisites", "exclusions", "assumed_knowledge",
        "progression_requirements", "graduation_requirements"
    ]
    
    for req_field in requirement_fields:
        if req_field in content:
            req_data = content[req_field]
            if isinstance(req_data, (dict, list)):
                req_fields = extract_all_meaningful_fields(req_data, req_field)
                cleaned.update(req_fields)
            elif is_meaningful(req_data):
                cleaned[req_field] = clean_text(str(req_data))
    
    return cleaned


def format_nested_section(title: str, section_data: Any) -> Optional[str]:
    """
    通用嵌套字段格式化器，支持列表对象、dict、段落等自动判断。
    """
    if not section_data:
        return None

    parts = [f"## {title}"]

    if isinstance(section_data, list):
        for item in section_data:
            if isinstance(item, dict):
                block = []
                for k, v in item.items():
                    if is_meaningful(v):
                        clean_k = beautify_field_name(str(k))
                        clean_v = clean_text(str(v))
                        block.append(f"- **{clean_k}:** {clean_v}")
                if block:
                    parts.append("\n".join(block))
            elif is_meaningful(item):
                parts.append(f"- {clean_text(str(item))}")
    elif isinstance(section_data, dict):
        for k, v in section_data.items():
            if is_meaningful(v):
                clean_k = beautify_field_name(str(k))
                clean_v = clean_text(str(v))
                parts.append(f"- **{clean_k}:** {clean_v}")
    elif isinstance(section_data, str):
        clean_v = clean_text(section_data)
        if clean_v:
            parts.append(clean_v)

    return "\n".join(parts) if len(parts) > 1 else None


def get_random_headers() -> Dict[str, str]:
    """Generate randomized headers to avoid detection"""
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0"
    ]
    
    accept_languages = [
        "en-US,en;q=0.9",
        "en-AU,en;q=0.9,en-US;q=0.8",
        "en-GB,en;q=0.9,en-US;q=0.8",
        "en-US,en;q=0.5"
    ]
    
    return {
        "User-Agent": random.choice(user_agents),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": random.choice(accept_languages),
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Charset": "UTF-8",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0"
    }


def add_random_delay(min_delay: float = 1.0, max_delay: float = 3.0):
    """Add random delay between requests to avoid rate limiting"""
    delay = random.uniform(min_delay, max_delay)
    print(f"⏱️ Waiting {delay:.1f}s before next request...")
    time.sleep(delay)


def make_request_with_retry(url: str, max_retries: int = 3, backoff_factor: float = 2.0) -> Optional[requests.Response]:
    """Make HTTP request with retries and exponential backoff"""
    for attempt in range(max_retries):
        try:
            headers = get_random_headers()
            
            # Add delay before request (except first attempt)
            if attempt > 0:
                delay = backoff_factor ** attempt + random.uniform(0.5, 1.5)
                print(f"🔄 Retry {attempt + 1}/{max_retries} after {delay:.1f}s delay...")
                time.sleep(delay)
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return response
            elif response.status_code == 403:
                print(f"⛔ HTTP 403 Forbidden - attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    continue
            elif response.status_code == 429:
                print(f"⏳ Rate limited (429) - attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    time.sleep(random.uniform(5, 10))
                    continue
            else:
                response.raise_for_status()
                
        except requests.exceptions.RequestException as e:
            print(f"🌐 Network error on attempt {attempt + 1}/{max_retries}: {e}")
            if attempt < max_retries - 1:
                continue
            
    print(f"❌ Failed to fetch {url} after {max_retries} attempts")
    return None


def parse_description(html_text: str) -> str:
    """将 HTML 格式描述转为纯文本 (legacy function for compatibility)"""
    return clean_text(html_text)


def scrape_single_page_chunked(url: str) -> List[Document]:
    """
    使用分块化方法提取页面内容，每个字段生成一个Document
    """
    print(f"🔍 Scraping structured page (chunked): {url}")

    # Use robust request function with retries
    response = make_request_with_retry(url)
    if not response:
        return []

    try:
        soup = BeautifulSoup(response.text, "html.parser")
        script_tag = soup.find("script", id="__NEXT_DATA__")
        if not script_tag:
            raise ValueError("❌ 找不到 __NEXT_DATA__ script 标签")
    except Exception as e:
        print(f"❌ HTML 解析失败: {e}")
        return []

    try:
        next_data = json.loads(script_tag.string)
        page_props = next_data.get("props", {}).get("pageProps", {})

        # 合并多个可能包含内容的字段
        merged_content = {}

        # 1. pageContent
        pc = page_props.get("pageContent")
        if isinstance(pc, dict):
            merged_content.update(pc)
        elif isinstance(pc, str):
            print("⚠️ pageContent 是字符串，可能是错误提示：", pc[:100])

        # 2. program (某些页面结构)
        pg = page_props.get("program")
        if isinstance(pg, dict):
            merged_content.update(pg)

        # 3. programData（部分页面）
        pd = page_props.get("programData")
        if isinstance(pd, dict):
            merged_content.update(pd)

        # 4. metadata（补充信息）
        meta = page_props.get("metadata")
        if isinstance(meta, dict):
            merged_content.update(meta)

        if not merged_content:
            print("⚠️ 没有发现结构化内容")
            return []

        # 使用分块化方法处理内容
        chunks = chunk_structured_content(merged_content, url)
        
        print(f"✅ Generated {len(chunks)} content chunks")
        return chunks

    except Exception as e:
        print(f"❌ 解析 structured JSON 失败: {e}")
        return []


def scrape_single_page(url: str, use_chunking: bool = False):
    """
    使用 __NEXT_DATA__ 脚本提取 UNSW handbook 页面结构化内容。
    适用于 program/specialisation/course 页面。
    
    Args:
        url: 页面URL
        use_chunking: 是否使用分块化处理（每个字段一个Document）
        
    Returns:
        List[Document] if use_chunking=True, Optional[Document] if use_chunking=False
    """
    if use_chunking:
        return scrape_single_page_chunked(url)
    
    print(f"🔍 Scraping structured page: {url}")

    # Use robust request function with retries
    response = make_request_with_retry(url)
    if not response:
        return None

    try:
        soup = BeautifulSoup(response.text, "html.parser")
        script_tag = soup.find("script", id="__NEXT_DATA__")
        if not script_tag:
            raise ValueError("❌ 找不到 __NEXT_DATA__ script 标签")
    except Exception as e:
        print(f"❌ HTML 解析失败: {e}")
        return None

    try:
        next_data = json.loads(script_tag.string)
        page_props = next_data.get("props", {}).get("pageProps", {})

        # 🧠 合并多个可能包含内容的字段
        merged_content = {}

        # 1. pageContent
        pc = page_props.get("pageContent")
        if isinstance(pc, dict):
            merged_content.update(pc)
        elif isinstance(pc, str):
            print("⚠️ pageContent 是字符串，可能是错误提示：", pc[:100])

        # 2. program (某些页面结构)
        pg = page_props.get("program")
        if isinstance(pg, dict):
            merged_content.update(pg)

        # 3. programData（部分页面）
        pd = page_props.get("programData")
        if isinstance(pd, dict):
            merged_content.update(pd)

        # 4. metadata（补充信息）
        meta = page_props.get("metadata")
        if isinstance(meta, dict):
            merged_content.update(meta)

        # 最终 merged_content 是综合内容
        if not merged_content:
            print("⚠️ 没有发现结构化内容")
            return None

        # 使用语义化文档构建器生成内容
        doc = build_semantic_document(merged_content, [], url)
        if not doc:
            print("⚠️ 无法生成语义化文档")
            return None
        
        full_text = doc.page_content
        
        # Create essential metadata only
        metadata = {
            "source": url,
            "scraped_at": datetime.utcnow().isoformat(),
            "content_length": len(full_text),
            "title": merged_content.get("title", ""),
            "code": merged_content.get("code", ""),
            "content_type": merged_content.get("contentTypeLabel", "")
        }

        return Document(page_content=full_text, metadata=metadata)

    except Exception as e:
        print(f"❌ 解析 structured JSON 失败: {e}")
        return None


def save_page_content(doc: Document, content_dir: str = None) -> str:
    if content_dir is None:
        content_dir = config.CONTENT_DIR
    os.makedirs(content_dir, exist_ok=True)

    # 使用 code 或 fallback 文件名
    url = doc.metadata.get("source", "")
    slug = slugify_url(url)
    filename = f"{slug}.json"
    filepath = os.path.join(content_dir, filename)

    data = {
        "page_content": doc.page_content,
        "metadata": doc.metadata,
        "saved_at": datetime.utcnow().isoformat()
    }

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"💾 Saved content to: {filepath}")
    return filepath


def load_page_content(filepath: str) -> Optional[Document]:
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
        print(f"❌ Error loading {filepath}: {e}")
        return None


def scrape_urls_batch(urls: List[str], save_content: bool = True, delay_range: tuple = (2.0, 5.0), use_chunking: bool = False) -> List[Document]:
    """
    Batch scrape URLs with anti-blocking measures
    
    Args:
        urls: List of URLs to scrape
        save_content: Whether to save content to files
        delay_range: (min_delay, max_delay) in seconds between requests
        use_chunking: Whether to use chunking (each field becomes a Document)
    """
    docs = []
    failed = []

    print(f"🚀 Scraping {len(urls)} UNSW handbook pages with anti-blocking measures")
    print(f"⏱️ Using random delays between {delay_range[0]}-{delay_range[1]}s")

    for i, url in enumerate(urls):
        print(f"\n[{i+1}/{len(urls)}] {url}")
        
        # Add delay between requests (except for first request)
        if i > 0:
            add_random_delay(delay_range[0], delay_range[1])
        
        result = scrape_single_page(url, use_chunking=use_chunking)
        if result:
            if use_chunking:
                # result is List[Document]
                docs.extend(result)
                if save_content:
                    for doc in result:
                        save_page_content(doc)
                print(f"✅ Successfully scraped {len(result)} chunks from: {url}")
            else:
                # result is Optional[Document]
                docs.append(result)
                if save_content:
                    save_page_content(result)
                print(f"✅ Successfully scraped: {result.metadata.get('title', 'Unknown')}")
        else:
            failed.append(url)
            print(f"❌ Failed to scrape: {url}")

    print(f"\n🎯 Batch Results: {len(docs)} success, ❌ {len(failed)} failed")
    
    if failed:
        print("\n❌ Failed URLs:")
        for url in failed:
            print(f"   - {url}")
    
    return docs


# Global storage for scraping progress (in production, use Redis or database)
_scraping_sessions = {}

def start_scraping_with_progress(urls: List[str], auto_update_vector_store: bool = True) -> str:
    """
    Start scraping with progress tracking and return a session ID
    """
    import uuid
    from threading import Thread
    
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
            
            docs = []
            failed = []
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
                doc = scrape_single_page(url)
                if doc:
                    docs.append(doc)
                    save_page_content(doc)
                    session["completed_urls"].append({
                        "url": url,
                        "title": doc.metadata.get("title", "Unknown"),
                        "content_length": len(doc.page_content)
                    })
                    total_content_length += len(doc.page_content)
                else:
                    failed.append(url)
                    session["failed_urls"].append(url)
                
                # Update counters
                session["completed"] = len(docs)
                session["failed"] = len(failed)
                session["statistics"]["success_rate"] = (len(docs) / (i + 1)) * 100
                
                if len(docs) > 0:
                    session["statistics"]["average_content_length"] = total_content_length // len(docs)
            
            # Final status
            if not session.get("cancelled"):
                session["status"] = "completed"
                session["current_url"] = None
                
                # Auto-update vector store if requested
                if auto_update_vector_store and docs:
                    session["status"] = "updating_vector_store"
                    try:
                        from rag.gemini3 import update_vector_store_with_scraped
                        update_vector_store_with_scraped()
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
    """
    Get current progress for a scraping session
    """
    return _scraping_sessions.get(scraping_id)


def cancel_scraping_session(scraping_id: str) -> bool:
    """
    Cancel an ongoing scraping session
    """
    if scraping_id in _scraping_sessions:
        _scraping_sessions[scraping_id]["cancelled"] = True
        _scraping_sessions[scraping_id]["status"] = "cancelling"
        return True
    return False
