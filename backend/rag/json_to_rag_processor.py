"""
Generic JSON to RAG Processor
Automated system to convert complex JSON structures into RAG-suitable format
Combines analysis, extraction, cleaning, and formatting in one comprehensive module
"""

import json
import re
import html
import os
from datetime import datetime
from typing import Dict, Any, List, Optional, Union, Tuple
from collections import Counter, defaultdict
from bs4 import BeautifulSoup
from langchain.docstore.document import Document


class JSONToRAGProcessor:
    """Complete automation system for converting JSON to RAG format"""
    
    def __init__(self):
        # Field name patterns that indicate content
        self.content_field_patterns = {
            'description', 'content', 'text', 'body', 'overview', 'summary', 
            'details', 'info', 'information', 'notes', 'comments', 'remarks',
            'learning_outcomes', 'requirements', 'opportunities', 'structure_summary',
            'career_opportunities', 'entry_requirements', 'progression_requirements'
        }
        
        # Field name patterns that indicate metadata
        self.metadata_field_patterns = {
            'title', 'name', 'code', 'id', 'type', 'level', 'category', 'status',
            'faculty', 'school', 'department', 'organization', 'location', 'campus',
            'duration', 'credit_points', 'points', 'credits', 'hours', 'study_level',
            'implementation_year', 'cricos_code', 'uac_code'
        }
        
        # Field patterns to ignore (likely meaningless)
        self.ignore_field_patterns = {
            'cl_id', 'key', 'sys_id', 'uuid', 'version', 'revision',
            'created_at', 'updated_at', 'modified_at', 'timestamp',
            'internal_id', 'reference_id', 'external_id', 'workflow_state'
        }
        
        # Meaningless phrases to remove
        self.meaningless_phrases = {
            'tbd', 'to be determined', 'n/a', 'not applicable', 'null', 'none',
            'undefined', 'empty', 'no data', 'no information', 'coming soon',
            'please check', 'see website', 'contact us', 'more information'
        }
        
        # Boilerplate patterns in academic content
        self.boilerplate_patterns = [
            r'©.*?rights reserved',
            r'this page was last updated.*',
            r'for more information.*visit.*',
            r'please note.*may be subject to change',
            r'disclaimer:.*',
            r'copyright.*university.*'
        ]
    
    def process_json_file(self, filepath: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """Complete processing pipeline for a JSON file"""
        try:
            # Load JSON data
            with open(filepath, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            # Process the data
            result = self.process_json_data(json_data, source_file=filepath)
            
            # Save output if directory specified
            if output_dir and result.get('rag_document'):
                os.makedirs(output_dir, exist_ok=True)
                filename = os.path.basename(filepath).replace('.json', '_processed.json')
                output_path = os.path.join(output_dir, filename)
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(result['rag_document'], f, indent=2, ensure_ascii=False)
                
                result['output_path'] = output_path
            
            return result
            
        except Exception as e:
            return {'error': f"Failed to process {filepath}: {e}"}
    
    def process_json_data(self, json_data: Dict[str, Any], source_file: Optional[str] = None) -> Dict[str, Any]:
        """Complete processing pipeline for JSON data"""
        # Step 1: Analyze structure
        analysis = self._analyze_json_structure(json_data)
        
        # Step 2: Extract content
        extracted = self._extract_content(json_data, analysis)
        
        # Step 3: Clean content
        cleaned = self._clean_content(extracted)
        
        # Step 4: Format for RAG
        rag_document = self._format_for_rag(cleaned, source_file)
        
        # Step 5: Create Document object
        document = self._create_document(rag_document)
        
        return {
            'analysis': analysis,
            'extracted': extracted,
            'cleaned': cleaned,
            'rag_document': rag_document,
            'langchain_document': document,
            'processing_stats': {
                'content_fields_found': len(analysis.get('content_fields', [])),
                'metadata_fields_found': len(analysis.get('metadata_fields', [])),
                'final_content_length': len(rag_document.get('page_content', '')),
                'final_metadata_count': len(rag_document.get('metadata', {}))
            }
        }
    
    def _analyze_json_structure(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze JSON structure and classify fields"""
        analysis = {
            'content_fields': [],
            'metadata_fields': [],
            'ignore_fields': [],
            'nested_objects': [],
            'arrays': [],
            'field_stats': {},
            'processing_strategy': None
        }
        
        self._analyze_recursive(json_data, analysis, path="")
        analysis['processing_strategy'] = self._determine_processing_strategy(analysis)
        
        return analysis
    
    def _analyze_recursive(self, data: Any, analysis: Dict, path: str = "", depth: int = 0):
        """Recursively analyze JSON structure"""
        if depth > 5:  # Prevent infinite recursion
            return
            
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                
                # Classify field based on name and value
                field_type = self._classify_field(key, value)
                field_info = {
                    'path': current_path,
                    'type': type(value).__name__,
                    'classification': field_type,
                    'value_length': len(str(value)) if value else 0
                }
                
                analysis['field_stats'][current_path] = field_info
                
                if field_type == 'content':
                    analysis['content_fields'].append(field_info)
                elif field_type == 'metadata':
                    analysis['metadata_fields'].append(field_info)
                elif field_type == 'ignore':
                    analysis['ignore_fields'].append(field_info)
                
                # Handle nested structures
                if isinstance(value, dict):
                    analysis['nested_objects'].append(current_path)
                    self._analyze_recursive(value, analysis, current_path, depth + 1)
                elif isinstance(value, list):
                    analysis['arrays'].append(current_path)
                    if value and isinstance(value[0], (dict, list)):
                        self._analyze_recursive(value[0], analysis, f"{current_path}[0]", depth + 1)
        
        elif isinstance(data, list) and data:
            # Analyze first few items in arrays
            for i, item in enumerate(data[:3]):
                if isinstance(item, (dict, list)):
                    self._analyze_recursive(item, analysis, f"{path}[{i}]", depth + 1)
    
    def _classify_field(self, field_name: str, value: Any) -> str:
        """Classify a field as content, metadata, or ignore"""
        field_lower = field_name.lower()
        
        # Check ignore patterns first
        if any(pattern in field_lower for pattern in self.ignore_field_patterns):
            return 'ignore'
        
        # Check if value should be ignored
        if self._is_meaningless_value(value):
            return 'ignore'
        
        # Check content patterns
        if any(pattern in field_lower for pattern in self.content_field_patterns):
            return 'content'
        
        # Check if value looks like content (long text)
        if isinstance(value, str) and (len(value) > 100 or '<' in value):
            return 'content'
        
        # Check metadata patterns
        if any(pattern in field_lower for pattern in self.metadata_field_patterns):
            return 'metadata'
        
        # Handle nested objects with 'value' or 'label' patterns
        if isinstance(value, dict) and ('value' in value or 'label' in value):
            return 'metadata'
        
        # Check if it's a simple value that could be metadata
        if isinstance(value, (str, int, float)) and len(str(value)) < 100:
            return 'metadata'
        
        # Default to content if unsure
        return 'content'
    
    def _determine_processing_strategy(self, analysis: Dict) -> str:
        """Determine the best processing strategy"""
        content_fields = len(analysis['content_fields'])
        metadata_fields = len(analysis['metadata_fields'])
        nested_objects = len(analysis['nested_objects'])
        
        if content_fields > 5 and nested_objects > 3:
            return 'complex_academic'
        elif content_fields > 3:
            return 'content_rich'
        elif metadata_fields > content_fields:
            return 'metadata_heavy'
        else:
            return 'simple'
    
    def _extract_content(self, json_data: Dict[str, Any], analysis: Dict) -> Dict[str, Any]:
        """Extract meaningful content from JSON data"""
        extracted = {
            'primary_content': {},
            'metadata': {},
            'structured_lists': {},
            'processing_info': {
                'strategy': analysis.get('processing_strategy'),
                'total_fields': len(analysis.get('field_stats', {})),
                'content_fields': len(analysis.get('content_fields', [])),
                'metadata_fields': len(analysis.get('metadata_fields', []))
            }
        }
        
        # Extract primary content fields
        content_fields = sorted(analysis['content_fields'], key=lambda x: x.get('value_length', 0), reverse=True)
        for field_info in content_fields[:10]:  # Top 10 content fields
            field_path = field_info['path']
            value = self._get_nested_value(json_data, field_path)
            if value and len(str(value)) > 20:
                clean_name = self._clean_field_name(field_path)
                extracted['primary_content'][clean_name] = str(value)
        
        # Extract metadata fields
        for field_info in analysis['metadata_fields'][:15]:  # Top 15 metadata fields
            field_path = field_info['path']
            value = self._get_nested_value(json_data, field_path)
            if value is not None:
                clean_name = self._clean_field_name(field_path)
                extracted['metadata'][clean_name] = self._extract_simple_value(value)
        
        # Extract structured lists
        for array_path in analysis['arrays'][:5]:  # Top 5 arrays
            array_data = self._get_nested_value(json_data, array_path)
            if array_data and isinstance(array_data, list) and len(array_data) > 0:
                clean_name = self._clean_field_name(array_path)
                processed_list = self._process_array(array_data)
                if processed_list:
                    extracted['structured_lists'][clean_name] = processed_list
        
        return extracted
    
    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get value from nested path"""
        try:
            current = data
            for part in path.split('.'):
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return None
            return current
        except (KeyError, TypeError):
            return None
    
    def _extract_simple_value(self, value: Any) -> Any:
        """Extract simple value from complex structures"""
        if isinstance(value, dict):
            if 'value' in value:
                return value['value']
            elif 'label' in value:
                return value['label']
            else:
                return str(value)
        elif isinstance(value, list):
            if value and all(isinstance(item, dict) for item in value):
                # Extract values from list of objects
                values = []
                for item in value[:3]:  # First 3 items
                    if 'value' in item:
                        values.append(str(item['value']))
                    elif 'label' in item:
                        values.append(str(item['label']))
                return ', '.join(values) if values else ''
            else:
                return ', '.join(str(item) for item in value[:3])
        else:
            return value
    
    def _process_array(self, array_data: List) -> Optional[List[str]]:
        """Process array data into meaningful list"""
        if not array_data:
            return None
        
        processed = []
        for item in array_data[:5]:  # Limit to first 5 items
            if isinstance(item, dict):
                # Extract text from object
                text = self._extract_text_from_object(item)
                if text and len(text) > 10:
                    processed.append(text)
            elif isinstance(item, str) and len(item) > 3:
                processed.append(item)
        
        return processed if processed else None
    
    def _extract_text_from_object(self, obj: Dict[str, Any]) -> Optional[str]:
        """Extract meaningful text from an object"""
        if not isinstance(obj, dict):
            return None
        
        # Look for common text fields
        text_fields = ['description', 'text', 'content', 'value', 'label', 'name', 'title']
        
        for field in text_fields:
            if field in obj and obj[field]:
                value = obj[field]
                if isinstance(value, str) and len(value.strip()) > 10:
                    return value.strip()
        
        return None
    
    def _clean_field_name(self, field_path: str) -> str:
        """Convert field path to clean name"""
        field_name = field_path.split('.')[-1]
        field_name = re.sub(r'\[\d+\]', '', field_name)
        field_name = field_name.replace('_', ' ').title()
        return field_name
    
    def _clean_content(self, extracted: Dict[str, Any]) -> Dict[str, Any]:
        """Clean extracted content"""
        cleaned = {
            'primary_content': {},
            'metadata': {},
            'structured_lists': {},
            'processing_info': extracted.get('processing_info', {}),
            'cleaning_stats': {
                'html_cleaned': 0,
                'whitespace_normalized': 0,
                'meaningless_removed': 0
            }
        }
        
        # Clean primary content
        for key, value in extracted.get('primary_content', {}).items():
            if isinstance(value, str):
                cleaned_value = self._clean_html_content(value)
                cleaned_value = self._normalize_whitespace(cleaned_value)
                cleaned_value = self._remove_meaningless_text(cleaned_value)
                
                if self._validate_content_quality(cleaned_value):
                    cleaned['primary_content'][key] = cleaned_value
                    if len(cleaned_value) < len(value):
                        cleaned['cleaning_stats']['html_cleaned'] += 1
        
        # Clean metadata
        for key, value in extracted.get('metadata', {}).items():
            if value is not None and not self._is_meaningless_value(value):
                if isinstance(value, str):
                    cleaned_value = self._clean_text_light(value)
                    if cleaned_value:
                        cleaned['metadata'][key] = cleaned_value
                else:
                    cleaned['metadata'][key] = value
        
        # Clean structured lists
        for key, value_list in extracted.get('structured_lists', {}).items():
            if value_list:
                cleaned_list = []
                for item in value_list:
                    if isinstance(item, str):
                        cleaned_item = self._clean_html_content(item)
                        cleaned_item = self._normalize_whitespace(cleaned_item)
                        if self._validate_content_quality(cleaned_item, min_length=10):
                            cleaned_list.append(cleaned_item)
                
                if cleaned_list:
                    cleaned['structured_lists'][key] = cleaned_list
        
        return cleaned
    
    def _clean_html_content(self, text: str) -> str:
        """Clean HTML content"""
        if not text:
            return ""
        
        # Decode HTML entities
        text = html.unescape(text)
        
        # Parse with BeautifulSoup and convert to markdown-like format
        soup = BeautifulSoup(text, "html.parser")
        
        # Handle lists
        for ol in soup.find_all('ol'):
            ol.insert_before('\n\n')
            # For ordered lists, preserve numbering
            for i, li in enumerate(ol.find_all('li'), 1):
                li.insert_before(f'\n{i}. ')
        for ul in soup.find_all('ul'):
            ul.insert_before('\n\n')
            # For unordered lists, use bullet points
            for li in ul.find_all('li'):
                li.insert_before('\n- ')
        
        # Handle paragraphs
        for p in soup.find_all('p'):
            p.insert_before('\n\n')
        
        # Handle line breaks
        for br in soup.find_all('br'):
            br.replace_with('\n')
        
        # Handle headers
        for i in range(1, 7):
            for h in soup.find_all(f'h{i}'):
                h.insert_before('\n\n' + '#' * i + ' ')
        
        return soup.get_text(separator=' ')
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace"""
        if not text:
            return ""
        
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        return text.strip()
    
    def _remove_meaningless_text(self, text: str) -> str:
        """Remove meaningless phrases"""
        if not text:
            return ""
        
        for phrase in self.meaningless_phrases:
            pattern = r'\b' + re.escape(phrase) + r'\b'
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Remove boilerplate patterns
        for pattern in self.boilerplate_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
        
        return text.strip()
    
    def _clean_text_light(self, text: str) -> str:
        """Light cleaning for metadata"""
        if not text:
            return ""
        
        text = html.unescape(str(text))
        text = BeautifulSoup(text, "html.parser").get_text(separator=" ")
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def _validate_content_quality(self, text: str, min_length: int = 20) -> bool:
        """Validate content quality"""
        if not text or len(text.strip()) < min_length:
            return False
        
        words = text.lower().split()
        if len(words) < 3:
            return False
        
        content_words = [word for word in words if len(word) > 3 and word.isalpha()]
        return len(content_words) >= 3
    
    def _is_meaningless_value(self, value: Any) -> bool:
        """Check if value is meaningless"""
        if value is None or value == "":
            return True
        
        if isinstance(value, str):
            value_lower = value.lower().strip()
            return value_lower in self.meaningless_phrases or len(value_lower) < 2
        
        if isinstance(value, (list, dict)) and not value:
            return True
        
        return False
    
    def _format_for_rag(self, cleaned: Dict[str, Any], source_file: Optional[str] = None) -> Dict[str, Any]:
        """Format cleaned content for RAG"""
        content_parts = []
        
        # Build markdown content
        primary_content = cleaned.get('primary_content', {})
        
        # Add title if available
        title_candidates = ['Title', 'Name', 'Program', 'Course']
        title = None
        for candidate in title_candidates:
            if candidate in primary_content:
                title = primary_content[candidate]
                content_parts.append(f"# {title}")
                break
        
        # Add description
        desc_candidates = ['Description', 'Overview', 'Summary']
        for candidate in desc_candidates:
            if candidate in primary_content:
                content_parts.append(f"\n## Description\n{primary_content[candidate]}")
                break
        
        # Add other content sections
        for key, value in primary_content.items():
            if key not in title_candidates + desc_candidates:
                content_parts.append(f"\n## {key}\n{value}")
        
        # Add structured lists
        for key, value_list in cleaned.get('structured_lists', {}).items():
            if value_list:
                content_parts.append(f"\n## {key}")
                for item in value_list:
                    content_parts.append(f"- {item}")
        
        # Combine all content
        page_content = '\n'.join(content_parts).strip()
        
        # Build metadata
        metadata = cleaned.get('metadata', {}).copy()
        metadata.update({
            'processed_at': datetime.utcnow().isoformat(),
            'processing_strategy': cleaned.get('processing_info', {}).get('strategy'),
            'content_length': len(page_content)
        })
        
        if source_file:
            metadata['source_file'] = source_file
        
        if title:
            metadata['title'] = title
        
        return {
            'page_content': page_content,
            'metadata': metadata,
            'saved_at': datetime.utcnow().isoformat()
        }
    
    def _create_document(self, rag_document: Dict[str, Any]) -> Document:
        """Create LangChain Document object"""
        return Document(
            page_content=rag_document.get('page_content', ''),
            metadata=rag_document.get('metadata', {})
        )
    
    def process_batch(self, input_dir: str, output_dir: str, file_pattern: str = "*.json") -> Dict[str, Any]:
        """Process multiple JSON files in batch"""
        import glob
        
        json_files = glob.glob(os.path.join(input_dir, file_pattern))
        results = {
            'processed': [],
            'failed': [],
            'stats': {
                'total_files': len(json_files),
                'successful': 0,
                'failed': 0
            }
        }
        
        os.makedirs(output_dir, exist_ok=True)
        
        for filepath in json_files:
            print(f"Processing {filepath}...")
            result = self.process_json_file(filepath, output_dir)
            
            if 'error' in result:
                results['failed'].append({'file': filepath, 'error': result['error']})
                results['stats']['failed'] += 1
            else:
                results['processed'].append({
                    'file': filepath,
                    'output': result.get('output_path'),
                    'stats': result.get('processing_stats')
                })
                results['stats']['successful'] += 1
        
        print(f"\nBatch processing complete: {results['stats']['successful']} successful, {results['stats']['failed']} failed")
        return results


# Convenience functions
def process_json_file(filepath: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
    """Process a single JSON file"""
    processor = JSONToRAGProcessor()
    return processor.process_json_file(filepath, output_dir)


def process_json_data(json_data: Dict[str, Any], source_file: Optional[str] = None) -> Dict[str, Any]:
    """Process JSON data directly"""
    processor = JSONToRAGProcessor()
    return processor.process_json_data(json_data, source_file)


def process_batch(input_dir: str, output_dir: str, file_pattern: str = "*.json") -> Dict[str, Any]:
    """Process multiple JSON files"""
    processor = JSONToRAGProcessor()
    return processor.process_batch(input_dir, output_dir, file_pattern)


if __name__ == "__main__":
    # Test with 3779.json
    result = process_json_file("/mnt/d/Study/25T2/COMP9900/capstone-project-25t2-9900-f10a-almond/3779.json")
    
    if 'error' not in result:
        print("=== Processing Results ===")
        print(f"Content length: {len(result['rag_document']['page_content'])}")
        print(f"Metadata fields: {len(result['rag_document']['metadata'])}")
        print(f"Processing stats: {result['processing_stats']}")
        
        print("\n=== Generated Content (first 500 chars) ===")
        print(result['rag_document']['page_content'][:500] + "...")
        
        print("\n=== Key Metadata ===")
        for key, value in list(result['rag_document']['metadata'].items())[:10]:
            print(f"{key}: {value}")
    else:
        print(f"Error: {result['error']}")