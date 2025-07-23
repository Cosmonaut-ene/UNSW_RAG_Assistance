from typing import List, Dict
from .keyword_search import SimpleKeywordSearch

class HybridSearchEngine:
    def __init__(self, content_dir: str, min_hybrid_score: float = 70.0, min_keyword_score: float = 10.0, min_rag_score: float = 50.0):
        self.keyword_searcher = SimpleKeywordSearch(content_dir)
        # 权重配置
        self.rag_weight = 0.6
        self.keyword_weight = 0.4
        # 阈值配置
        self.min_hybrid_score = min_hybrid_score
        self.min_keyword_score = min_keyword_score
        self.min_rag_score = min_rag_score
        
    def combine_results(self, rag_results: List[Dict], keyword_results: List[Dict], max_results: int = 5) -> List[Dict]:
        """合并RAG和关键词搜索结果"""
        
        # 标准化RAG结果格式，添加search_type
        for result in rag_results:
            if 'metadata' not in result:
                result['metadata'] = {}
            result['metadata']['search_type'] = 'rag'
            result['metadata']['rag_score'] = 100  # RAG默认满分，因为已经是top结果
            result['metadata']['keyword_score'] = 0
        
        # 确保关键词结果格式正确
        for result in keyword_results:
            if 'metadata' not in result:
                result['metadata'] = {}
            result['metadata']['rag_score'] = 0
            if 'keyword_score' not in result['metadata']:
                result['metadata']['keyword_score'] = 50  # 默认分数
        
        # 合并所有结果
        all_results = []
        seen_sources = set()
        
        # 处理RAG结果
        for result in rag_results:
            source = result.get('metadata', {}).get('source', '')
            if source and source not in seen_sources:
                seen_sources.add(source)
                all_results.append(result)
        
        # 处理关键词结果，避免重复
        for result in keyword_results:
            source = result.get('metadata', {}).get('source', '')
            if source and source not in seen_sources:
                seen_sources.add(source)
                all_results.append(result)
            elif source in seen_sources:
                # 找到重复项，合并分数
                for existing in all_results:
                    if existing.get('metadata', {}).get('source') == source:
                        existing['metadata']['keyword_score'] = result['metadata']['keyword_score']
                        existing['metadata']['search_type'] = 'hybrid'
                        if 'matched_terms' in result['metadata']:
                            existing['metadata']['matched_terms'] = result['metadata']['matched_terms']
                        break
        
        # 计算混合分数
        for result in all_results:
            rag_score = result['metadata'].get('rag_score', 0)
            keyword_score = result['metadata'].get('keyword_score', 0)
            hybrid_score = (rag_score * self.rag_weight) + (keyword_score * self.keyword_weight)
            result['metadata']['hybrid_score'] = hybrid_score
        
        # 应用阈值过滤
        filtered_results = []
        filtered_count = 0
        
        for result in all_results:
            metadata = result['metadata']
            hybrid_score = metadata.get('hybrid_score', 0)
            keyword_score = metadata.get('keyword_score', 0)
            rag_score = metadata.get('rag_score', 0)
            
            # 检查是否满足阈值条件（使用OR逻辑：满足任一条件即可通过）
            passes_hybrid = hybrid_score >= self.min_hybrid_score
            passes_rag = rag_score >= self.min_rag_score
            passes_keyword = keyword_score >= self.min_keyword_score
            
            if passes_hybrid:
                filtered_results.append(result)
                print(f"[HybridSearch] Accepted result from {metadata.get('source', 'unknown')} - "
                      f"Hybrid: {hybrid_score:.2f}, Keyword: {keyword_score:.2f}, RAG: {rag_score:.2f} "
                      f"(Passed: {'Hybrid ' if passes_hybrid else ''}{'RAG ' if passes_rag else ''}{'Keyword' if passes_keyword else ''})")
            else:
                filtered_count += 1
                print(f"[HybridSearch] Filtered out result from {metadata.get('source', 'unknown')} - "
                      f"Hybrid: {hybrid_score:.2f} (min: {self.min_hybrid_score}), "
                      f"Keyword: {keyword_score:.2f} (min: {self.min_keyword_score}), "
                      f"RAG: {rag_score:.2f} (min: {self.min_rag_score})")
        
        if filtered_count > 0:
            print(f"[HybridSearch] Filtered out {filtered_count} low-quality results")
        
        # 按混合分数排序
        filtered_results.sort(key=lambda x: x['metadata']['hybrid_score'], reverse=True)
        
        return filtered_results[:max_results]
    
    def search_hybrid(self, query: str, rag_results: List[Dict] = None, max_results: int = 5) -> List[Dict]:
        """执行混合搜索"""
        
        # 如果没有RAG结果，使用空列表
        if rag_results is None:
            rag_results = []
        
        # 执行关键词搜索
        keyword_results = self.keyword_searcher.search_keywords(query, max_results)
        
        # 合并结果
        combined_results = self.combine_results(rag_results, keyword_results, max_results)
        
        return combined_results