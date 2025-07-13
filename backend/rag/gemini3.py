# rag/gemini3.py
import os
import spacy
import google.generativeai as genai
from langchain.text_splitter import RecursiveCharacterTextSplitter
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
            print(f"[Gemini3] Loaded {len(doc_chunks)} pages from {filename}")
            documents.extend(doc_chunks)
    return documents
    
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
def update_vector_store(folder_path):
    """
    Check if docs folder has new or different files. If yes, rebuild vector store.
    """
    source_record_file = os.path.join(VECTOR_STORE_DIR, "source_files.txt")
    current_files = sorted([f for f in os.listdir(folder_path) if f.endswith(".pdf")])

    if not current_files:
        print("[Gemini3] No PDF files found in docs folder.")
        return

    # read last files list
    last_files = []
    if os.path.exists(source_record_file):
        with open(source_record_file, 'r') as f:
            last_files = sorted(line.strip() for line in f.readlines())

    if current_files != last_files:
        print("[Gemini3] Detected new or different files. Rebuilding vector store...")
        docs = load_documents_from_folder(folder_path)
        chunks = split_documents_spacy(docs)
        create_vector_store(chunks)

        # save current files list
        os.makedirs(VECTOR_STORE_DIR, exist_ok=True)
        with open(source_record_file, 'w') as f:
            for filename in current_files:
                f.write(f"{filename}\n")
    else:
        print("[Gemini3] Vector store is up-to-date.")

# ========== RAG Chain ==========
def build_rag_qa_chain():
    """
    Build a RetrievalQA chain using Chroma + Gemini.
    """
    update_vector_store(KNOWLEDGE_BASE_DIR)
    vectorstore = Chroma(
        persist_directory=VECTOR_STORE_DIR,
        embedding_function=GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    )
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

    prompt_template = PromptTemplate(
        input_variables=["context", "question"],
        template=(
            "You are a helpful assistant for UNSW CSE Open Day."
            " Always answer politely and concisely."
            " If you do not know the answer, say 'Sorry, I don't know the answer to that question.'\n\n"
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

# ========== Fallback ==========
def fallback_llm_answer(question: str) -> str:
    """
    Directly use Gemini to answer without RAG context.
    """
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    print("[Gemini3] Using fallback direct Gemini LLM.")
    return llm.invoke(question).content

def ask_with_rag_and_fallback(question: str, qa_chain) -> dict:
    """
    Try answering via RAG first, fallback to direct LLM if no context found.
    """
    print(f"[Gemini3] Processing question with RAG: {question}")
    update_vector_store(KNOWLEDGE_BASE_DIR)
    result = qa_chain.invoke({"query": question})

    sources = result.get("source_documents", [])
    if not sources or all(len(doc.page_content.strip()) < 10 for doc in sources):
        print("[Gemini3] No relevant sources found, using LLM fallback.")
        fallback_answer = fallback_llm_answer(question)
        return {
            "answer": fallback_answer,
            "sources": []
        }

    return {
        "answer": result.get("result", "I don't know."),
        "sources": [doc.page_content for doc in sources]
    }
