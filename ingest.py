import os, json, uuid, numpy as np
from pathlib import Path
from pdfminer.high_level import extract_text
from sentence_transformers import SentenceTransformer
import faiss

EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
CHUNK_SIZE = 800
OVERLAP = 100
INDEX_PATH = "faiss_index.bin"
META_PATH = "faiss_meta.json"
RAW_PATH = "faiss_raw.json"

def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=OVERLAP):
    chunks=[]
    start=0
    L=len(text)
    while start < L:
        end=min(L, start+chunk_size)
        chunk=text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks

def ingest_pdf_folder(pdf_folder="pdfs"):
    model = SentenceTransformer(EMBED_MODEL_NAME)
    embeddings=[]
    metas=[]
    raw_map={}
    for pdf_file in Path(pdf_folder).glob("*.pdf"):
        print('Processing', pdf_file)
        text = extract_text(str(pdf_file))
        chunks = chunk_text(text)
        for i, chunk in enumerate(chunks):
            id = str(uuid.uuid4())
            metas.append({ "id": id, "source": pdf_file.name, "chunk_index": i, "text_preview": chunk[:300]})
            raw_map[id] = chunk
            emb = model.encode(chunk)
            # Ensure embedding is a numpy array and convert to float32
            if not isinstance(emb, np.ndarray):
                emb = np.array(emb)
            embeddings.append(emb.astype('float32'))
    if not embeddings:
        print('No PDF chunks found - ensure pdfs/ has PDF files.')
        return
    # Stack embeddings into a 2D numpy array
    X = np.vstack(embeddings).astype('float32')
    dim = X.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(X)
    faiss.write_index(index, INDEX_PATH)
    with open(META_PATH,'w',encoding='utf8') as f:
        json.dump(metas,f,ensure_ascii=False,indent=2)
    with open(RAW_PATH,'w',encoding='utf8') as f:
        json.dump(raw_map,f,ensure_ascii=False,indent=2)
    print('Ingestion complete:', len(metas),'chunks saved.')

if __name__=='__main__':
    os.makedirs('pdfs', exist_ok=True)
    ingest_pdf_folder('pdfs')
