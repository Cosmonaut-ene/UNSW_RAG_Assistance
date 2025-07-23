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
        """加载所有JSON文档内容"""
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
        """从JSON文档中提取所有可搜索的文本"""
        text_parts = []
        
        # 递归提取所有字符串值
        def extract_strings(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    # 跳过一些不重要的字段
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
        """计算匹配分数和匹配项"""
        query_lower = query.lower()
        searchable_text = self._extract_searchable_text(doc)
        
        score = 0
        matched_terms = []
        
        # 检测课程代码 (COMP9900等)
        course_codes = re.findall(r'\b[A-Z]{4}\d{4}\b', query.upper())
        for code in course_codes:
            if code.lower() in searchable_text:
                score += 100
                matched_terms.append(f"Course Code: {code}")
        
        # 检测程序代码 (8543等) 和智能课程代码匹配
        program_codes = re.findall(r'\b\d{4}\b', query)
        for code in program_codes:
            # 直接匹配4位数字
            if code in searchable_text:
                score += 100  
                matched_terms.append(f"Program Code: {code}")
            # 智能匹配：如果查询是4位数字，也搜索COMP+数字格式
            else:
                potential_course_code = f"comp{code}"
                if potential_course_code in searchable_text:
                    score += 90  # 稍低于完全匹配的分数
                    matched_terms.append(f"Course Code Match: COMP{code}")
        
        # 反向匹配：如果文档包含COMP代码，也匹配查询中的数字
        doc_course_codes = re.findall(r'\bcomp\d{4}\b', searchable_text)
        query_numbers = re.findall(r'\b\d{4}\b', query_lower)
        for doc_code in doc_course_codes:
            course_number = doc_code[4:]  # 提取COMP后的数字
            if course_number in query_numbers:
                score += 90
                matched_terms.append(f"Reverse Course Match: {doc_code.upper()}")
        
        # 关键词匹配
        query_terms = [term for term in query_lower.split() if len(term) > 2]
        for term in query_terms:
            if term in searchable_text:
                # 计算词频
                term_count = searchable_text.count(term)
                score += min(term_count * 5, 25)  # 限制单词的最大贡献
                matched_terms.append(f"Keyword: {term}")
        
        # 短语匹配
        if len(query_terms) > 1 and query_lower in searchable_text:
            score += 30
            matched_terms.append("Phrase Match")
        
        return score, matched_terms
    
    def search_keywords(self, query: str, max_results: int = 5) -> List[Dict]:
        """执行关键词搜索，返回page_content格式"""
        if not query.strip():
            return []
        
        results = []
        
        for doc in self.documents:
            score, matched_terms = self._calculate_match_score(query, doc)
            
            if score > 0:
                # 统一返回page_content格式
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
        
        # 按分数排序
        results.sort(key=lambda x: x['metadata']['keyword_score'], reverse=True)
        return results[:max_results]