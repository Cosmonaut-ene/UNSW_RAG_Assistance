# rag/bm25_search.py
"""
BM25 Search Engine - Replaces keyword search with proper BM25 scoring on vector chunks
"""

import re
from typing import List, Dict, Optional
from langchain.docstore.document import Document

# Try to import BM25 and NLTK dependencies
try:
    import nltk
    from rank_bm25 import BM25Okapi
    from nltk.tokenize import word_tokenize
    from nltk.corpus import stopwords
    
    # Download required NLTK data if not already present
    try:
        # Try new punkt_tab first, fall back to punkt
        try:
            nltk.data.find('tokenizers/punkt_tab')
        except LookupError:
            try:
                nltk.data.find('tokenizers/punkt')
            except LookupError:
                print("[BM25Search] Downloading NLTK tokenizer data...")
                nltk.download('punkt_tab', quiet=True)
                nltk.download('punkt', quiet=True)  # Fallback for older versions
        
        nltk.data.find('corpora/stopwords')
    except LookupError:
        print("[BM25Search] Downloading NLTK stopwords data...")
        nltk.download('stopwords', quiet=True)
    
    BM25_AVAILABLE = True
    print("[BM25Search] BM25 and NLTK dependencies loaded successfully")
    
except ImportError as e:
    print(f"[BM25Search] Warning: BM25 dependencies not available: {e}")
    print("[BM25Search] Install with: pip install rank-bm25 nltk")
    BM25_AVAILABLE = False
    
    # Fallback implementations
    class BM25Okapi:
        def __init__(self, *args, **kwargs):
            pass
        def get_scores(self, query):
            return []
    
    def word_tokenize(text):
        return text.lower().split()
    
    def stopwords():
        return set(['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'])

class BM25SearchEngine:
    """
    BM25-based search engine that operates on the same chunked documents as RAG
    """
    
    def __init__(self, vector_store=None):
        """
        Initialize BM25 search engine
        
        Args:
            vector_store: Vector store containing chunked documents
        """
        self.vector_store = vector_store
        self.corpus = []           # All chunk texts
        self.chunk_metadata = []   # Corresponding metadata
        self.documents = []        # Original Document objects
        self.bm25 = None
        self.bm25_available = BM25_AVAILABLE
        
        if BM25_AVAILABLE:
            self.stop_words = set(stopwords.words('english'))
        else:
            self.stop_words = stopwords()  # Use fallback
        
        if vector_store:
            self._build_bm25_index()
    
    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text for BM25 processing
        
        Args:
            text: Input text to tokenize
            
        Returns:
            List of tokens
        """
        if not text:
            return []
        
        # Convert to lowercase and tokenize
        tokens = word_tokenize(text.lower())
        
        # Filter out stopwords and non-alphabetic tokens, but keep academic codes
        filtered_tokens = []
        for token in tokens:
            # Keep academic codes (COMP9900, 8543, etc.)
            if re.match(r'^[A-Z]{4}\d{4}$', token.upper()) or re.match(r'^\d{4}$', token):
                filtered_tokens.append(token.upper())
            # Keep meaningful words (not stopwords, not punctuation)
            elif token.isalpha() and len(token) > 2 and token not in self.stop_words:
                filtered_tokens.append(token)
            # Keep numbers that might be important
            elif token.isdigit() and len(token) >= 2:
                filtered_tokens.append(token)
        
        return filtered_tokens
    
    def _build_bm25_index(self):
        """
        Build BM25 index from vector store documents
        """
        if not self.bm25_available:
            print("[BM25Search] BM25 dependencies not available, skipping index build")
            return
            
        if not self.vector_store:
            print("[BM25Search] Warning: No vector store provided")
            return
        
        try:
            # Get all documents from vector store
            all_chunks = self._get_all_documents_from_vector_store()
            
            if not all_chunks:
                print("[BM25Search] Warning: No documents found in vector store")
                return
            
            self.documents = all_chunks
            self.corpus = [doc.page_content for doc in all_chunks]
            self.chunk_metadata = [doc.metadata for doc in all_chunks]
            
            # Tokenize corpus for BM25
            print(f"[BM25Search] Tokenizing {len(self.corpus)} documents...")
            tokenized_corpus = [self._tokenize(doc) for doc in self.corpus]
            
            # Build BM25 index
            self.bm25 = BM25Okapi(tokenized_corpus)
            print(f"[BM25Search] Built BM25 index with {len(self.corpus)} documents")
            
        except Exception as e:
            print(f"[BM25Search] Error building BM25 index: {e}")
            print("[BM25Search] If this is an NLTK data error, BM25 will gracefully degrade to RAG-only search")
            self.bm25 = None
            self.bm25_available = False  # Disable BM25 for this session
    
    def _get_all_documents_from_vector_store(self) -> List[Document]:
        """
        Extract all documents from the vector store
        
        Returns:
            List of Document objects
        """
        try:
            # ChromaDB approach - get all documents
            if hasattr(self.vector_store, '_collection'):
                # Get all document IDs and retrieve documents
                results = self.vector_store._collection.get()
                
                documents = []
                for i in range(len(results['documents'])):
                    doc = Document(
                        page_content=results['documents'][i],
                        metadata=results['metadatas'][i] if results['metadatas'] else {}
                    )
                    documents.append(doc)
                
                return documents
            
            # Fallback: if vector store has a get_all method
            elif hasattr(self.vector_store, 'get_all'):
                return self.vector_store.get_all()
            
            # Another fallback: try similarity search with empty query
            elif hasattr(self.vector_store, 'similarity_search'):
                # This might not get ALL documents, but it's better than nothing
                return self.vector_store.similarity_search("", k=1000)
            
            else:
                print("[BM25Search] Unable to extract documents from vector store")
                return []
                
        except Exception as e:
            print(f"[BM25Search] Error extracting documents from vector store: {e}")
            return []
    
    def update_index(self, vector_store=None):
        """
        Update BM25 index with new vector store data
        
        Args:
            vector_store: New vector store to index
        """
        if vector_store:
            self.vector_store = vector_store
        
        self._build_bm25_index()
    
    def search(self, query: str, top_k: int = 20, min_score: float = 0.0) -> List[Dict]:
        """
        Search using BM25 algorithm
        
        Args:
            query: Search query string
            top_k: Maximum number of results to return
            min_score: Minimum BM25 score threshold
            
        Returns:
            List of search results with content, metadata, and scores
        """
        if not self.bm25_available:
            print("[BM25Search] BM25 dependencies not available, returning empty results")
            return []
            
        if not self.bm25 or not self.corpus:
            print("[BM25Search] BM25 index not available")
            return []
        
        try:
            # Tokenize query
            tokenized_query = self._tokenize(query)
            
            if not tokenized_query:
                print("[BM25Search] No valid tokens in query")
                return []
            
            # Get BM25 scores
            scores = self.bm25.get_scores(tokenized_query)
            
            # Get top results
            top_indices = scores.argsort()[-top_k:][::-1]
            
            results = []
            for idx in top_indices:
                score = scores[idx]
                if score > min_score:  # Filter by minimum score
                    result = {
                        'content': self.corpus[idx],
                        'metadata': self.chunk_metadata[idx],
                        'document': self.documents[idx],
                        'bm25_score': float(score),
                        'index': int(idx)
                    }
                    results.append(result)
            
            print(f"[BM25Search] Found {len(results)} results for query: '{query}'")
            
            # Log detailed BM25 results
            for i, result in enumerate(results, 1):
                metadata = result['metadata']
                source = metadata.get('source', 'Unknown')
                content_type = metadata.get('content_type', 'Unknown') 
                code = metadata.get('code', 'Unknown')
                title = metadata.get('title', 'Unknown')
                score = result['bm25_score']
                content_preview = result['content'][:200].replace('\n', ' ') if result['content'] else 'No content'
                
                print(f"[BM25Search] Result {i} (BM25={score:.4f}): {code} - {title}")
                print(f"[BM25Search]   Source: {source} ({content_type})")
                print(f"[BM25Search]   Content: {content_preview}...")
                print(f"[BM25Search]   ---")
            return results
            
        except Exception as e:
            print(f"[BM25Search] Error during search: {e}")
            return []
    
    def search_with_filters(self, query: str, content_type: Optional[str] = None, 
                          course_code: Optional[str] = None, top_k: int = 20) -> List[Dict]:
        """
        Search with metadata filters
        
        Args:
            query: Search query string
            content_type: Filter by content type (e.g., 'scraped_web')
            course_code: Filter by course/program code
            top_k: Maximum results to return
            
        Returns:
            List of filtered search results
        """
        # Get all results first
        all_results = self.search(query, top_k=top_k * 2)  # Get more to account for filtering
        
        # Apply filters
        filtered_results = []
        for result in all_results:
            metadata = result['metadata']
            
            # Content type filter
            if content_type and metadata.get('content_type') != content_type:
                continue
            
            # Course code filter
            if course_code and metadata.get('code') != course_code:
                continue
            
            filtered_results.append(result)
            
            # Stop when we have enough results
            if len(filtered_results) >= top_k:
                break
        
        return filtered_results
    
    def get_stats(self) -> Dict:
        """
        Get search engine statistics
        
        Returns:
            Dictionary with index statistics
        """
        return {
            'total_documents': len(self.corpus) if self.corpus else 0,
            'index_available': self.bm25 is not None,
            'avg_document_length': sum(len(doc.split()) for doc in self.corpus) / len(self.corpus) if self.corpus else 0
        }