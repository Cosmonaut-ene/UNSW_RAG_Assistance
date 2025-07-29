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
        
    if metadata.get('content_type'):
        header_parts.append(f"**Type:** {metadata['content_type']}")
        
    if metadata.get('source'):
        header_parts.append(f"**Source:** {metadata['source']}")
    
    if header_parts:
        return "**Context Information:**\n" + "\n".join(header_parts)
    else:
        return ""

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
    
    # Process scraped documents with H2 header splitting (new logic)
    if scraped_docs:
        scraped_chunks = split_scraped_documents_by_headers(scraped_docs)
        scraped_chunk_count = len([c for c in scraped_chunks if c.metadata.get('content_type') == 'scraped_web'])
        all_chunks.extend(scraped_chunks)
        print(f"[TextSplitter] Processed {len(scraped_docs)} scraped documents into {scraped_chunk_count} chunks")
    
    # Keep other documents as-is
    if other_docs:
        all_chunks.extend(other_docs)
        print(f"[TextSplitter] Kept {len(other_docs)} other documents unchanged")
    
    print(f"[TextSplitter] Total chunks created: {len(all_chunks)}")
    return all_chunks