import streamlit as st
import os
import json
import uuid
import numpy as np
from pathlib import Path
from pdfminer.high_level import extract_text
from sentence_transformers import SentenceTransformer
import faiss
from retriever import Retriever
import requests
import tempfile

# Orchestrator configuration
ORCHESTRATOR_URL = "http://127.0.0.1:8000/chat"

# Configuration
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
CHUNK_SIZE = 800
OVERLAP = 100
INDEX_PATH = "faiss_index.bin"
META_PATH = "faiss_meta.json"
RAW_PATH = "faiss_raw.json"
PDFS_FOLDER = "pdfs"

# Initialize session state
if 'index_loaded' not in st.session_state:
    st.session_state.index_loaded = False
if 'retriever' not in st.session_state:
    st.session_state.retriever = None
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = []
if 'selected_example' not in st.session_state:
    st.session_state.selected_example = None
if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if 'account_id' not in st.session_state:
    st.session_state.account_id = "acct_123"  # Default for demo
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = True  # Default for demo

def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=OVERLAP):
    """Chunk text with overlap."""
    chunks = []
    start = 0
    L = len(text)
    while start < L:
        end = min(L, start + chunk_size)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks

def ingest_pdf_file(pdf_path, existing_metas=None, existing_raw=None, existing_embeddings=None):
    """Ingest a single PDF file and return embeddings, metas, and raw text."""
    model = SentenceTransformer(EMBED_MODEL_NAME)
    embeddings = existing_embeddings if existing_embeddings else []
    metas = existing_metas if existing_metas else []
    raw_map = existing_raw if existing_raw else {}
    
    print(f'Processing {pdf_path}')
    text = extract_text(str(pdf_path))
    chunks = chunk_text(text)
    
    for i, chunk in enumerate(chunks):
        id = str(uuid.uuid4())
        metas.append({
            "id": id,
            "source": Path(pdf_path).name,
            "chunk_index": i,
            "text_preview": chunk[:300]
        })
        raw_map[id] = chunk
        emb = model.encode(chunk)
        embeddings.append(emb)
    
    return embeddings, metas, raw_map

def load_or_create_index():
    """Load existing index or create new one."""
    if os.path.exists(INDEX_PATH) and os.path.exists(META_PATH) and os.path.exists(RAW_PATH):
        try:
            index = faiss.read_index(INDEX_PATH)
            with open(META_PATH, 'r', encoding='utf8') as f:
                metas = json.load(f)
            with open(RAW_PATH, 'r', encoding='utf8') as f:
                raw_map = json.load(f)
            return index, metas, raw_map
        except Exception as e:
            st.error(f"Error loading existing index: {e}")
            return None, None, None
    return None, None, None

def save_index(index, metas, raw_map):
    """Save FAISS index and metadata."""
    faiss.write_index(index, INDEX_PATH)
    with open(META_PATH, 'w', encoding='utf8') as f:
        json.dump(metas, f, ensure_ascii=False, indent=2)
    with open(RAW_PATH, 'w', encoding='utf8') as f:
        json.dump(raw_map, f, ensure_ascii=False, indent=2)

def process_uploaded_file(uploaded_file):
    """Process an uploaded PDF file."""
    os.makedirs(PDFS_FOLDER, exist_ok=True)
    
    # Save uploaded file
    file_path = os.path.join(PDFS_FOLDER, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    # Load existing index if available
    index, metas, raw_map = load_or_create_index()
    existing_embeddings = []
    
    if index is not None and metas is not None:
        # Extract existing embeddings from index
        # Note: FAISS doesn't allow direct extraction, so we'll rebuild
        # For efficiency, we could store embeddings separately, but for simplicity, we rebuild
        st.info("Rebuilding index with new document...")
        existing_embeddings = None  # We'll rebuild from all PDFs
        metas = []
        raw_map = {}
    else:
        index = None
        metas = []
        raw_map = {}
    
    # Process all PDFs in the folder (including the new one)
    model = SentenceTransformer(EMBED_MODEL_NAME)
    embeddings = []
    
    for pdf_file in Path(PDFS_FOLDER).glob("*.pdf"):
        text = extract_text(str(pdf_file))
        chunks = chunk_text(text)
        for i, chunk in enumerate(chunks):
            id = str(uuid.uuid4())
            metas.append({
                "id": id,
                "source": pdf_file.name,
                "chunk_index": i,
                "text_preview": chunk[:300]
            })
            raw_map[id] = chunk
            emb = model.encode(chunk)
            # Ensure embedding is a numpy array and convert to float32
            if not isinstance(emb, np.ndarray):
                emb = np.array(emb)
            embeddings.append(emb.astype('float32'))
    
    if not embeddings:
        return False, "No chunks found in PDF"
    
    # Create or update FAISS index
    X = np.vstack(embeddings).astype('float32')
    dim = X.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(X)
    
    # Save index
    save_index(index, metas, raw_map)
    
    return True, f"Successfully ingested {len(embeddings)} chunks from {uploaded_file.name}"

def initialize_retrievers():
    """Initialize retriever (for document ingestion only)."""
    if os.path.exists(INDEX_PATH) and os.path.exists(META_PATH) and os.path.exists(RAW_PATH):
        try:
            st.session_state.retriever = Retriever()
            st.session_state.index_loaded = True
            return True
        except Exception as e:
            st.error(f"Error initializing retriever: {e}")
            return False
    return False

# Streamlit UI
st.set_page_config(page_title="iMitra", page_icon="🏦", layout="wide")

st.title("🏦 Your-Bank-iMitra")
st.markdown("Upload PDF documents and query them with AI-powered answers and citations")

# Sidebar for document upload
with st.sidebar:
    st.header("📄 Document Upload")
    
    uploaded_file = st.file_uploader(
        "Upload a PDF document",
        type=['pdf'],
        help="Upload a PDF file to add it to the knowledge base"
    )
    
    if uploaded_file is not None:
        if st.button("📥 Ingest Document", type="primary"):
            with st.spinner("Processing document..."):
                success, message = process_uploaded_file(uploaded_file)
                if success:
                    st.success(message)
                    # Reset retrievers to reload index
                    st.session_state.index_loaded = False
                    st.session_state.retriever = None
                    st.rerun()
                else:
                    st.error(message)
    
    st.markdown("---")
    st.header("📊 Index Status")
    
    # Check if index exists
    if os.path.exists(INDEX_PATH):
        try:
            with open(META_PATH, 'r', encoding='utf8') as f:
                metas = json.load(f)
            st.success(f"✅ Index loaded: {len(metas)} chunks")
            
            # Show document sources
            sources = set([m['source'] for m in metas])
            st.markdown(f"**Documents:** {len(sources)}")
            for source in sorted(sources):
                count = sum(1 for m in metas if m['source'] == source)
                st.markdown(f"  - {source} ({count} chunks)")
        except Exception as e:
            st.error(f"Error reading index: {e}")
    else:
        st.warning("⚠️ No index found. Upload a document to get started.")

# Main content area
# Check if orchestrator is available
orchestrator_available = True
try:
    response = requests.get("http://127.0.0.1:8000/docs", timeout=2)
except:
    orchestrator_available = False

if not st.session_state.index_loaded:
    if initialize_retrievers():
        st.success("✅ Index loaded successfully!")
    else:
        st.warning("⚠️ Please upload and ingest at least one PDF document before querying.")

# Query interface
if st.session_state.index_loaded and orchestrator_available:
    st.header("Ask a Question ?💬 ")
    
    # Account settings (for actions)
    with st.expander("⚙️ Account Settings"):
        st.session_state.account_id = st.text_input("Account ID", value=st.session_state.account_id, key="account_id_input")
        st.session_state.authenticated = st.checkbox("Authenticated", value=st.session_state.authenticated, key="auth_checkbox")
    
    # Query input
    query = st.text_input(
        "Enter your question:",
        placeholder="e.g., What is the ATM withdrawal limit? or Block my card",
        key="query_input"
    )
    
    # If an example was selected, use it for search automatically
    example_query = None
    if st.session_state.selected_example:
        example_query = st.session_state.selected_example
        st.session_state.selected_example = None  # Clear it after using
        # Show which query is being used
        st.info(f"🔍 Searching for: **{example_query}**")
    
    col1, col2 = st.columns([1, 5])
    with col1:
        search_button = st.button("Send Query💬", type="primary", use_container_width=True)
    
    # Determine if we should search (button click or example was selected)
    should_search = search_button or (example_query is not None)
    search_query = example_query if example_query else query
    
    # Process query through orchestrator
    if should_search and search_query:
        with st.spinner("Processing your request..."):
            try:
                # Call orchestrator
                payload = {
                    "session_id": st.session_state.session_id,
                    "user_text": search_query,
                    "account_id": st.session_state.account_id if st.session_state.authenticated else None,
                    "authenticated": st.session_state.authenticated
                }
                
                response = requests.post(ORCHESTRATOR_URL, json=payload, timeout=30)
                response.raise_for_status()
                result = response.json()
                
                intent = result.get("intent", "unknown")
                
                # Display intent
                if intent == "faq":
                    st.success("📚 FAQ Query")
                    parsed = result.get("response", {})
                    
                    # Display answer
                    st.markdown("### 📝 Answer")
                    st.markdown(parsed.get("answer", "No answer generated"))
                    
                    # Display citations
                    st.markdown("### 📚 Citations")
                    citations = parsed.get("citations", [])
                    if citations:
                        for i, citation in enumerate(citations, 1):
                            source = citation.get("source", "Unknown")
                            chunk_idx = citation.get("chunk_index", "?")
                            with st.expander(f"Citation {i}: {source} (Chunk {chunk_idx})"):
                                st.markdown(f"**Source:** {source}")
                                st.markdown(f"**Chunk Index:** {chunk_idx}")
                    else:
                        st.info("No specific citations provided.")
                        
                elif intent == "action":
                    st.success("⚡ Action Query")
                    action_result = result.get("action_result", {})
                    status = result.get("status", "ok")
                    
                    if status == "needs_auth":
                        st.warning("🔒 Authentication required for this action. Please enable authentication in Account Settings.")
                    else:
                        st.markdown("### ✅ Action Result")
                        st.json(action_result)
                        
                else:
                    st.warning(f"Unknown intent: {intent}")
                    st.json(result)
                
            except requests.exceptions.ConnectionError:
                st.error("❌ Cannot connect to orchestrator. Please ensure `server_orchestrator.py` is running on port 8000.")
            except requests.exceptions.Timeout:
                st.error("⏱️ Request timed out. Please try again.")
            except Exception as e:
                st.error(f"Error processing query: {e}")
                st.exception(e)
    
    elif search_button and not query:
        st.warning("Please enter a question before searching.")
    
    # Example queries
    st.markdown("---")
    st.markdown("### 💡 Example Queries")
    st.markdown("**FAQ Queries:**")
    example_queries_faq = [
        "What is the ATM withdrawal limit?",
        "What are the account balance requirements?",
        "What are the card blocking procedures?",
        "What fees are associated with the account?",
    ]
    
    cols1 = st.columns(len(example_queries_faq))
    for i, example in enumerate(example_queries_faq):
        with cols1[i]:
            if st.button(example, key=f"example_faq_{i}", use_container_width=True):
                st.session_state.selected_example = example
                st.rerun()
    
    st.markdown("**Action Queries:**")
    example_queries_action = [
        "What is my account balance?",
        "Block my card immediately",
    ]
    
    cols2 = st.columns(len(example_queries_action))
    for i, example in enumerate(example_queries_action):
        with cols2[i]:
            if st.button(example, key=f"example_action_{i}", use_container_width=True):
                st.session_state.selected_example = example
                st.rerun()

elif not orchestrator_available:
    st.error("❌ Orchestrator is not running. Please start it with: `uvicorn server_orchestrator:app --port 8000`")
    st.info("Also ensure `server_fastapi.py` is running on port 8001: `uvicorn server_fastapi:app --port 8001`")
else:
    st.info("👆 Please upload and ingest at least one PDF document using the sidebar to start querying.")

