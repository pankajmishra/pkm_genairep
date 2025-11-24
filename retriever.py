import faiss, json, numpy as np
from sentence_transformers import SentenceTransformer

INDEX_PATH = "faiss_index.bin"
META_PATH = "faiss_meta.json"
RAW_PATH = "faiss_raw.json"
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"

class Retriever:
    def __init__(self):
        self.model = SentenceTransformer(EMBED_MODEL_NAME)
        self.index = faiss.read_index(INDEX_PATH)
        with open(META_PATH,'r',encoding='utf8') as f:
            self.metas = json.load(f)
        with open(RAW_PATH,'r',encoding='utf8') as f:
            self.raw = json.load(f)

    def retrieve(self, query, top_k=4):
        q_emb = self.model.encode(query)
        # Ensure embedding is a numpy array and convert to float32
        if not isinstance(q_emb, np.ndarray):
            q_emb = np.array(q_emb)
        q_emb = q_emb.astype('float32')
        D,I = self.index.search(np.expand_dims(q_emb,axis=0), top_k)
        results=[]
        for idx in I[0]:
            meta = self.metas[idx].copy()
            meta['text'] = self.raw.get(meta['id'], meta.get('text_preview',''))
            results.append(meta)
        return results
