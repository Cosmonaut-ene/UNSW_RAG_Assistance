# Hybrid Search Engine

## Overview

The Hybrid Search Engine combines semantic similarity search (RAG) with keyword-based text matching to provide comprehensive and relevant search results. This module implements intelligent result filtering and score-based ranking to ensure high-quality responses.

## Features

- **Dual Search Strategy**: Combines RAG (Retrieval-Augmented Generation) with keyword search
- **Configurable Thresholds**: Filter low-quality results using customizable score thresholds
- **Intelligent Score Weighting**: Balanced scoring system (60% RAG, 40% keyword)
- **Result Deduplication**: Prevents duplicate results from different search methods
- **Quality Filtering**: OR-based threshold logic allows strong results from either method

## Core Components

### HybridSearchEngine Class

The main class that orchestrates hybrid search operations.

#### Constructor Parameters

```python
HybridSearchEngine(
    content_dir: str,                    # Directory containing searchable content
    min_hybrid_score: float = 70.0,      # Minimum combined score threshold
    min_keyword_score: float = 10.0,     # Minimum keyword match score
    min_rag_score: float = 50.0          # Minimum semantic similarity score
)
```

#### Key Methods

- **`combine_results()`**: Merges and scores results from both search methods
- **`search_hybrid()`**: Executes the complete hybrid search pipeline

## Scoring System

### Score Calculation

```
hybrid_score = (rag_score × 0.6) + (keyword_score × 0.4)
```

### Threshold Logic

Results pass filtering if they meet **any** of these conditions:
- `hybrid_score >= min_hybrid_score` (default: 70.0)
- `rag_score >= min_rag_score` (default: 50.0) 
- `keyword_score >= min_keyword_score` (default: 10.0)

This OR-based logic ensures that:
- Strong semantic matches aren't filtered by weak keyword scores
- Strong keyword matches aren't filtered by weak semantic scores
- Combined results must meet the hybrid threshold

## Search Metadata

Each result includes comprehensive metadata:

```python
{
    'page_content': str,           # Document content
    'metadata': {
        'source': str,             # Source file/URL
        'search_type': str,        # 'rag', 'keyword', or 'hybrid'
        'rag_score': float,        # Semantic similarity score (0-100)
        'keyword_score': float,    # Keyword matching score (0-∞)
        'hybrid_score': float,     # Combined weighted score
        'matched_terms': list      # Keywords that matched (if applicable)
    }
}
```

## Usage Example

```python
from rag.hybrid_search import HybridSearchEngine

# Initialize with custom thresholds
engine = HybridSearchEngine(
    content_dir="scraped_content/content",
    min_hybrid_score=60.0,
    min_keyword_score=15.0,
    min_rag_score=40.0
)

# Perform hybrid search
rag_results = [...]  # Results from semantic search
results = engine.search_hybrid(
    query="introduce COMP9020",
    rag_results=rag_results,
    max_results=5
)

# Process results
for result in results:
    print(f"Source: {result['metadata']['source']}")
    print(f"Score: {result['metadata']['hybrid_score']:.2f}")
    print(f"Content: {result['page_content'][:100]}...")
```

## Integration

The hybrid search engine integrates with:

- **Keyword Search Module**: Provides text-based matching capabilities
- **RAG System**: Receives semantic similarity results
- **Query Processor**: Main application pipeline integration

## Logging

The module provides detailed logging for debugging and monitoring:

- Result acceptance/rejection with scores
- Threshold filtering statistics
- Source file matching information
- Performance metrics

## Performance Considerations

- **Caching**: Uses singleton pattern for engine instance
- **Deduplication**: Prevents processing duplicate sources
- **Early Filtering**: Applies thresholds before expensive operations
- **Configurable Limits**: Customizable result count limits

## Error Handling

- Graceful handling of missing metadata
- Default score assignment for incomplete results
- Robust source file extraction
- Safe string operations for content processing