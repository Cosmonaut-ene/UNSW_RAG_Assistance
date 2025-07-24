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


def is_meaningful_value(value: Any) -> bool:
    """Check if a value is meaningful (not empty, None, or useless cl_id)"""
    if value is None:
        return False
    
    str_val = str(value).strip()
    if not str_val or str_val.lower() == "none":
        return False
    
    # Filter out meaningless cl_id patterns (like cl_12345678)
    if re.match(r'^cl_\d+$', str_val, re.IGNORECASE):
        return False
    
    return True

def extract_key_value(obj: Dict[str, Any], key: str, default: str = "") -> str:
    """Extract value from nested dictionary structures, filtering out meaningless values"""
    if not obj or not isinstance(obj, dict):
        return default
    
    value = obj.get(key, default)
    
    # Handle different value formats from UNSW API
    if isinstance(value, dict):
        if "value" in value and is_meaningful_value(value["value"]):
            return str(value["value"])
        elif "label" in value and is_meaningful_value(value["label"]):
            return str(value["label"])
    elif isinstance(value, list) and value:
        # For arrays, take the first meaningful item's value/label
        for item in value:
            if isinstance(item, dict):
                if "value" in item and is_meaningful_value(item["value"]):
                    return str(item["value"])
                elif "label" in item and is_meaningful_value(item["label"]):
                    return str(item["label"])
    elif is_meaningful_value(value):
        return str(value)
    
    return default


def extract_list_values(obj: List[Dict[str, Any]], key: str = "value") -> List[str]:
    """Extract meaningful values from list of objects, filtering out empty/useless values"""
    if not obj or not isinstance(obj, list):
        return []
    
    values = []
    for item in obj:
        if isinstance(item, dict):
            if key in item and is_meaningful_value(item[key]):
                values.append(str(item[key]))
            elif "label" in item and is_meaningful_value(item["label"]):
                values.append(str(item["label"]))
    
    return values


def beautify_field_name(field_name: str) -> str:
    """Convert technical field names to more readable format"""
    # Remove common prefixes/suffixes
    field_name = re.sub(r'(_value|_label|_single)$', '', field_name)
    
    # Handle common field name patterns
    field_mappings = {
        'parent_academic_org': 'faculty',
        'academic_org': 'school', 
        'full_time_duration': 'duration_fulltime',
        'part_time_duration': 'duration_parttime',
        'entry_requirements_onshore': 'entry_requirements_domestic',
        'entry_requirements_offshore': 'entry_requirements_international',
        'indicative_fee': 'fee_domestic',
        'indicative_fee_international': 'fee_international',
        'uac_code_single': 'uac_code',
        'credit_points': 'credits'
    }
    
    # Apply mappings
    for old_name, new_name in field_mappings.items():
        if old_name in field_name:
            field_name = field_name.replace(old_name, new_name)
    
    return field_name


def extract_all_meaningful_fields(obj: Any, prefix: str = "") -> Dict[str, str]:
    """
    Recursively extract all meaningful fields from a nested object structure.
    This ensures no valuable data is lost during content cleaning.
    """
    result = {}
    
    if isinstance(obj, dict):
        for key, value in obj.items():
            field_name = f"{prefix}_{key}" if prefix else key
            
            # Keep all fields - no filtering
            # Skip only truly empty/meaningless values
            if not is_meaningful_value(value):
                continue
            
            if isinstance(value, (dict, list)):
                # Recursively process nested structures
                nested_fields = extract_all_meaningful_fields(value, field_name)
                result.update(nested_fields)
            else:
                # Extract scalar values
                if is_meaningful_value(value):
                    result[field_name] = str(value)
                    
    elif isinstance(obj, list):
        # Handle lists by extracting meaningful values
        meaningful_values = []
        for i, item in enumerate(obj):
            if isinstance(item, dict):
                # For objects in list, try to extract key meaningful fields
                if "value" in item and is_meaningful_value(item["value"]):
                    meaningful_values.append(str(item["value"]))
                elif "label" in item and is_meaningful_value(item["label"]):
                    meaningful_values.append(str(item["label"]))
                elif "description" in item and is_meaningful_value(item["description"]):
                    meaningful_values.append(clean_text(item["description"]))
                else:
                    # Extract all meaningful fields from object
                    nested_fields = extract_all_meaningful_fields(item, f"{prefix}_{i}" if prefix else str(i))
                    result.update(nested_fields)
            elif is_meaningful_value(item):
                meaningful_values.append(str(item))
        
        if meaningful_values:
            result[prefix or "values"] = ", ".join(meaningful_values)
    
    return result

def generate_program_structure_formatted(content: Dict[str, Any]) -> str:
    cs = content.get("curriculumStructure", {})
    containers = cs.get("container", [])
    sections = []

    for container in containers:
        title = container.get("title", "").strip()
        description = container.get("description", "").replace("<br />", "\n").strip()

        rels = container.get("relationship", [])
        specialisations = []
        for rel in rels:
            if not rel.get("academic_item_active", False):
                continue

            code = rel.get("academic_item_code", "")
            name = rel.get("academic_item_name", "")
            url = rel.get("academic_item_url", "")
            uoc = rel.get("academic_item_credit_points", "")
            specialisations.append(f"- {code} **{name}** – {uoc} UOC – [{url}]({url})")

        section_md = f"### {title}\n\n{description}\n\n" + "\n".join(specialisations)
        sections.append(section_md)

    return "\n\n---\n\n".join(sections)

def generate_associated_programs_formatted(content: Dict[str, Any]) -> str:
    """
    Generate formatted associated programs from `associated_programs` nested JSON.
    """
    programs_sections = []
    associations = content.get("associated_programs", [])

    for assoc in associations:
        assoc_type = assoc.get("association_type") or assoc.get("association_type", {}).get("label", "")
        if assoc_type:
            programs_sections.append(f"### {assoc_type}")

        for program in assoc.get("associated_programs", []):
            program_info = []

            title = program.get("assoc_title", "")
            short_title = program.get("assoc_short_title", "")
            award = program.get("assoc_award_single", "")
            duration = program.get("assoc_duration_hb_display", "")
            campus = program.get("assoc_campus", "")
            credits = program.get("assoc_credit_points", "")
            url = program.get("assoc_url", "")
            full_url = f"https://www.handbook.unsw.edu.au{url}" if url else ""

            if short_title:
                program_info.append(f"**Program:** {short_title}")
            elif title:
                program_info.append(f"**Program:** {title}")
            if award:
                program_info.append(f"**Award:** {award}")
            if duration:
                program_info.append(f"**Duration:** {duration}")
            if campus:
                program_info.append(f"**Campus:** {campus}")
            if credits:
                program_info.append(f"**Credits:** {credits} UOC")
            if full_url:
                program_info.append(f"[🔗 View program]({full_url})")

            if program_info:
                programs_sections.append("  ".join(program_info))

    return "\n\n".join(programs_sections)

def generate_entry_requirements_formatted(content: Dict[str, Any]) -> str:
    """
    Generate formatted entry requirements from any `entry_requirements_*` field.
    Supports both flat (_domain/_requirements) and structured list formats.
    """
    requirements_sections = []
    entry_req_groups = {}

    for key, value in content.items():
        if "entry_requirements_" not in key:
            continue
        
        if isinstance(value, list):
            for block in value:
                if not isinstance(block, dict):
                    continue
                domain = block.get("domain", "").strip()
                req_list = block.get("requirements", [])
                if not isinstance(req_list, list):
                    continue
                paragraph_parts = []
                for req in req_list:
                    if not isinstance(req, dict):
                        continue
                    desc = req.get("description", "")
                    clean_desc = clean_text(desc)
                    if clean_desc:
                        paragraph_parts.append(clean_desc)
                if paragraph_parts:
                    combined = "\n".join(paragraph_parts)
                    if domain:
                        requirements_sections.append(f"### {domain}\n{combined}")
                    else:
                        requirements_sections.append(combined)

        elif isinstance(value, str) and is_meaningful_value(value):
            if key.endswith("_domain"):
                base = key[:-7]
                entry_req_groups.setdefault(base, {})["domain"] = clean_text(value)
            elif key.endswith("_requirements"):
                base = key[:-13]
                entry_req_groups.setdefault(base, {})["requirements"] = clean_text(value)

    for base_name, section_data in sorted(entry_req_groups.items()):
        domain = section_data.get("domain", "")
        requirements = section_data.get("requirements", "")
        if domain and requirements:
            requirements_sections.append(f"### {domain}\n{requirements}")
        elif requirements:
            requirements_sections.append(requirements)

    result = "\n\n".join(requirements_sections)
    return result

def generate_recognition_of_achievements_formatted(content: Dict[str, Any]) -> str:
    """
    Convert the 'recognition_of_achievements' dictionary to markdown format.
    """
    achievements_sections = []
    achievements = content.get("recognition_of_achievements", [])

    cardtitle = achievements.get("cardtitle", {}).get("text", "").strip()
    if cardtitle:
        achievements_sections.append(f"## {cardtitle}")

    cardsubtitle = achievements.get("cardsubtitle", {}).get("text", "").strip()
    if cardsubtitle:
        achievements_sections.append(f"### {cardsubtitle}")

    content_items = achievements.get("content", [])
    for item in sorted(content_items, key=lambda x: x.get("order", 0)):
        if "text" in item:
            achievements_sections.append(item["text"].strip())
        elif "label" in item and "value" in item:
            label = item["label"].strip()
            url = item["value"].strip()
            achievements_sections.append(f"[{label}]({url})")

    return "\n\n".join(achievements_sections)


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
    
    # Generate formatted program structure
    program_structure_formatted = generate_program_structure_formatted(content)
    if program_structure_formatted:
        cleaned["program_structure_formatted"] = program_structure_formatted
    
    # Generate formatted entry requirements from entry_requirements_* fields
    entry_requirements_formatted = generate_entry_requirements_formatted(content)
    if entry_requirements_formatted:
        cleaned["entry_requirements_formatted"] = entry_requirements_formatted
    
    # Generate formatted associated programs from associated_programs_* fields
    associated_programs_formatted = generate_associated_programs_formatted(content)
    if associated_programs_formatted:
        cleaned["associated_programs_formatted"] = associated_programs_formatted
        
    # Generate formatted recognition of achievement
    recognition_of_achievements_formatted = generate_recognition_of_achievements_formatted(content)
    if recognition_of_achievements_formatted:
        cleaned["recognition_of_achievements_formatted"] = recognition_of_achievements_formatted    
    
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
            elif is_meaningful_value(req_data):
                cleaned[req_field] = clean_text(str(req_data))
    
    return cleaned


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


def scrape_single_page(url: str) -> Optional[Document]:
    """
    使用 __NEXT_DATA__ 脚本提取 UNSW handbook 页面结构化内容。
    适用于 program/specialisation/course 页面。
    """
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
        page_content = next_data.get("props", {}).get("pageProps", {}).get("pageContent", {})
        if not page_content:
            print("⚠️ 无 pageContent 字段")
            return None

        # Clean and extract content using new data cleansing functions
        cleaned_content = clean_academic_content(page_content)
        
        # Build comprehensive structured content text, preserving maximum information
        content_parts = []
        
        # Title and basic info
        title = cleaned_content.get("title", "").strip()
        code = cleaned_content.get("code", "").strip()
        source = url.strip()
        type_label = (
            cleaned_content.get("contentTypeLabel") or
            cleaned_content.get("academic_item_type")
        )
        
        if type_label == "Double Degree":
            type_label = "Double Degree Program"

        if title:
            content_parts.append(f"# {title} - {type_label} {code}")

        if code:
            content_parts.append(f"**{type_label} Code:** {code}")
            
        if source:
            content_parts.append(f"**Source URL:** {source}")
        
        # Academic details
        academic_info = []
        academic_fields = [
            ("faculty", "Faculty"), ("school", "School"), ("study_level", "Study Level"),
            ("credit_points", "Credit Points"), ("duration", "Duration"), 
            ("part_time_duration", "Part-time Duration"), ("program_type", "Program Type"),
            ("content_type", "Content Type"), ("type", "Type")
        ]
        
        for field, label in academic_fields:
            if cleaned_content.get(field):
                academic_info.append(f"**{label}:** {cleaned_content[field]}")
                
        # 1. Academic Information
        if academic_info:
            content_parts.append("## Academic Information")
            content_parts.append(" ".join(academic_info))
        
        # 2. Overview
        if cleaned_content.get("description"):
            content_parts.append(f"## Overview\n{cleaned_content['description']}")
            
        # 3. Learning outcomes (formatted as numbered list)
        if cleaned_content.get("learning_outcomes_formatted"):
            content_parts.append(f"## Learning Outcomes\n{cleaned_content['learning_outcomes_formatted']}")
        elif cleaned_content.get("learning_outcomes"):
            content_parts.append(f"## Learning Outcomes\n{cleaned_content['learning_outcomes']}")
        
        # 4.1 Program Structure
        if cleaned_content.get("structure_summary"):
            content_parts.append(f"## Program Structure\n{cleaned_content['structure_summary']}\n{cleaned_content['program_structure_formatted']}")
        
        # 5. Admission Requirements (comprehensive)
        if cleaned_content.get("entry_requirements_formatted"):
            content_parts.append(f"## Admission Requirements\n{cleaned_content['entry_requirements_formatted']}")

        # 6. Program Requirements
        if cleaned_content.get("additional_progression_requirements_restrictions"):
            content_parts.append(f"## Program Requirements\n{cleaned_content['additional_progression_requirements_restrictions']}")
        if cleaned_content.get("assumed_knowledge"):
            content_parts.append(f"## Assumed Knowledge\n{cleaned_content['assumed_knowledge']}")
        
        # 7. Associated Programs
        if cleaned_content.get("associated_programs_formatted"):
            content_parts.append(f"## Associated Programs\n{cleaned_content['associated_programs_formatted']}")
        
        # 8. Recognition of Achievements
        if cleaned_content.get("recognition_of_achievements_formatted"):
            content_parts.append(f"## Recognition of Achievements\n{cleaned_content['recognition_of_achievements_formatted']}")
        
        # 9. Program Fees
        program_fees = """
            At UNSW fees are generally charged at course level and therefore dependent upon individual enrolment and other factors such as student's residency status. For generic information on fees and additional expenses of UNSW programs, click on one of the following:
            - [Domestic Students](https://student.unsw.edu.au/fees-domestic-full-fee-paying)
            - [Commonwealth Supported Students (if applicable)](https://student.unsw.edu.au/fees-student-contribution-rates)
            - [International Students](https://student.unsw.edu.au/fees-international)
        """
        if "Program" in type_label:
            content_parts.append(f"## Program Fees\n{cleaned_content['assessment']}")
        if cleaned_content.get("additional_info"):
            content_parts.append(f"### Additional Info\n{cleaned_content['additional_info']}")
        
        if cleaned_content.get("teaching_methods"):
            content_parts.append(f"## Teaching Methods\n{cleaned_content['teaching_methods']}")        
      
        # Career and professional information
        if cleaned_content.get("career_opportunities"):
            content_parts.append(f"## Career Opportunities\n{cleaned_content['career_opportunities']}")
        
        if cleaned_content.get("professional_recognition"):
            content_parts.append(f"## Professional Recognition\n{cleaned_content['professional_recognition']}")
        
        if cleaned_content.get("accreditation"):
            content_parts.append(f"## Accreditation\n{cleaned_content['accreditation']}")
        
        # Specializations and majors
        if cleaned_content.get("specializations"):
            content_parts.append(f"## Specializations\n{cleaned_content['specializations']}")
        
        if cleaned_content.get("majors"):
            content_parts.append(f"## Majors\n{cleaned_content['majors']}")
        
        # Study details and logistics
        study_details = []
        study_fields = [
            ("study_modes", "Study Modes"), ("intake_periods", "Intake Periods"),
            ("campus", "Campus"), ("contact_hours", "Contact Hours"),
            ("workload", "Workload"), ("min_units", "Minimum Units"),
            ("max_units", "Maximum Units")
        ]
        
        for field, label in study_fields:
            if cleaned_content.get(field):
                study_details.append(f"**{label}:** {cleaned_content[field]}")
        
        if study_details:
            content_parts.append("## Study Details")
            content_parts.append(" ".join(study_details))
        
        # Fees and costs
        fee_info = []
        if cleaned_content.get("indicative_fee"):
            fee_info.append(f"**Domestic Fee:** {cleaned_content['indicative_fee']}")
        if cleaned_content.get("indicative_fee_international"):
            fee_info.append(f"**International Fee:** {cleaned_content['indicative_fee_international']}")
        
        if fee_info:
            content_parts.append("## Fees")
            content_parts.append(" ".join(fee_info))
        
        # Administrative information
        admin_info = []
        admin_fields = [
            ("cricos_code", "CRICOS Code"), ("uac_code", "UAC Code"), ("atar", "ATAR")
        ]
        
        for field, label in admin_fields:
            if cleaned_content.get(field):
                admin_info.append(f"**{label}:** {cleaned_content[field]}")
        
        if admin_info:
            content_parts.append("## Administrative Information")
            content_parts.append(" ".join(admin_info))
        
        # Progression requirements
        if cleaned_content.get("progression_requirements"):
            content_parts.append(f"## Progression Requirements\n{cleaned_content['progression_requirements']}")

        # Join all parts with double newline for proper markdown spacing
        full_text = "\n\n".join(content_parts).strip()

        # Create comprehensive metadata
        metadata = {
            "source": url,
            "scraped_at": datetime.utcnow().isoformat(),
            "content_length": len(full_text),
        }
        
        # Add all cleaned content fields to metadata
        metadata.update(cleaned_content)

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


def scrape_urls_batch(urls: List[str], save_content: bool = True, delay_range: tuple = (2.0, 5.0)) -> List[Document]:
    """
    Batch scrape URLs with anti-blocking measures
    
    Args:
        urls: List of URLs to scrape
        save_content: Whether to save content to files
        delay_range: (min_delay, max_delay) in seconds between requests
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
        
        doc = scrape_single_page(url)
        if doc:
            docs.append(doc)
            if save_content:
                save_page_content(doc)
            print(f"✅ Successfully scraped: {doc.metadata.get('title', 'Unknown')}")
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
