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
from .hybrid_search import HybridSearchEngine

# ========== Google API keys ==========
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "rag/key.json")
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# ========== Vector Store ==========
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
VECTOR_STORE_DIR = os.path.join(CURRENT_DIR, "vector_store")
KNOWLEDGE_BASE_DIR = os.path.join(CURRENT_DIR, "docs")
SCRAPED_CONTENT_DIR = os.path.join(CURRENT_DIR, "scraped_content")

# ========== Hybrid Search ==========
# Initialize hybrid search engine (lazy initialization)
_hybrid_search_engine = None

def get_hybrid_search_engine():
    global _hybrid_search_engine
    if _hybrid_search_engine is None:
        content_dir = os.path.join(SCRAPED_CONTENT_DIR, "content")
        _hybrid_search_engine = HybridSearchEngine(content_dir)
    return _hybrid_search_engine

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
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

    prompt_template = PromptTemplate(
        input_variables=["context", "question"],
        template = (
            "You are the UNSW CSE Open Day AI Assistant, designed to help visitors—especially prospective students—explore information about Computer Science at UNSW. 🎓\n\n"
            
            "You are friendly, concise, and informative. You can answer questions about:\n"
            "- Computer Science degrees (undergraduate, postgraduate)\n"
            "- Course structures, prerequisites, key subjects\n"
            "- Student societies (e.g., CSESoc)\n"
            "- Facility locations (e.g., buildings, restrooms)\n"
            "- Open Day schedules and booth locations\n\n"
            
            "You answer questions based on structured academic documents written in Markdown format. These documents include the following sections:\n"
            "- ## Description\n"
            "- ## Learning Outcomes\n"
            "- ## Program Structure\n"
            "- ## Study Details\n"
            "- ## Academic Information\n"
            "- ## Administrative Information\n\n"
            
            "🎯 Your job:\n"
            "- Use the provided context to answer the question clearly and accurately\n"
            "- Respond in a friendly, conversational tone, using emojis where appropriate 😊\n"
            "- If comparing two or more courses/programs, present the answer in a **Markdown table** comparing key attributes like name, duration, campus, intake, AQF level, etc.\n"
            "- If the question is vague or a greeting (e.g., 'hi', 'hello', 'what can you do?'), **ignore the context** and respond with:\n"
            "  👋 Hi there! I'm your UNSW CSE Open Day Assistant. I can help you with:\n"
            "  - 🧑‍🏫 Program and course info\n"
            "  - 📍 Maps and booth locations\n"
            "  - 🗓️ Event schedules\n"
            "  - 💬 Student societies and FAQs\n"
            "  What would you like to explore today?\n"
            "  (Try asking about a course code like COMP9020 or a program like 3789!)\n"
            
            "- If the context is unrelated or doesn't contain an answer, reply:\n"
            "  🙁 Sorry, I couldn't find relevant information in our materials. Could you please rephrase or be more specific?\n"
            "- If a user asks a question unrelated to Computer Science or the Open Day event, kindly reply:\n"
            "  \"I'm currently focused on UNSW CSE Open Day and Computer Science topics. Please check the main UNSW website for other areas.\"\n"
            "- If users ask for building locations, directions, restrooms, or booth areas, use the MazeMap search URL pattern:\n"
            "  For buildings: https://use.mazemap.com/#v=1&config=unsw&campusid=111&zlevel=1&center=151.231022,-33.917689&zoom=16.2&search=[SEARCH_TERM]\n"
            "  Replace [SEARCH_TERM] with the building code/name (URL encode spaces as %20). This triggers search suggestions.\n"
            "  Format as: [Building/Location MazeMap Search](URL)\n"
            "  Example: \"You can search for K17 Building here: [K17 MazeMap Search](https://use.mazemap.com/#v=1&config=unsw&campusid=111&zlevel=1&center=151.231022,-33.917689&zoom=16.2&search=K17)\"\n\n"

            "✅ Always:\n"
            "- Encourage follow-up questions\n"
            "- Keep responses helpful and engaging\n"
            "- Prioritize information from *.unsw.edu.au domains when providing links\n"

            "------------------------------\n"
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
def rewrite_query_gemini(original_query: str, conversation_history: list = None) -> str:
    # Format conversation history for context
    from services.query_processor import format_conversation_history
    formatted_history = format_conversation_history(conversation_history) if conversation_history else ""
    
    history_context = ""
    if formatted_history:
        history_context = f"""
    
    == Conversation History ==
    The user has had the following previous conversation:
    {formatted_history}
    
    🔍 Context-Aware Rewriting:
    - If the user's current query contains pronouns or vague references (like "it", "this course", "that program", "them", "这个", "那个"), use the conversation history to determine what they're referring to and make the query specific.
    - If the user is asking a follow-up question about something mentioned earlier, incorporate the specific course/program codes or names from the history.
    - If the user is comparing things mentioned in history, make sure to include all relevant identifiers.
    
    """
    
    prompt = f"""
    You are a helpful assistant that rewrites user queries to make them more comprehensive and structured, so they retrieve the most complete and relevant academic information.

    All academic documents are structured in Markdown format, containing sections like:
    - ## Description
    - ## Learning Outcomes
    - ## Program Structure
    - ## Study Details
    - ## Academic Information
    - ## Administrative Information
    - **Course Code:** (inline metadata)
    - **Source URL:** (inline metadata)
    {history_context}
    🎯 Rewrite Instructions:
    - If the user input is vague or general (e.g., "Tell me about COMP9315"), rewrite it to request **all key academic details** from the document.
    - If the query refers to a course or program code (e.g., COMP9020 or 5546), rephrase it to encourage **complete context retrieval** — include description, structure, learning outcomes, academic metadata, and study details.
    - Always include the course or program code explicitly in the rewritten query.
    - ✅ However, if the input is a **greeting or general opener** (e.g., "hi", "hello", "what can you do?"), **DO NOT rewrite** — return it exactly as-is.

    💡 Tip: When unsure what specific information the user wants, assume they want **everything available** to ensure completeness.

    ---

    ### Example 1
    Input: "Tell me about COMP9020"  
    Rewritten: "Provide full academic and course information for COMP9020, including description, academic metadata, learning outcomes, structure, and study details"

    ### Example 2
    Input: "What is 5546?"  
    Rewritten: "Give all available information about program 5546, including description, outcomes, structure, academic info, and campus details"

    ### Example 3  
    Input: "Where is ACTL5105 taught?"  
    Rewritten: "Provide study details and all academic information for ACTL5105"

    ### Example 4  
    Input: "hi"  
    Rewritten: "hi"
    
    ### Example 5 (with history context)
    History: User asked about COMP9020
    Input: "What about the prerequisites for it?"
    Rewritten: "What are the prerequisites and academic requirements for COMP9020?"

    ### Example 6 (with history context)  
    History: User asked about programs 5546 and 8543
    Input: "Which one has better job prospects?"
    Rewritten: "Compare job prospects and career outcomes between program 5546 and program 8543"

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
def fallback_llm_answer(question: str, conversation_history: list = None) -> str:
    """
    Directly use Gemini to answer without RAG context, but with consistent UNSW CSE Open Day assistant identity.
    """
    from services.query_processor import format_conversation_history
    formatted_history = format_conversation_history(conversation_history) if conversation_history else ""
    
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    
    # Use the same identity and tone as the main RAG chain
    if formatted_history:
        prompt_template = PromptTemplate(
            input_variables=["history", "question"],
            template=(
                "You are the UNSW CSE Open Day AI Assistant, designed to help visitors—especially prospective students—explore information about Computer Science at UNSW. 🎓\n\n"
                
                "== Conversation History ==\n"
                "{history}\n\n"
                
                "== Current Query ==\n"
                "❓ Question:\n{question}\n\n"
                
                "== 🧠 Instructions ==\n"
                "Please answer the question based on the conversation history. "
                "If the user uses vague references like 'it', 'this course', 'that program', refer to the conversation history to determine what they're referring to.\n\n"
                
                "Since I don't have specific context documents available for this query, I'll provide general information about UNSW CSE programs and encourage the user to ask more specific questions or visit official UNSW resources.\n\n"
                
                "Use a friendly, conversational tone with emojis where appropriate 😊. "
                "If the question is vague or a greeting (e.g., 'hi', 'hello', 'what can you do?'), respond with:\n"
                "👋 Hi there! I'm your UNSW CSE Open Day Assistant. I can help you with:\n"
                "- 🧑‍🏫 Program and course info\n"
                "- 📍 Maps and booth locations\n"
                "- 🗓️ Event schedules\n"
                "- 💬 Student societies and FAQs\n"
                "What would you like to explore today?\n"
                "(Try asking about a course code like COMP9020 or a program like 3789!)\n\n"
                
                "Always encourage follow-up questions and keep responses helpful and engaging."
            )
        )
        formatted_prompt = prompt_template.format(history=formatted_history, question=question)
    else:
        prompt_template = PromptTemplate(
            input_variables=["question"],
            template=(
                "You are the UNSW CSE Open Day AI Assistant, designed to help visitors—especially prospective students—explore information about Computer Science at UNSW. 🎓\n\n"
                
                "❓ Question:\n{question}\n\n"
                
                "== 🧠 Instructions ==\n"
                "Since I don't have specific context documents available for this query, I'll provide general information about UNSW CSE programs and encourage the user to ask more specific questions or visit official UNSW resources.\n\n"
                
                "Use a friendly, conversational tone with emojis where appropriate 😊. "
                "If the question is vague or a greeting (e.g., 'hi', 'hello', 'what can you do?'), respond with:\n"
                "👋 Hi there! I'm your UNSW CSE Open Day Assistant. I can help you with:\n"
                "- 🧑‍🏫 Program and course info\n"
                "- 📍 Maps and booth locations\n"
                "- 🗓️ Event schedules\n"
                "- 💬 Student societies and FAQs\n"
                "What would you like to explore today?\n"
                "(Try asking about a course code like COMP9020 or a program like 3789!)\n\n"
                
                "Always encourage follow-up questions and keep responses helpful and engaging."
            )
        )
        formatted_prompt = prompt_template.format(question=question)
    
    print("[Gemini3] Using fallback direct Gemini LLM with UNSW CSE Open Day assistant identity.")
    return llm.invoke(formatted_prompt).content

# ========= Query Processing Pipeline ============
def ask_with_hybrid_search(question: str, qa_chain, conversation_history: list = None) -> dict:
    """
    Answer questions using hybrid search (RAG + keyword)
    """
    print(f"[Gemini3] Processing question with hybrid search: {question}")
    
    # 1.Safety Check
    if not is_query_safe_by_gemini(question):
        return {
            "answer": "I cannot process this query as it may violate safety guidelines. Please rephrase your question.",
            "sources": [],
            "matched_files": [],
            "safety_blocked": True
        }
    
    # 2.Rewrite Query with conversation history
    rewritten_query = rewrite_query_gemini(question, conversation_history)
    print(f"[Rewritten Query] {rewritten_query}")
    
    # 3. Get RAG results
    result = qa_chain.invoke({"query": rewritten_query})
    rag_sources = result.get("source_documents", [])
    
    # Convert RAG results to standard format
    rag_results = []
    for doc in rag_sources:
        rag_results.append({
            'page_content': doc.page_content,
            'metadata': doc.metadata if hasattr(doc, 'metadata') else {}
        })
    
    # 4. Add MazeMap fallback document (always included in context)
    fallback_doc = {
        'page_content': """
UNSW Campus Map Instructions:

When users ask about building locations, directions, or facilities, provide MazeMap search links that will show search suggestions.

## MazeMap Search URL Pattern:
For buildings: https://use.mazemap.com/#v=1&config=unsw&campusid=111&zlevel=1&center=151.231022,-33.917689&zoom=16.2&search=[SEARCH_TERM]

Replace [SEARCH_TERM] with the building code or name. This will trigger MazeMap's search functionality with suggestions.

## Search Term Examples:
- For K17: search=K17
- For Computer Science Building: search=Computer%20Science%20Building
- For Engineering: search=Engineering
- For Roundhouse: search=Roundhouse
- For Library: search=Library

## URL Examples:
- K17 Building: https://use.mazemap.com/#v=1&config=unsw&campusid=111&zlevel=1&center=151.231022,-33.917689&zoom=16.2&search=K17
- Computer Science: https://use.mazemap.com/#v=1&config=unsw&campusid=111&zlevel=1&center=151.231022,-33.917689&zoom=16.2&search=Computer%20Science
- General campus map: https://use.mazemap.com/#v=1&config=unsw&campusid=111&zlevel=1&center=151.231022,-33.917689&zoom=16.2

Always format as: [Building/Location MazeMap Search](URL)
""",
        'metadata': {
            'source': 'mazemap_fallback',
            'search_type': 'fallback',
            'rag_score': 0,
            'keyword_score': 0,
            'hybrid_score': 0
        }
    }
    
    # 5. Execute hybrid search
    hybrid_engine = get_hybrid_search_engine()
    hybrid_results = hybrid_engine.search_hybrid(rewritten_query, rag_results, max_results=5)
    
    # Always add MazeMap fallback to results
    hybrid_results.append(fallback_doc)
    
    print(f"[Hybrid Search] Found {len(hybrid_results)} results after threshold filtering")
    
    # If hybrid search has no results, use fallback
    if not hybrid_results:
        print("[Gemini3] No results from hybrid search after filtering, using LLM fallback.")
        fallback_answer = fallback_llm_answer(question, conversation_history)
        return {
            "answer": fallback_answer,
            "sources": [],
            "matched_files": [],
            "safety_blocked": False
        }
    
    # Display hybrid search results
    print(f"\n{'='*80}")
    print(f"HYBRID SEARCH RESULTS FOR QUERY: {question}")
    print(f"{'='*80}")
    for i, doc in enumerate(hybrid_results, 1):
        print(f"\n--- RESULT {i} ---")
        metadata = doc.get('metadata', {})
        source_file = metadata.get('source', 'Unknown')
        search_type = metadata.get('search_type', 'unknown')
        hybrid_score = metadata.get('hybrid_score', 0)
        
        filename = source_file.split('/')[-1] if '/' in source_file else source_file
        
        print(f"SOURCE: {filename}")
        print(f"SEARCH TYPE: {search_type}")
        print(f"HYBRID SCORE: {hybrid_score:.2f}")
        
        if 'matched_terms' in metadata:
            print(f"MATCHED: {metadata['matched_terms']}")
        
        print(f"CONTENT ({len(doc.get('page_content', ''))} chars):")
        lines = doc.get('page_content', '').split('\n')
        for line_num, line in enumerate(lines[:10], 1):  # Only show first 10 lines
            print(f"{line_num:3d}: {line}")
        if len(lines) > 10:
            print("    ... (truncated)")
        print(f"{'─'*60}")
    print(f"{'='*80}\n")
    
    # 5. Use hybrid results to rebuild context and generate answer
    context_parts = []
    for doc in hybrid_results:
        context_parts.append(doc.get('page_content', ''))
    
    combined_context = '\n\n'.join(context_parts)
    
    # Format conversation history
    from services.query_processor import format_conversation_history
    formatted_history = format_conversation_history(conversation_history) if conversation_history else ""
    
    # Use template to generate final answer
    vectorstore = Chroma(
        persist_directory=VECTOR_STORE_DIR,
        embedding_function=GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    )
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    
    # Build prompt with history
    if formatted_history:
        prompt_template = PromptTemplate(
            input_variables=["history", "context", "question"],
            template = (
                "You are the UNSW CSE Open Day AI Assistant, designed to help visitors—especially prospective students—explore information about Computer Science at UNSW. 🎓\n\n"

                "== Conversation History ==\n"
                "{history}\n\n"

                "== Current Query ==\n"
                "The following context was retrieved using hybrid search (semantic + keyword matching):\n\n"
                "📚 Context:\n{context}\n\n"
                "❓ Question:\n{question}\n\n"

                "== 🧠 Instructions ==\n"
                "Please answer the question based on the conversation history and the provided context. "
                "If the user uses vague references like 'this course', 'it', or 'that program', refer to the conversation history to determine what they are referring to.\n\n"

                "Use a friendly, conversational tone with emojis where appropriate 😊. "
                "If comparing multiple items (e.g., programs or courses), use **markdown tables** for clarity.\n\n"

                "== 🔗 Link Requirements ==\n"
                "If a source URL is available in the context (e.g., a line like '**Source URL:** https://...'), you **must** extract it and include it at the end of your answer as a clickable markdown link. "
                "Format it as: 📎 [View in Handbook](URL). Do **not** say 'no link available' if the URL is present in the context.\n\n"
                "Always include a clickable link if the user requests one or if the question is about a specific program, specialisation or course."
            )
        )
        final_answer = llm.invoke(prompt_template.format(
            history=formatted_history,
            context=combined_context, 
            question=question
        ))
    else:
        prompt_template = PromptTemplate(
            input_variables=["context", "question"],
            template=(
                "You are the UNSW CSE Open Day AI Assistant, designed to help visitors—especially prospective students—explore information about Computer Science at UNSW. 🎓\n\n"
                "The following context was found using hybrid search (combining semantic and keyword matching):\n\n"
                "Context: {context}\n\n"
                "Question: {question}\n\n"
                "Please provide a comprehensive answer based on the context above. "
                "Use a friendly, conversational tone with emojis where appropriate. "
                "If comparing multiple items, use markdown tables for clarity."
            )
        )
        final_answer = llm.invoke(prompt_template.format(context=combined_context, question=question))
    
    # 6. Extract source file information
    matched_files = []
    source_details = []
    
    for doc in hybrid_results:
        source_details.append(doc.get('page_content', ''))
        metadata = doc.get('metadata', {})
        source_file = metadata.get('source', 'Unknown')
        if source_file != 'Unknown':
            filename = source_file.split('/')[-1] if '/' in source_file else source_file
            if filename not in matched_files:
                matched_files.append(filename)
    
    print(f"[Hybrid Search] Matched files: {matched_files}")
    
    return {
        "answer": final_answer.content if hasattr(final_answer, 'content') else str(final_answer),
        "sources": source_details,
        "matched_files": matched_files,
        "safety_blocked": False,
        "search_type": "hybrid"
    }

def ask_with_rag_and_fallback(question: str, qa_chain, conversation_history: list = None) -> dict:
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
    
    # 2.Rewrite Query with conversation history
    rewritten_query = rewrite_query_gemini(question, conversation_history)
    print(f"[Rewritten Query] {rewritten_query}")
    
    result = qa_chain.invoke({"query": rewritten_query})

    sources = result.get("source_documents", [])
    if not sources or all(len(doc.page_content.strip()) < 10 for doc in sources):
        print("[Gemini3] No relevant sources found, using LLM fallback.")
        fallback_answer = fallback_llm_answer(question, conversation_history)
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
