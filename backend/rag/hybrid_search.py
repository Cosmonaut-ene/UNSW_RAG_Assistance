from typing import List, Dict, Optional
from .bm25_search import BM25SearchEngine

class HybridSearchEngine:
    def __init__(self, vector_store=None, min_hybrid_score: float = 50.0, min_bm25_score: float = 5.0, min_rag_score: float = 30.0):
        self.bm25_searcher = BM25SearchEngine(vector_store)
        # Weight configuration
        self.rag_weight = 0.6
        self.bm25_weight = 0.4
        # Threshold configuration  
        self.min_hybrid_score = min_hybrid_score
        self.min_bm25_score = min_bm25_score
        self.min_rag_score = min_rag_score
        
    def combine_results(self, rag_results: List[Dict], bm25_results: List[Dict], max_results: int = 5) -> List[Dict]:
        """Combine RAG and BM25 search results"""
        
        # Standardize RAG result format, add search_type
        for result in rag_results:
            if 'metadata' not in result:
                result['metadata'] = {}
            result['metadata']['search_type'] = 'rag'
            result['metadata']['rag_score'] = 100  # RAG defaults to full score as top results
            result['metadata']['bm25_score'] = 0
        
        # Standardize BM25 results format
        for result in bm25_results:
            if 'metadata' not in result:
                result['metadata'] = {}
            result['metadata']['search_type'] = 'bm25'
            result['metadata']['rag_score'] = 0
            # Normalize BM25 score to 0-100 range (BM25 scores are typically 0-15)
            raw_bm25_score = result.get('bm25_score', 0)
            normalized_score = min(raw_bm25_score * 10, 100)  # Scale up and cap at 100
            result['metadata']['bm25_score'] = normalized_score
        
        # Merge all results by content similarity (since both work on same chunks now)
        all_results = []
        seen_content = set()
        
        # Process RAG results
        for result in rag_results:
            content = result.get('page_content', result.get('content', ''))[:100]  # Use first 100 chars as ID
            if content and content not in seen_content:
                seen_content.add(content)
                all_results.append(result)
        
        # Process BM25 results, avoid duplicates by content
        for result in bm25_results:
            content = result.get('content', result.get('page_content', ''))[:100]
            if content and content not in seen_content:
                seen_content.add(content)
                # Convert BM25 result format to standard format
                standardized_result = {
                    'page_content': result.get('content', ''),
                    'metadata': result.get('metadata', {}),
                    'content': result.get('content', '')
                }
                standardized_result['metadata']['bm25_score'] = result['metadata']['bm25_score']
                all_results.append(standardized_result)
            elif content in seen_content:
                # Found duplicate, merge BM25 score with existing result
                for existing in all_results:
                    existing_content = existing.get('page_content', existing.get('content', ''))[:100]
                    if existing_content == content:
                        existing['metadata']['bm25_score'] = result['metadata']['bm25_score']
                        existing['metadata']['search_type'] = 'hybrid'
                        break
        
        # Calculate hybrid scores
        for result in all_results:
            rag_score = result['metadata'].get('rag_score', 0)
            bm25_score = result['metadata'].get('bm25_score', 0)
            hybrid_score = (rag_score * self.rag_weight) + (bm25_score * self.bm25_weight)
            result['metadata']['hybrid_score'] = hybrid_score
        
        # Apply threshold filtering
        filtered_results = []
        filtered_count = 0
        
        for result in all_results:
            metadata = result['metadata']
            hybrid_score = metadata.get('hybrid_score', 0)
            bm25_score = metadata.get('bm25_score', 0)
            rag_score = metadata.get('rag_score', 0)
            
            # Check if threshold conditions are met (using OR logic: any condition passes)
            passes_hybrid = hybrid_score >= self.min_hybrid_score
            passes_rag = rag_score >= self.min_rag_score
            passes_bm25 = bm25_score >= self.min_bm25_score
            
            if passes_hybrid:
                filtered_results.append(result)
                print(f"[HybridSearch] Accepted result from {metadata.get('source', 'unknown')} - "
                      f"Hybrid: {hybrid_score:.2f}, BM25: {bm25_score:.2f}, RAG: {rag_score:.2f} "
                      f"(Passed: {'Hybrid ' if passes_hybrid else ''}{'RAG ' if passes_rag else ''}{'BM25' if passes_bm25 else ''})")
            else:
                filtered_count += 1
                print(f"[HybridSearch] Filtered out result from {metadata.get('source', 'unknown')} - "
                      f"Hybrid: {hybrid_score:.2f} (min: {self.min_hybrid_score}), "
                      f"BM25: {bm25_score:.2f} (min: {self.min_bm25_score}), "
                      f"RAG: {rag_score:.2f} (min: {self.min_rag_score})")
        
        if filtered_count > 0:
            print(f"[HybridSearch] Filtered out {filtered_count} low-quality results")
        
        # Sort by hybrid score
        filtered_results.sort(key=lambda x: x['metadata']['hybrid_score'], reverse=True)
        
        return filtered_results[:max_results]
    
    def search_hybrid(self, query: str, rag_results: List[Dict] = None, max_results: int = 5) -> List[Dict]:
        """Execute hybrid search with BM25"""
        
        # If no RAG results, use empty list
        if rag_results is None:
            rag_results = []
        
        # Execute BM25 search
        print(f"[HybridSearch] Executing BM25 search with query: '{query}'")
        bm25_results = self.bm25_searcher.search(query, top_k=max_results * 2)  # Get more for better selection
        print(f"[HybridSearch] BM25 search returned {len(bm25_results)} results")
        
        # Log input statistics
        print(f"[HybridSearch] Input: {len(rag_results)} RAG results, {len(bm25_results)} BM25 results")
        
        # Combine results
        combined_results = self.combine_results(rag_results, bm25_results, max_results)
        
        # Log combination statistics
        hybrid_count = sum(1 for r in combined_results if r.get('metadata', {}).get('search_type') == 'hybrid')
        rag_only_count = sum(1 for r in combined_results if r.get('metadata', {}).get('search_type') == 'rag')  
        bm25_only_count = sum(1 for r in combined_results if r.get('metadata', {}).get('search_type') == 'bm25')
        print(f"[HybridSearch] Result composition: {hybrid_count} hybrid, {rag_only_count} RAG-only, {bm25_only_count} BM25-only")
        
        # Log combined chunk details
        print(f"[HybridSearch] Combined {len(combined_results)} results:")
        for i, result in enumerate(combined_results, 1):
            metadata = result.get('metadata', {})
            source = metadata.get('source', 'Unknown')
            content_type = metadata.get('content_type', 'Unknown')
            search_type = metadata.get('search_type', 'Unknown')
            hybrid_score = metadata.get('hybrid_score', 0)
            rag_score = metadata.get('rag_score', 0)
            bm25_score = metadata.get('bm25_score', 0)
            code = metadata.get('code', 'Unknown')
            title = metadata.get('title', 'Unknown')
            chunk_content = result.get('page_content', result.get('content', ''))
            chunk_preview = chunk_content[:150].replace('\n', ' ') if chunk_content else 'No content'
            
            print(f"[HybridSearch] Result {i} ({search_type}): {code} - {title}")
            print(f"[HybridSearch]   Scores: Hybrid={hybrid_score:.2f} (RAG={rag_score:.1f} + BM25={bm25_score:.1f})")
            print(f"[HybridSearch]   Source: {source} ({content_type})")
            print(f"[HybridSearch]   Content: {chunk_preview}...")
            print(f"[HybridSearch]   ---")
        
        return combined_results
    
    def update_bm25_index(self, vector_store):
        """Update the BM25 index when vector store changes"""
        self.bm25_searcher.update_index(vector_store)