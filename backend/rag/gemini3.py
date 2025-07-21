# rag/gemini3.py
import os
import json
import spacy
import google.generativeai as genai
from typing import List, Optional, Dict
from langchain.text_splitter import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
from langchain.docstore.document import Document
from langchain_community.document_loaders import PyMuPDFLoader
from langchain.chains import RetrievalQA
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_chroma import Chroma
from langchain.prompts import PromptTemplate

# ========== Google API keys ==========
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "rag/key.json")
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# ========== Vector Store ==========
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
VECTOR_STORE_DIR = os.path.join(CURRENT_DIR, "vector_store")
KNOWLEDGE_BASE_DIR = os.path.join(CURRENT_DIR, "docs")
SCRAPED_CONTENT_DIR = os.path.join(CURRENT_DIR, "scraped_content")

# ========== Load Documents ==========
def load_documents_from_folder(folder_path):
    """
    Load PDF documents from folder.
    """
    documents = []
    for filename in os.listdir(folder_path):
        if filename.endswith(".pdf"):
            loader = PyMuPDFLoader(os.path.join(folder_path, filename))
            doc_chunks = loader.load()
            # Mark PDF documents with content_type
            for doc in doc_chunks:
                doc.metadata["content_type"] = "pdf"
            print(f"[Gemini3] Loaded {len(doc_chunks)} pages from {filename}")
            documents.extend(doc_chunks)
    return documents




def load_scraped_documents() -> List[Document]:
    """
    Load documents from scraped content directory.
    Returns LangChain Documents from JSON files created by the scrapers module.
    """
    scraped_docs = []
    content_dir = os.path.join(SCRAPED_CONTENT_DIR, "content")
    
    if not os.path.exists(content_dir):
        print("[Gemini3] No scraped content directory found")
        return []
    
    # Load all JSON files from content directory
    json_files = [f for f in os.listdir(content_dir) if f.endswith('.json')]
    
    if not json_files:
        print("[Gemini3] No scraped content files found")
        return []
    
    print(f"[Gemini3] Loading {len(json_files)} scraped documents...")
    
    for filename in json_files:
        filepath = os.path.join(content_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Create Document from scraped data
                document = Document(
                    page_content=data.get("page_content", ""),
                    metadata=data.get("metadata", {})
                )
                
                # Add scraping metadata
                document.metadata["scraped_from_file"] = filename
                document.metadata["content_type"] = "scraped_web"
                
                scraped_docs.append(document)
                
        except Exception as e:
            print(f"[Gemini3] Error loading scraped file {filename}: {e}")
            continue
    
    print(f"[Gemini3] Successfully loaded {len(scraped_docs)} scraped documents")
    return scraped_docs
    
def split_documents(documents, chunk_size=500, chunk_overlap=50):
    """
    Split loaded documents into chunks for vector storage.
    """
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = splitter.split_documents(documents)
    print(f"[Gemini3] Split documents into {len(chunks)} chunks.")
    return chunks

# English spaCy language model for sentence segmentation
nlp = spacy.load("en_core_web_sm")
def split_documents_spacy(documents, sentences_per_chunk=3):
    """
        Split loaded documents using stacy.
    """
    new_chunks = []
    for doc in documents:
        spacy_doc = nlp(doc.page_content)
        sentences = [sent.text.strip() for sent in spacy_doc.sents if sent.text.strip()]
        metadata = doc.metadata

        for i in range(0, len(sentences), sentences_per_chunk):
            chunk_text = " ".join(sentences[i:i + sentences_per_chunk])
            if chunk_text:
                new_chunks.append(Document(page_content=chunk_text, metadata=metadata))
    print(f"[spaCy Chunking] Created {len(new_chunks)} chunks from {len(documents)} documents.")
    return new_chunks

def split_documents_markdown(documents, chunk_size=1000, chunk_overlap=100):
    """
    Split loaded documents using MarkdownHeaderTextSplitter for better structure preservation.
    
    Args:
        documents: List of Document objects with markdown content
        chunk_size: Maximum size of each chunk after header splitting
        chunk_overlap: Overlap between chunks for continuity
    
    Returns:
        List of Document chunks with preserved markdown structure
    """
    # Define headers to split on - matching the structure from page_scraper
    headers_to_split_on = [
        ("#", "Header 1"),      # Main title (e.g., "# Course Title")
        ("##", "Header 2"),     # Major sections (e.g., "## Learning Outcomes", "## Description")
        ("###", "Header 3"),    # Sub-sections if any
    ]
    
    # Create markdown splitter
    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        return_each_line=False,
        strip_headers=False  # Keep headers for context
    )
    
    # Secondary splitter for large sections
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    
    all_chunks = []
    
    for doc in documents:
        try:
            # First split by markdown headers
            header_splits = markdown_splitter.split_text(doc.page_content)
            
            for header_doc in header_splits:
                # Preserve original metadata and add header info
                chunk_metadata = doc.metadata.copy()
                
                # Add header hierarchy information
                if hasattr(header_doc, 'metadata') and header_doc.metadata:
                    chunk_metadata.update(header_doc.metadata)
                
                # If chunk is still too large, split further
                if len(header_doc.page_content) > chunk_size:
                    sub_chunks = text_splitter.split_documents([Document(
                        page_content=header_doc.page_content,
                        metadata=chunk_metadata
                    )])
                    all_chunks.extend(sub_chunks)
                else:
                    all_chunks.append(Document(
                        page_content=header_doc.page_content,
                        metadata=chunk_metadata
                    ))
                    
        except Exception as e:
            print(f"[Markdown Splitting] Error processing document: {e}")
            # Fallback to simple text splitting
            fallback_chunks = text_splitter.split_documents([doc])
            all_chunks.extend(fallback_chunks)
    
    print(f"[Markdown Chunking] Created {len(all_chunks)} chunks from {len(documents)} documents.")
    return all_chunks

# ========== Vector store creation ==========
def create_vector_store(docs):
    """
    Create Chroma vector store from document chunks.
    """
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    db = Chroma.from_documents(docs, embeddings, persist_directory=VECTOR_STORE_DIR)
    # db._collection.persist()
    print("[Gemini3] Created and persisted Chroma vector store.")
    return db

# ========== Update vector store ==========
def _validate_vector_database_exists():
    """
    Check if vector database files exist and are accessible.
    Returns True if database exists and appears valid, False otherwise.
    """
    if not os.path.exists(VECTOR_STORE_DIR):
        print("[Gemini3] Vector store directory does not exist")
        return False
    
    # Look for ChromaDB collection directories
    chroma_dirs = [d for d in os.listdir(VECTOR_STORE_DIR) 
                   if os.path.isdir(os.path.join(VECTOR_STORE_DIR, d)) and 
                   d != "__pycache__" and not d.startswith('.')]
    
    if not chroma_dirs:
        print("[Gemini3] No ChromaDB collection directories found")
        return False
    
    # Check if any collection has essential ChromaDB files
    essential_files = ['header.bin', 'data_level0.bin']
    for chroma_dir in chroma_dirs:
        chroma_path = os.path.join(VECTOR_STORE_DIR, chroma_dir)
        has_essential_files = all(
            os.path.exists(os.path.join(chroma_path, f)) 
            for f in essential_files
        )
        if has_essential_files:
            print(f"[Gemini3] Valid vector database found in {chroma_dir}")
            return True
    
    print("[Gemini3] Vector database files appear to be missing or corrupted")
    return False




def update_vector_store(folder_path, include_scraped=True):
    """
    Check if docs folder or scraped content have changed. If yes, rebuild vector store.
    """
    source_record_file = os.path.join(VECTOR_STORE_DIR, "source_files.txt")
    current_files = sorted([f for f in os.listdir(folder_path) if f.endswith(".pdf")])
    

    # Check scraped content if enabled
    current_scraped_files = []
    if include_scraped:
        scraped_content_dir = os.path.join(SCRAPED_CONTENT_DIR, "content")
        if os.path.exists(scraped_content_dir):
            current_scraped_files = sorted([f for f in os.listdir(scraped_content_dir) if f.endswith(".json")])

    # Read last sources
    last_files = []
    last_scraped_files = []
    if os.path.exists(source_record_file):
        with open(source_record_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if content:
                lines = content.split('\n')
                # Separate files and scraped files
                for line in lines:
                    if line.startswith('scraped:'):
                        last_scraped_files.append(line[8:])  # Remove 'scraped:' prefix
                    else:
                        last_files.append(line)
                last_files = sorted(last_files)
                last_scraped_files = sorted(last_scraped_files)

    # Check if sources changed
    files_changed = current_files != last_files
    scraped_changed = current_scraped_files != last_scraped_files
    
    # Check if vector database exists
    db_exists = _validate_vector_database_exists()
    
    # Rebuild if sources changed OR database is missing
    rebuild_needed = files_changed or scraped_changed or not db_exists
    
    if rebuild_needed:
        # Log specific reasons for rebuild
        reasons = []
        if files_changed:
            reasons.append(f"PDF files changed (was: {len(last_files)}, now: {len(current_files)})")
        if scraped_changed:
            reasons.append(f"Scraped content changed (was: {len(last_scraped_files)}, now: {len(current_scraped_files)})")
        if not db_exists:
            reasons.append("Vector database files missing or corrupted")
        
        print(f"[Gemini3] Rebuilding vector store. Reasons: {'; '.join(reasons)}")
        
        try:
            # Load all documents
            all_docs = []
            
            # Load PDF documents
            if current_files:
                pdf_docs = load_documents_from_folder(folder_path)
                all_docs.extend(pdf_docs)
                print(f"[Gemini3] Loaded {len(pdf_docs)} PDF documents")
            
            
            # Load scraped documents
            if include_scraped:
                scraped_docs = load_scraped_documents()
                all_docs.extend(scraped_docs)
                print(f"[Gemini3] Loaded {len(scraped_docs)} scraped documents")
            
            if not all_docs:
                print("[Gemini3] No documents found to process.")
                return
            
            # Split documents based on content type
            pdf_docs = [doc for doc in all_docs if doc.metadata.get('content_type') == 'pdf']
            json_docs = [doc for doc in all_docs if doc.metadata.get('content_type') == 'scraped_web']
            
            chunks = []
            
            # Use spaCy for PDF documents - better semantic chunking
            if pdf_docs:
                pdf_chunks = split_documents_spacy(pdf_docs)
                chunks.extend(pdf_chunks)
                print(f"[Gemini3] Created {len(pdf_chunks)} chunks from PDF documents using spaCy")
            
            # Keep JSON/scraped documents as whole chunks - preserves context
            if json_docs:
                chunks.extend(json_docs)  # Add JSON documents directly without splitting
                print(f"[Gemini3] Added {len(json_docs)} JSON documents as whole chunks to preserve context")
            
            create_vector_store(chunks)

            # Only update source tracking after successful vector store creation
            os.makedirs(VECTOR_STORE_DIR, exist_ok=True)
            with open(source_record_file, 'w', encoding='utf-8') as f:
                for filename in current_files:
                    f.write(f"{filename}\n")
                for scraped_file in current_scraped_files:
                    f.write(f"scraped:{scraped_file}\n")
            
            scraped_count = len(current_scraped_files) if include_scraped else 0
            print(f"[Gemini3] Vector store successfully rebuilt with {len(current_files)} PDFs and {scraped_count} scraped documents")
            
        except Exception as e:
            print(f"[Gemini3] Error during vector store rebuild: {e}")
            # Don't update source_files.txt if rebuild failed
            raise
    else:
        print("[Gemini3] Vector store is up-to-date.")

# ========== RAG Chain ==========
def build_rag_qa_chain():
    """
    Build a RetrievalQA chain using Chroma + Gemini.
    """
    update_vector_store(KNOWLEDGE_BASE_DIR, include_scraped=True)
    vectorstore = Chroma(
        persist_directory=VECTOR_STORE_DIR,
        embedding_function=GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    )
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

    prompt_template = PromptTemplate(
        input_variables=["context", "question"],
        template=(
            "You are a helpful assistant for UNSW CSE Open Day.\n\n"
            "IMPORTANT: Use the provided context to answer the question. The context contains structured academic information in markdown format with sections like Description, Program Structure, Learning Outcomes, etc.\n\n"
            "Instructions:\n"
            "- Answer based on the provided context\n"
            "- If the context contains relevant information, provide a comprehensive answer\n"
            "- Only say 'Sorry, I don't know the answer to that question' if the context is completely unrelated to the question\n"
            "- Be specific and detailed when the context provides relevant information\n\n"
            "Context:\n{context}\n\n"
            "Question:\n{question}\n\n"
            "Answer:"
        )
    )

    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": prompt_template}
    )
    print("[Gemini3] Built RAG QA chain with Chroma + Gemini.")
    return qa_chain


# ========== Scrapers Integration Functions ==========
def update_vector_store_with_scraped():
    """
    Convenience function to update vector store including scraped content.
    """
    return update_vector_store(KNOWLEDGE_BASE_DIR, include_scraped=True)


def get_content_sources_summary() -> Dict:
    """
    Get summary of all content sources in the vector store.
    
    Returns:
        Dictionary with content source statistics
    """
    from datetime import datetime
    
    # PDF files
    pdf_files = []
    if os.path.exists(KNOWLEDGE_BASE_DIR):
        pdf_files = [f for f in os.listdir(KNOWLEDGE_BASE_DIR) if f.endswith('.pdf')]
    
    
    # Scraped content
    scraped_files = []
    scraped_content_dir = os.path.join(SCRAPED_CONTENT_DIR, "content")
    if os.path.exists(scraped_content_dir):
        scraped_files = [f for f in os.listdir(scraped_content_dir) if f.endswith('.json')]
    
    # Load source tracking file
    source_record_file = os.path.join(VECTOR_STORE_DIR, "source_files.txt")
    last_updated = None
    if os.path.exists(source_record_file):
        stat = os.stat(source_record_file)
        last_updated = datetime.fromtimestamp(stat.st_mtime).isoformat()
    
    return {
        "pdf_sources": {
            "count": len(pdf_files),
            "files": pdf_files
        },
        "scraped_sources": {
            "count": len(scraped_files),
            "files": scraped_files[:10]  # Show first 10 for preview
        },
        "total_sources": len(pdf_files) + len(scraped_files),
        "vector_store_last_updated": last_updated,
        "vector_store_exists": _validate_vector_database_exists()
    }


def force_rebuild_vector_store():
    """
    Force rebuild of vector store regardless of changes.
    Useful for admin operations.
    """
    print("[Gemini3] Force rebuilding vector store...")
    
    try:
        # Load all documents
        all_docs = []
        
        # Load PDF documents
        if os.path.exists(KNOWLEDGE_BASE_DIR):
            pdf_docs = load_documents_from_folder(KNOWLEDGE_BASE_DIR)
            all_docs.extend(pdf_docs)
            print(f"[Gemini3] Loaded {len(pdf_docs)} PDF documents")
        
        
        # Load scraped documents
        scraped_docs = load_scraped_documents()
        all_docs.extend(scraped_docs)
        print(f"[Gemini3] Loaded {len(scraped_docs)} scraped documents")
        
        if not all_docs:
            print("[Gemini3] No documents found to process.")
            return False
        
        # Split documents based on content type
        pdf_docs = [doc for doc in all_docs if doc.metadata.get('content_type') == 'pdf']
        json_docs = [doc for doc in all_docs if doc.metadata.get('content_type') == 'scraped_web']
        
        chunks = []
        
        # Use spaCy for PDF documents - better semantic chunking
        if pdf_docs:
            pdf_chunks = split_documents_spacy(pdf_docs)
            chunks.extend(pdf_chunks)
            print(f"[Gemini3] Created {len(pdf_chunks)} chunks from PDF documents using spaCy")
        
        # Keep JSON/scraped documents as whole chunks - preserves context
        if json_docs:
            chunks.extend(json_docs)  # Add JSON documents directly without splitting
            print(f"[Gemini3] Added {len(json_docs)} JSON documents as whole chunks to preserve context")
        
        create_vector_store(chunks)
        
        # Update source tracking
        source_record_file = os.path.join(VECTOR_STORE_DIR, "source_files.txt")
        os.makedirs(VECTOR_STORE_DIR, exist_ok=True)
        
        with open(source_record_file, 'w', encoding='utf-8') as f:
            # Write PDF files
            if os.path.exists(KNOWLEDGE_BASE_DIR):
                pdf_files = [f for f in os.listdir(KNOWLEDGE_BASE_DIR) if f.endswith('.pdf')]
                for filename in sorted(pdf_files):
                    f.write(f"{filename}\n")
            
            
            # Write scraped files
            scraped_content_dir = os.path.join(SCRAPED_CONTENT_DIR, "content")
            if os.path.exists(scraped_content_dir):
                scraped_files = [f for f in os.listdir(scraped_content_dir) if f.endswith('.json')]
                for scraped_file in sorted(scraped_files):
                    f.write(f"scraped:{scraped_file}\n")
        
        print(f"[Gemini3] Force rebuild completed successfully")
        return True
        
    except Exception as e:
        print(f"[Gemini3] Force rebuild failed: {e}")
        return False


# ========== Gemini Safety Check ==========
def is_query_safe_by_gemini(query: str) -> bool:
    """
    Check if query is safe using Gemini's built-in safety filters
    """
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(query)
        if response.prompt_feedback and response.prompt_feedback.block_reason:
            print(f"[Gemini3] Query blocked by Gemini Safety: {response.prompt_feedback.block_reason}")
            return False
        print("[Gemini3] Query passed safety check")
        return True
    except Exception as e:
        print(f"[Gemini3] Safety check error: {e}")
        # Default to safe if check fails
        return True
    
# ========= Gemini Query Rewqrite =========
def rewrite_query_gemini(original_query: str) -> str:
    prompt = f"""
    You are a helpful assistant that rewrites user queries to make them more comprehensive and structured, so they retrieve the most complete and relevant academic information.

    All documents are structured in Markdown format, containing sections like:

    - ## Description
    - ## Learning Outcomes
    - ## Program Structure
    - ## Study Details
    - ## Academic Information
    - ## Administrative Information

    If the user query is vague or general (e.g., "Tell me about COMP9315"), rewrite it to request **all key academic details** from the document.

    If the query is about a course or program code, or a specific question (e.g., about availability or entry requirements), still rephrase to **encourage complete context retrieval**.

    Always include the code or course name explicitly in the rewritten query.

    ---

    ### Example 1
    Input: "Tell me about COMP9020"
    Rewritten: "Provide full academic and program information for COMP9020, including description, learning outcomes, structure, and study details"

    ### Example 2
    Input: "What is 5546?"
    Rewritten: "Give all available information about program 5546, including description, outcomes, structure, and campus details"

    ### Example 3
    Input: "Where is ACTL5105 taught?"
    Rewritten: "Provide study details and all other academic information for ACTL5105"

    ---

    Now rewrite the following:

    Input: "{original_query}"
    Rewritten:
    """
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        return response.text.strip().split("\n")[0]
    except Exception as e:
        print("[Rewrite Error]", e)
        return original_query

# ========== Fallback ==========
def fallback_llm_answer(question: str) -> str:
    """
    Directly use Gemini to answer without RAG context.
    """
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    print("[Gemini3] Using fallback direct Gemini LLM.")
    return llm.invoke(question).content

# ========= Query Processing Pipeline ============
def ask_with_rag_and_fallback(question: str, qa_chain) -> dict:
    """
    Try answering via RAG first, fallback to direct LLM if no context found.
    Includes safety check for all queries.
    """
    print(f"[Gemini3] Processing question with RAG: {question}")
    
    # 1.Safety Check
    if not is_query_safe_by_gemini(question):
        return {
            "answer": "I cannot process this query as it may violate safety guidelines. Please rephrase your question.",
            "sources": [],
            "matched_files": [],
            "safety_blocked": True
        }
    
    # 2.Rewrite Query
    rewritten_query = rewrite_query_gemini(question)
    print(f"[Rewritten Query] {rewritten_query}")
    
    result = qa_chain.invoke({"query": rewritten_query})

    sources = result.get("source_documents", [])
    if not sources or all(len(doc.page_content.strip()) < 10 for doc in sources):
        print("[Gemini3] No relevant sources found, using LLM fallback.")
        fallback_answer = fallback_llm_answer(question)
        return {
            "answer": fallback_answer,
            "sources": [],
            "matched_files": [],
            "safety_blocked": False
        }

    # Visual chunk inspection
    print(f"\n{'='*80}")
    print(f"RETRIEVED {len(sources)} SOURCE CHUNKS FOR QUERY: {question}")
    print(f"{'='*80}")
    for i, doc in enumerate(sources, 1):
        print(f"\n--- CHUNK {i} ---")
        source_file = doc.metadata.get('source', 'Unknown') if hasattr(doc, 'metadata') and doc.metadata else 'Unknown'
        filename = source_file.split('/')[-1] if '/' in source_file else source_file
        page = doc.metadata.get('page', 'Unknown') if hasattr(doc, 'metadata') and doc.metadata else 'Unknown'
        
        print(f"SOURCE: {filename}")
        print(f"PAGE: {page}")
        print(f"CONTENT ({len(doc.page_content)} chars):")
        
        lines = doc.page_content.split('\n')
        for line_num, line in enumerate(lines, 1):
            print(f"{line_num:3d}: {line}")
        print(f"{'─'*60}")
    print(f"{'='*80}\n")

    # 3.Extract source file information from metadata
    matched_files = []
    source_details = []
    
    for doc in sources:
        source_details.append(doc.page_content)
        # Get filename from metadata
        if hasattr(doc, 'metadata') and doc.metadata:
            source_file = doc.metadata.get('source', 'Unknown')
            # Extract just the filename from the full path
            if source_file != 'Unknown':
                filename = source_file.split('/')[-1] if '/' in source_file else source_file
                if filename not in matched_files:
                    matched_files.append(filename)
    
    print(f"[Gemini3] Matched files: {matched_files}")
    
    return {
        "answer": result.get("result", "I don't know."),
        "sources": source_details,
        "matched_files": matched_files,
        "safety_blocked": False
    }
