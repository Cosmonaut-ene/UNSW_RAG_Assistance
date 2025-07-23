# Keyword Search Module

## Overview

The Keyword Search Module provides intelligent text-based search capabilities with specialized course code detection and flexible matching algorithms. It's designed specifically for academic content with support for UNSW course codes, program codes, and general keyword matching.

## Features

- **Smart Course Code Detection**: Recognizes and matches course codes like COMP9020
- **Bidirectional Matching**: "9020" ↔ "COMP9020" intelligent cross-referencing
- **Program Code Support**: Direct matching for 4-digit program codes
- **Weighted Scoring**: Different scores for different match types
- **Phrase Matching**: Multi-word phrase detection and scoring
- **JSON Content Processing**: Optimized for scraped web content

## Core Components

### SimpleKeywordSearch Class

The main search engine that processes JSON documents and performs keyword matching.

#### Constructor Parameters

```python
SimpleKeywordSearch(content_dir: str)
```

- `content_dir`: Directory containing JSON files with scraped content

## Scoring System

### Match Types and Scores

| Match Type | Score | Description |
|------------|-------|-------------|
| **Course Code** (COMP9020) | 100 | Exact course code match |
| **Program Code** (4-digit) | 100 | Direct 4-digit number match |
| **Smart Course Match** | 90 | "9020" → "COMP9020" mapping |
| **Reverse Course Match** | 90 | "COMP9020" → "9020" mapping |
| **Phrase Match** | 30 | Multi-word exact phrase |
| **Keyword Match** | 5 per occurrence | Individual word (max 25 per term) |

### Intelligent Course Code Matching

The module implements sophisticated course code detection:

1. **Direct Course Code**: `COMP9020` in query matches `comp9020` in content
2. **Number to Course**: `9020` in query finds `comp9020` in content  
3. **Course to Number**: `comp9020` in content matches `9020` in query
4. **Case Insensitive**: All matching is case-insensitive

## Search Algorithm

### 1. Text Preprocessing
- Convert content to lowercase for matching
- Extract searchable text from JSON structure
- Preserve original formatting for display

### 2. Pattern Detection
```python
# Course codes (e.g., COMP9020, ACTL5105)
course_codes = re.findall(r'\b[A-Z]{4}\d{4}\b', query.upper())

# Program codes (e.g., 9020, 5546)  
program_codes = re.findall(r'\b\d{4}\b', query)

# Document course codes
doc_course_codes = re.findall(r'\bcomp\d{4}\b', searchable_text)
```

### 3. Score Calculation
- Each match type contributes to the total score
- Multiple occurrences increase score (with limits)
- Final score determines result relevance

## JSON Document Structure

Expected JSON format for content files:

```json
{
    "page_content": "Course content with COMP9020 information...",
    "metadata": {
        "source": "https://handbook.unsw.edu.au/...",
        "title": "Course Title",
        "content_type": "scraped_web"
    }
}
```

## Usage Example

```python
from rag.keyword_search import SimpleKeywordSearch

# Initialize search engine
searcher = SimpleKeywordSearch("scraped_content/content")

# Perform search
results = searcher.search_keywords("introduce 9020", max_results=5)

# Process results
for result in results:
    metadata = result['metadata']
    print(f"Source: {metadata['source']}")
    print(f"Score: {metadata['keyword_score']}")
    print(f"Matched: {metadata['matched_terms']}")
    print(f"Content: {result['page_content'][:200]}...")
```

## Search Result Format

Each result includes:

```python
{
    'page_content': str,           # Full document content
    'metadata': {
        'source': str,             # Original source URL/file
        'keyword_score': int,      # Total keyword match score
        'matched_terms': list,     # List of matched terms with types
        'search_type': 'keyword'   # Search method identifier
    }
}
```

## Advanced Features

### Term Frequency Limiting
- Individual keywords limited to 25 points maximum
- Prevents single high-frequency terms from dominating scores
- Encourages diverse content matching

### Query Term Filtering
- Ignores terms with less than 3 characters
- Focuses on meaningful keywords
- Reduces noise from common words

### Flexible Content Extraction
The `_extract_searchable_text()` method handles various JSON structures:
- Direct string content
- Nested metadata fields
- Mixed content types
- Robust error handling

## Integration Points

### With Hybrid Search
- Provides keyword_score for hybrid scoring
- Supplies matched_terms for debugging
- Integrates seamlessly with RAG results

### With Query Processor
- Called through hybrid search pipeline
- Results formatted for consistent processing
- Error handling for invalid inputs

## Performance Optimizations

- **Regex Compilation**: Efficient pattern matching
- **String Operations**: Optimized case-insensitive search
- **Memory Management**: Processes documents incrementally
- **Early Termination**: Skips empty or invalid documents

## Error Handling

- **File Loading**: Graceful handling of missing/corrupt files
- **JSON Parsing**: Robust error recovery
- **Empty Queries**: Safe handling of blank inputs
- **Content Validation**: Checks for required fields

## Debugging Features

- **Match Term Tracking**: Records what terms matched
- **Score Breakdown**: Detailed scoring information
- **Source Attribution**: Links results to original files
- **Verbose Logging**: Optional detailed output

This module is essential for finding academic content that might not be captured by semantic search alone, especially when users search using course codes or specific program numbers.