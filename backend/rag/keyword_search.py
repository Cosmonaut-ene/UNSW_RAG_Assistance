import json
import re
from typing import List, Dict
from pathlib import Path

class SimpleKeywordSearch:
    def __init__(self, content_dir: str):
        self.content_dir = content_dir
        self.documents = []
        self.load_documents()
    
    def load_documents(self):
        """Load all JSON document content"""
        content_path = Path(self.content_dir)
        if not content_path.exists():
            print(f"Content directory not found: {self.content_dir}")
            return
        
        for json_file in content_path.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.documents.append(data)
            except Exception as e:
                print(f"Error loading {json_file}: {e}")
                
        print(f"Loaded {len(self.documents)} documents for keyword search")
    
    def _extract_searchable_text(self, doc: dict) -> str:
        """Extract all searchable text from JSON document"""
        text_parts = []
        
        # Recursively extract all string values
        def extract_strings(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    # Skip some unimportant fields
                    if key in ['saved_at', 'scraped_at', 'content_length']:
                        continue
                    extract_strings(value)
            elif isinstance(obj, list):
                for item in obj:
                    extract_strings(item)
            elif isinstance(obj, str) and obj.strip():
                text_parts.append(obj.strip())
        
        extract_strings(doc)
        return ' '.join(text_parts).lower()
    
    def _calculate_match_score(self, query: str, doc: dict) -> tuple[int, list]:
        """Calculate match score and matched items"""
        query_lower = query.lower()
        searchable_text = self._extract_searchable_text(doc)
        
        score = 0
        matched_terms = []
        
        # Detect course codes (COMP9900, etc.)
        course_codes = re.findall(r'\b[A-Z]{4}\d{4}\b', query.upper())
        for code in course_codes:
            if code.lower() in searchable_text:
                score += 100
                matched_terms.append(f"Course Code: {code}")
        
        # Detect program codes (8543, etc.) and intelligent course code matching
        program_codes = re.findall(r'\b\d{4}\b', query)
        for code in program_codes:
            # Direct match for 4-digit numbers
            if code in searchable_text:
                score += 100  
                matched_terms.append(f"Program Code: {code}")
            # Smart matching: if query is 4-digit number, also search COMP+number format
            else:
                potential_course_code = f"comp{code}"
                if potential_course_code in searchable_text:
                    score += 90  # Slightly lower than perfect match score
                    matched_terms.append(f"Course Code Match: COMP{code}")
        
        # Reverse matching: if document contains COMP codes, also match numbers in query
        doc_course_codes = re.findall(r'\bcomp\d{4}\b', searchable_text)
        query_numbers = re.findall(r'\b\d{4}\b', query_lower)
        for doc_code in doc_course_codes:
            course_number = doc_code[4:]  # Extract number after COMP
            if course_number in query_numbers:
                score += 90
                matched_terms.append(f"Reverse Course Match: {doc_code.upper()}")
        
        # Keyword matching
        query_terms = [term for term in query_lower.split() if len(term) > 2]
        for term in query_terms:
            if term in searchable_text:
                # Calculate term frequency
                term_count = searchable_text.count(term)
                score += min(term_count * 5, 25)  # Limit maximum contribution per word
                matched_terms.append(f"Keyword: {term}")
        
        # Phrase matching
        if len(query_terms) > 1 and query_lower in searchable_text:
            score += 30
            matched_terms.append("Phrase Match")
        
        return score, matched_terms
    
    def search_keywords(self, query: str, max_results: int = 5) -> List[Dict]:
        """Execute keyword search, return page_content format"""
        if not query.strip():
            return []
        
        results = []
        
        for doc in self.documents:
            score, matched_terms = self._calculate_match_score(query, doc)
            
            if score > 0:
                # Unified return format as page_content
                result = {
                    'page_content': doc.get('page_content', ''),
                    'metadata': {
                        'source': doc.get('metadata', {}).get('source', ''),
                        'search_type': 'keyword',
                        'keyword_score': score,
                        'matched_terms': matched_terms
                    }
                }
                results.append(result)
        
        # Sort by score
        results.sort(key=lambda x: x['metadata']['keyword_score'], reverse=True)
        return results[:max_results]