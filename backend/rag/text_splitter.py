# rag/text_splitter.py
"""
Text Splitter - Handles document chunking with different strategies for PDF and JSON content
"""

import re
import spacy
from typing import List, Dict
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Load English spaCy model for PDF processing
try:
    nlp = spacy.load("en_core_web_sm")
    SPACY_AVAILABLE = True
except OSError:
    print("[TextSplitter] Warning: spaCy model 'en_core_web_sm' not found. PDF chunking will use fallback method.")
    SPACY_AVAILABLE = False

# Enhanced chunking configuration
CHUNK_CONFIG = {
    # Merging parameters (for small sections)
    'target_chunk_size': 600,           # Target for merged chunks
    'min_chunk_size': 200,              # Minimum before forcing merge (realistic for varied content)
    'merge_threshold': 1200,            # Merge sections smaller than this
    
    # Large section handling
    'large_section_threshold': 1200,    # Sections larger than this stay intact
    'max_standalone_size': 4000,        # Absolute maximum for any single chunk
    
    # Section count limits
    'min_sections_per_chunk': 2,        # At least 2 H2 sections per merged chunk
    'max_sections_per_chunk': 8,        # Allow more merging for very short sections
    
    # Context
    'context_header_size': 100          # Reserve space for context header
}

def create_context_header(metadata: Dict) -> str:
    """
    Create context header with key information for scraped content chunks
    
    Args:
        metadata: Document metadata dictionary
        
    Returns:
        str: Formatted context header
    """
    header_parts = []
    
    # Core identification information
    if metadata.get('code'):
        header_parts.append(f"**Program/Course Code:** {metadata['code']}")
    
    if metadata.get('title'):
        header_parts.append(f"**Title:** {metadata['title']}")
        
    if metadata.get('type'):
        header_parts.append(f"**Type:** {metadata['type']}")
        
    if metadata.get('source'):
        header_parts.append(f"**Source:** {metadata['source']}")
    
    if header_parts:
        return "**Context Information:**\n" + "\n".join(header_parts)
    else:
        return ""

def create_optimized_context(metadata: Dict) -> str:
    """
    Create minimal context header optimized for chunk density
    
    Args:
        metadata: Document metadata dictionary
        
    Returns:
        str: Compact context header with source URL
    """
    parts = []
    
    # Essential identification only
    if metadata.get('code') and metadata.get('title'):
        parts.append(f"**{metadata['code']} - {metadata['title']}**")
    elif metadata.get('code'):
        parts.append(f"**Code:** {metadata['code']}")
    elif metadata.get('title'):
        parts.append(f"**Title:** {metadata['title']}")
    
    if metadata.get('content_type'):
        parts.append(f"**Type:** {metadata['content_type']}")
    
    # Add source URL if available
    if metadata.get('source') and metadata['source'].startswith('https://www.handbook.unsw.edu.au'):
        parts.append(f"**Source:** {metadata['source']}")
    
    return "\n".join(parts) if parts else ""

def split_by_h2_headers(content: str) -> List[str]:
    """
    Split markdown content by level 2 headers (##)
    
    Args:
        content: Markdown content string
        
    Returns:
        List of content sections
    """
    # Split by ## headers, keeping the header with the content
    sections = re.split(r'\n(?=##\s)', content)
    
    # Clean up sections and filter out empty ones
    cleaned_sections = []
    for section in sections:
        section = section.strip()
        if section and len(section) > 10:  # Ignore very short sections
            cleaned_sections.append(section)
    
    return cleaned_sections

def split_pdf_documents_spacy(documents: List[Document], sentences_per_chunk: int = 3) -> List[Document]:
    """
    Split PDF documents using spaCy for semantic chunking (preserves existing logic)
    
    Args:
        documents: List of PDF documents
        sentences_per_chunk: Number of sentences per chunk
        
    Returns:
        List of chunked documents
    """
    if not SPACY_AVAILABLE:
        # Fallback to simple text splitting
        return split_documents_simple(documents)
    
    new_chunks = []
    for doc in documents:
        if doc.metadata.get('content_type') != 'pdf':
            new_chunks.append(doc)  # Skip non-PDF documents
            continue
            
        try:
            spacy_doc = nlp(doc.page_content)
            sentences = [sent.text.strip() for sent in spacy_doc.sents if sent.text.strip()]
            metadata = doc.metadata

            for i in range(0, len(sentences), sentences_per_chunk):
                chunk_text = " ".join(sentences[i:i + sentences_per_chunk])
                if chunk_text:
                    new_chunks.append(Document(page_content=chunk_text, metadata=metadata))
                    
        except Exception as e:
            print(f"[TextSplitter] SpaCy processing error for PDF: {e}")
            # Fallback to simple splitting for this document
            simple_chunks = split_documents_simple([doc])
            new_chunks.extend(simple_chunks)
    
    print(f"[TextSplitter] Created {len(new_chunks)} PDF chunks using spaCy")
    return new_chunks

def split_scraped_documents_by_headers(documents: List[Document]) -> List[Document]:
    """
    Split scraped JSON documents by ## headers with context preservation
    
    Args:
        documents: List of scraped documents
        
    Returns:
        List of chunked documents with context headers
    """
    chunks = []
    
    for doc in documents:
        if doc.metadata.get('content_type') != 'scraped_web':
            chunks.append(doc)  # Skip non-scraped content
            continue
        
        try:
            # Create context header with key metadata
            header = create_context_header(doc.metadata)
            
            # Split content by ## headers
            sections = split_by_h2_headers(doc.page_content)
            
            if not sections:
                # If no ## headers found, keep the whole document
                chunks.append(doc)
                continue
            
            # Create chunks for each section
            for i, section in enumerate(sections):
                if section.strip():
                    # Combine header + section content
                    if header:
                        chunk_content = f"{header}\n\n{section}"
                    else:
                        chunk_content = section
                    
                    # Create new chunk with enhanced metadata
                    chunk_metadata = doc.metadata.copy()
                    chunk_metadata.update({
                        'chunk_type': 'h2_section',
                        'chunk_index': i,
                        'total_chunks': len(sections),
                        'has_context_header': bool(header),
                        'section_title': extract_section_title(section)
                    })
                    
                    chunk = Document(
                        page_content=chunk_content,
                        metadata=chunk_metadata
                    )
                    chunks.append(chunk)
                    
        except Exception as e:
            print(f"[TextSplitter] Error processing scraped document: {e}")
            # Keep original document if processing fails
            chunks.append(doc)
    
    scraped_chunks = [c for c in chunks if c.metadata.get('content_type') == 'scraped_web']
    print(f"[TextSplitter] Created {len(scraped_chunks)} scraped content chunks using H2 headers")
    return chunks

def merge_h2_sections(sections: List[str]) -> str:
    """
    Merge multiple H2 sections into a single chunk
    
    Args:
        sections: List of H2 sections to merge
        
    Returns:
        str: Combined section content
    """
    if not sections:
        return ""
    
    # Join sections with double newline separator
    return "\n\n".join(section.strip() for section in sections if section.strip())

def process_h2_sections_with_merging(sections: List[str]) -> List[str]:
    """
    Process H2 sections using smart merging strategy
    
    Args:
        sections: List of individual H2 sections
        
    Returns:
        List of optimized chunks (merged small sections, standalone large sections)
    """
    if not sections:
        return []
    
    chunks = []
    current_merge_group = []
    current_merge_size = 0
    
    for section in sections:
        section = section.strip()
        if not section:
            continue
            
        section_size = len(section)
        
        # Special Case: Overview section - always standalone
        if section.startswith('## Overview'):
            # First, finish any pending merge group
            if current_merge_group:
                merged_chunk = merge_h2_sections(current_merge_group)
                if merged_chunk:
                    chunks.append(merged_chunk)
                current_merge_group = []
                current_merge_size = 0
            
            # Add Overview section as standalone
            print(f"[TextSplitter] Found Overview section, creating standalone chunk (size: {section_size})")
            chunks.append(section)
            continue
        
        # Case 1: Large section - keep as standalone chunk
        if section_size >= CHUNK_CONFIG['large_section_threshold']:
            # First, finish any pending merge group
            if current_merge_group:
                merged_chunk = merge_h2_sections(current_merge_group)
                if merged_chunk:
                    chunks.append(merged_chunk)
                current_merge_group = []
                current_merge_size = 0
            
            # Add large section as standalone
            chunks.append(section)
            
        # Case 2: Small section - add to merge group
        else:
            # Check if adding this section would exceed target or max sections
            would_exceed_size = (current_merge_size + section_size > CHUNK_CONFIG['target_chunk_size'])
            would_exceed_count = (len(current_merge_group) >= CHUNK_CONFIG['max_sections_per_chunk'])
            
            # Only split if we have enough content for a valid chunk AND would exceed limits
            current_would_be_valid = (current_merge_size >= CHUNK_CONFIG['min_chunk_size'])
            
            if (would_exceed_size or would_exceed_count) and current_merge_group and current_would_be_valid:
                # Finish current group and start new one
                merged_chunk = merge_h2_sections(current_merge_group)
                if merged_chunk:
                    chunks.append(merged_chunk)
                current_merge_group = [section]
                current_merge_size = section_size
            else:
                # Add to current group
                current_merge_group.append(section)
                current_merge_size += section_size
    
    # Handle remaining merge group
    if current_merge_group:
        merged_chunk = merge_h2_sections(current_merge_group)
        if merged_chunk:
            chunks.append(merged_chunk)
    
    return chunks

def validate_chunk_quality(chunk: str) -> bool:
    """
    Validate if a chunk meets quality requirements
    
    Args:
        chunk: Text chunk to validate
        
    Returns:
        bool: True if chunk meets quality standards
    """
    if not chunk or not chunk.strip():
        return False
    
    chunk_size = len(chunk.strip())
    
    # Must be at least minimum size
    if chunk_size < CHUNK_CONFIG['min_chunk_size']:
        return False
    
    # Should not exceed maximum size (unless it's a single large H2 section)
    if chunk_size > CHUNK_CONFIG['max_standalone_size']:
        return False
    
    return True

def extract_section_title(section: str) -> str:
    """
    Extract the title from a section (first ## header)
    
    Args:
        section: Content section string
        
    Returns:
        str: Section title or empty string
    """
    lines = section.split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith('##'):
            # Remove ## and clean the title
            title = line[2:].strip()
            return title
    return ""

def split_documents_simple(documents: List[Document], chunk_size: int = 500, chunk_overlap: int = 50) -> List[Document]:
    """
    Simple text splitting fallback method
    
    Args:
        documents: Documents to split
        chunk_size: Maximum chunk size
        chunk_overlap: Overlap between chunks
        
    Returns:
        List of chunked documents
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, 
        chunk_overlap=chunk_overlap
    )
    chunks = splitter.split_documents(documents)
    print(f"[TextSplitter] Created {len(chunks)} chunks using simple text splitting")
    return chunks

def split_scraped_documents_by_merged_headers(documents: List[Document]) -> List[Document]:
    """
    Split scraped JSON documents by ## headers with intelligent merging
    
    Args:
        documents: List of scraped documents
        
    Returns:
        List of optimally chunked documents with merged small sections
    """
    chunks = []
    
    for doc in documents:
        if doc.metadata.get('content_type') != 'scraped_web':
            chunks.append(doc)  # Skip non-scraped content
            continue
        
        try:
            # Split content by ## headers first
            sections = split_by_h2_headers(doc.page_content)
            
            if not sections:
                # If no ## headers found, keep the whole document
                chunks.append(doc)
                continue
            
            # Process sections with intelligent merging
            optimized_chunks = process_h2_sections_with_merging(sections)
            
            if not optimized_chunks:
                # Fallback to original document
                chunks.append(doc)
                continue
            
            # Create document chunks with optimized context headers
            for i, chunk_content in enumerate(optimized_chunks):
                if not validate_chunk_quality(chunk_content):
                    print(f"[TextSplitter] Warning: Chunk {i} failed quality validation")
                    continue
                
                # Create optimized context header
                context_header = create_optimized_context(doc.metadata)
                
                # Combine context + chunk content
                if context_header:
                    final_content = f"{context_header}\n\n{chunk_content}"
                else:
                    final_content = chunk_content
                
                # Extract section titles for metadata
                section_titles = []
                for line in chunk_content.split('\n'):
                    if line.strip().startswith('##'):
                        title = line.strip()[2:].strip()
                        if title:
                            section_titles.append(title)
                
                # Check if this is an Overview chunk
                is_overview_chunk = any('Overview' in title for title in section_titles)
                if is_overview_chunk:
                    print(f"[TextSplitter] Created Overview chunk: {section_titles[0]} (size: {len(chunk_content)})")
                
                # Create enhanced chunk metadata
                chunk_metadata = doc.metadata.copy()
                chunk_metadata.update({
                    'chunk_type': 'merged_h2_sections',
                    'chunk_index': i,
                    'total_chunks': len(optimized_chunks),
                    'has_context_header': bool(context_header),
                    'section_titles': ', '.join(section_titles[:3]),  # Convert list to string
                    'section_count': len(section_titles),
                    'chunk_size': len(chunk_content),
                    'final_size': len(final_content)
                })
                
                chunk = Document(
                    page_content=final_content,
                    metadata=chunk_metadata
                )
                chunks.append(chunk)
                
        except Exception as e:
            print(f"[TextSplitter] Error processing scraped document with merging: {e}")
            # Fallback to original document
            chunks.append(doc)
    
    scraped_chunks = [c for c in chunks if c.metadata.get('content_type') == 'scraped_web']
    print(f"[TextSplitter] Created {len(scraped_chunks)} scraped content chunks using merged H2 headers")
    return chunks

def split_documents_by_content_type(documents: List[Document]) -> List[Document]:
    """
    Split documents using appropriate strategy based on content type
    
    Args:
        documents: Mixed list of PDF and scraped documents
        
    Returns:
        List of appropriately chunked documents
    """
    # Separate documents by type
    pdf_docs = [doc for doc in documents if doc.metadata.get('content_type') == 'pdf']
    scraped_docs = [doc for doc in documents if doc.metadata.get('content_type') == 'scraped_web']
    other_docs = [doc for doc in documents if doc.metadata.get('content_type') not in ['pdf', 'scraped_web']]
    
    all_chunks = []
    
    # Process PDF documents with spaCy (preserve existing logic)
    if pdf_docs:
        pdf_chunks = split_pdf_documents_spacy(pdf_docs)
        all_chunks.extend(pdf_chunks)
        print(f"[TextSplitter] Processed {len(pdf_docs)} PDF documents into {len(pdf_chunks)} chunks")
    
    # Process scraped documents with enhanced H2 header merging (new logic)
    if scraped_docs:
        scraped_chunks = split_scraped_documents_by_merged_headers(scraped_docs)
        scraped_chunk_count = len([c for c in scraped_chunks if c.metadata.get('content_type') == 'scraped_web'])
        all_chunks.extend(scraped_chunks)
        print(f"[TextSplitter] Processed {len(scraped_docs)} scraped documents into {scraped_chunk_count} chunks using merged headers")
    
    # Keep other documents as-is
    if other_docs:
        all_chunks.extend(other_docs)
        print(f"[TextSplitter] Kept {len(other_docs)} other documents unchanged")
    
    print(f"[TextSplitter] Total chunks created: {len(all_chunks)}")
    return all_chunks