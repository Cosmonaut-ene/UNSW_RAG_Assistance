"""
Mock implementations for ChromaDB Vector Store operations
"""

from unittest.mock import MagicMock
from typing import Dict, List, Any, Optional
import uuid
import numpy as np
from langchain.docstore.document import Document


class MockChromaCollection:
    """Mock ChromaDB Collection"""
    
    def __init__(self, name: str = "test_collection"):
        self.name = name
        self._documents = {}
        self._embeddings = {}
        self._metadata = {}
        self.call_count = 0
        
    def add(self, documents: List[str], embeddings: List[List[float]] = None, 
            metadatas: List[Dict] = None, ids: List[str] = None):
        """Mock document addition"""
        self.call_count += 1
        
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in documents]
        if embeddings is None:
            embeddings = [[0.1] * 768 for _ in documents]
        if metadatas is None:
            metadatas = [{}] * len(documents)
            
        for i, doc_id in enumerate(ids):
            self._documents[doc_id] = documents[i]
            self._embeddings[doc_id] = embeddings[i]
            self._metadata[doc_id] = metadatas[i]
            
    def query(self, query_embeddings: List[List[float]] = None, 
              query_texts: List[str] = None, n_results: int = 5,
              where: Dict = None, **kwargs) -> Dict:
        """Mock query operation"""
        self.call_count += 1
        
        # Return mock results based on stored documents
        doc_ids = list(self._documents.keys())[:n_results]
        
        results = {
            "ids": [doc_ids],
            "distances": [[0.1 + i * 0.1 for i in range(len(doc_ids))]],
            "documents": [[self._documents[doc_id] for doc_id in doc_ids]],
            "metadatas": [[self._metadata[doc_id] for doc_id in doc_ids]]
        }
        
        # Filter by metadata if specified
        if where:
            filtered_results = {"ids": [[]], "distances": [[]], "documents": [[]], "metadatas": [[]]}
            for i, doc_id in enumerate(doc_ids):
                metadata = self._metadata[doc_id]
                if self._matches_where_clause(metadata, where):
                    filtered_results["ids"][0].append(doc_id)
                    filtered_results["distances"][0].append(results["distances"][0][i])
                    filtered_results["documents"][0].append(results["documents"][0][i])
                    filtered_results["metadatas"][0].append(results["metadatas"][0][i])
            results = filtered_results
            
        return results
        
    def count(self) -> int:
        """Mock document count"""
        return len(self._documents)
        
    def delete(self, ids: List[str] = None, where: Dict = None):
        """Mock document deletion"""
        self.call_count += 1
        if ids:
            for doc_id in ids:
                self._documents.pop(doc_id, None)
                self._embeddings.pop(doc_id, None)
                self._metadata.pop(doc_id, None)
                
    def update(self, ids: List[str], documents: List[str] = None, 
               embeddings: List[List[float]] = None, metadatas: List[Dict] = None):
        """Mock document update"""
        self.call_count += 1
        for i, doc_id in enumerate(ids):
            if documents:
                self._documents[doc_id] = documents[i]
            if embeddings:
                self._embeddings[doc_id] = embeddings[i]
            if metadatas:
                self._metadata[doc_id] = metadatas[i]
                
    def get(self, ids: List[str] = None, where: Dict = None, limit: int = None) -> Dict:
        """Mock document retrieval"""
        self.call_count += 1
        
        if ids:
            doc_ids = [doc_id for doc_id in ids if doc_id in self._documents]
        else:
            doc_ids = list(self._documents.keys())
            
        if limit:
            doc_ids = doc_ids[:limit]
            
        return {
            "ids": doc_ids,
            "documents": [self._documents[doc_id] for doc_id in doc_ids],
            "metadatas": [self._metadata[doc_id] for doc_id in doc_ids],
            "embeddings": [self._embeddings[doc_id] for doc_id in doc_ids]
        }
        
    def _matches_where_clause(self, metadata: Dict, where: Dict) -> bool:
        """Check if metadata matches where clause"""
        for key, value in where.items():
            if key not in metadata or metadata[key] != value:
                return False
        return True


class MockChromaClient:
    """Mock ChromaDB Client"""
    
    def __init__(self):
        self._collections = {}
        self.call_count = 0
        
    def create_collection(self, name: str, **kwargs) -> MockChromaCollection:
        """Mock collection creation"""
        self.call_count += 1
        collection = MockChromaCollection(name)
        self._collections[name] = collection
        return collection
        
    def get_collection(self, name: str) -> MockChromaCollection:
        """Mock collection retrieval"""
        self.call_count += 1
        if name not in self._collections:
            # Auto-create collection if it doesn't exist
            self._collections[name] = MockChromaCollection(name)
        return self._collections[name]
        
    def get_or_create_collection(self, name: str, **kwargs) -> MockChromaCollection:
        """Mock get or create collection"""
        self.call_count += 1
        return self.get_collection(name)
        
    def list_collections(self) -> List[Any]:
        """Mock collection listing"""
        self.call_count += 1
        return [MagicMock(name=name) for name in self._collections.keys()]
        
    def delete_collection(self, name: str):
        """Mock collection deletion"""
        self.call_count += 1
        self._collections.pop(name, None)


class MockVectorStore:
    """Mock Vector Store with sample data"""
    
    def __init__(self):
        self.client = MockChromaClient()
        self.collection = self.client.create_collection("test_collection")
        self._collection = self.collection  # Add alias for BM25SearchEngine compatibility
        self._setup_sample_data()
        
    def _setup_sample_data(self):
        """Setup sample documents for testing"""
        sample_documents = [
            "COMP9900 is a capstone project course in computer science at UNSW.",
            "The Computer Science building is located at J17 on the UNSW campus.",
            "Prerequisites for COMP9900 include completion of COMP2511 and other core courses.",
            "UNSW offers various undergraduate and postgraduate programs in computer science.",
            "The campus has multiple study spaces including the library and student lounges."
        ]
        
        sample_metadata = [
            {"source": "handbook.pdf", "page": 1, "course_code": "COMP9900", "content_type": "course_description"},
            {"source": "campus_guide.pdf", "page": 5, "building": "J17", "content_type": "location_info"},
            {"source": "handbook.pdf", "page": 2, "course_code": "COMP9900", "content_type": "prerequisites"},
            {"source": "programs.pdf", "page": 1, "content_type": "program_info"},
            {"source": "campus_guide.pdf", "page": 8, "content_type": "facilities"}
        ]
        
        sample_ids = [f"doc_{i}" for i in range(len(sample_documents))]
        
        self.collection.add(
            documents=sample_documents,
            metadatas=sample_metadata,
            ids=sample_ids
        )
        
    def similarity_search(self, query: str, k: int = 5) -> List[Document]:
        """Mock similarity search"""
        results = self.collection.query(query_texts=[query], n_results=k)
        
        documents = []
        for i in range(len(results["documents"][0])):
            doc = Document(
                page_content=results["documents"][0][i],
                metadata=results["metadatas"][0][i]
            )
            documents.append(doc)
            
        return documents
        
    def add_documents(self, documents: List[Document]):
        """Mock document addition"""
        texts = [doc.page_content for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        ids = [str(uuid.uuid4()) for _ in documents]
        
        self.collection.add(documents=texts, metadatas=metadatas, ids=ids)
        
    def delete(self, ids: List[str]):
        """Mock document deletion"""
        self.collection.delete(ids=ids)


def create_mock_vector_store_with_data(documents: List[Document] = None) -> MockVectorStore:
    """Create a mock vector store with optional custom data"""
    mock_store = MockVectorStore()
    
    if documents:
        mock_store.add_documents(documents)
        
    return mock_store