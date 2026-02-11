"""
Semantic Search Module - agent/semantic_search.py

Indexes: lore/*.md + brain.db episodes + semantic/*.md
Embeddings: nomic-embed-text-v1.5.Q8_0.gguf (llama-cpp-python)
Storage: FAISS index + numpy pickle fallback
"""

import os
import sys
import json
import pickle
import sqlite3
import numpy as np

# Pre-load llama_cpp with suppressed logging to avoid C++ warnings
_Llama = None
_log_callback_ref = None  # Keep reference to prevent GC

def _get_llama():
    global _Llama, _log_callback_ref
    if _Llama is None:
        # Set up no-op log callback to suppress C++ warnings
        from llama_cpp import llama_log_set
        import ctypes
        
        # Create callback type and function
        CB_TYPE = ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_char_p)
        
        def _noop_log_callback(level, text):
            pass
        
        # Keep reference alive (convert to C callable)
        _log_callback_ref = CB_TYPE(_noop_log_callback)
        llama_log_set(_log_callback_ref, None)
        
        from llama_cpp import Llama
        _Llama = Llama
    return _Llama

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "brain.db")
INDEX_PATH = os.path.join(SCRIPT_DIR, "semantic.index")
CHUNKS_PATH = os.path.join(SCRIPT_DIR, "semantic_chunks.json")

class SemanticSearch:
    def __init__(self):
        self.encoder = None
        self.index = None
        self.chunks = []  # (source, text) tuples
        self.dimension = 768  # nomic-embed-text-v1.5 dimension
        self.model_path = os.path.join(os.path.dirname(SCRIPT_DIR), "data", "nomic-embed-text-v1.5.Q8_0.gguf")
        self._load_encoder()
        self._load_or_build_index()
    
    def _load_encoder(self):
        """Load llama-cpp-python model or None if not available."""
        try:
            if os.path.exists(self.model_path):
                Llama = _get_llama()
                self.encoder = Llama(
                    model_path=self.model_path,
                    embedding=True,
                    n_ctx=2048,
                    verbose=False
                )
                #print(f"[SemanticSearch] Loaded nomic-embed-text-v1.5.Q8_0.gguf")
            else:
                print(f"[SemanticSearch] Warning: Model not found at {self.model_path}")
                self.encoder = None
        except ImportError as e:
            print(f"[SemanticSearch] Warning: llama-cpp-python not installed ({e}). Using fallback.")
            self.encoder = None
    
    def _embed(self, texts):
        """Encode texts to vectors using llama-cpp-python."""
        if self.encoder:
            # llama-cpp creates embeddings - returns list of floats for single text
            embeddings = []
            for text in texts:
                # Nomic embeddings work best with 'search_document' or 'search_query' prefixes
                embedding = self.encoder.embed(text, normalize=True)
                embeddings.append(embedding)
            return np.array(embeddings, dtype='float32')
        else:
            # Fallback: random vectors (for testing without model)
            return np.random.randn(len(texts), self.dimension).astype('float32')
    
    def _load_or_build_index(self):
        """Load existing FAISS index or build from scratch."""
        if os.path.exists(INDEX_PATH) and os.path.exists(CHUNKS_PATH):
            self._load_index()
        else:
            self.build_index()
    
    def _load_index(self):
        """Load FAISS index and chunks mapping."""
        # Check if dimension matches current model (768 for nomic)
        dimension_mismatch = False
        try:
            import faiss
            temp_index = faiss.read_index(INDEX_PATH)
            if temp_index.d != self.dimension:
                print(f"[SemanticSearch] Dimension mismatch: index={temp_index.d}, model={self.dimension}. Rebuilding...")
                dimension_mismatch = True
            else:
                self.index = temp_index
                with open(CHUNKS_PATH, 'r', encoding='utf-8') as f:
                    self.chunks = json.load(f)
        except Exception as e:
            print(f"[SemanticSearch] Could not load FAISS index: {e}")
            dimension_mismatch = True
        
        if dimension_mismatch:
            # Rebuild index with new dimension
            self.build_index()
    
    def _collect_all_chunks(self):
        """Collect text from all sources."""
        chunks = []
        
        # 1. Lore files (semantic memory)
        lore_files = {
            "lore/self": "agent/lore/self.md",
            "lore/user": "agent/lore/user.md",
            "lore/relationship": "agent/lore/relationship.md",
        }
        for source, path in lore_files.items():
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    text = f.read().strip()
                    if text:
                        chunks.append((source, text))
        
        # 2. Semantic memory
        sem_path = "memory/semantic/memory.md"
        if os.path.exists(sem_path):
            with open(sem_path, 'r', encoding='utf-8') as f:
                text = f.read().strip()
                if text:
                    chunks.append(("semantic/memory", text))
        
        # 3. Episodes from SQLite
        if os.path.exists(DB_PATH):
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT content, filename FROM episodes LIMIT 1000")
            for row in cursor.fetchall():
                content, filename = row
                if content:
                    chunks.append((f"episode/{filename}", content))
            conn.close()
        
        return chunks
    
    def build_index(self):
        """Build FAISS index from all sources."""
        print("[SemanticSearch] Building index...")
        self.chunks = self._collect_all_chunks()
        
        if not self.chunks:
            print("[SemanticSearch] Warning: No chunks found to index")
            return
        
        texts = [chunk[1] for chunk in self.chunks]
        vectors = self._embed(texts)
        
        # Normalize for cosine similarity
        vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
        vectors = vectors.astype('float32')
        
        # Build FAISS index
        try:
            import faiss
            self.index = faiss.IndexFlatIP(self.dimension)  # Inner product = cosine for normalized vectors
            self.index.add(vectors)
            faiss.write_index(self.index, INDEX_PATH)
        except Exception as e:
            print(f"[SemanticSearch] FAISS error ({e}), using numpy fallback")
            # Fallback: save numpy array
            self.index = vectors
            with open(INDEX_PATH + '.npy', 'wb') as f:
                pickle.dump(vectors, f)
        
        # Save chunks mapping
        with open(CHUNKS_PATH, 'w', encoding='utf-8') as f:
            json.dump(self.chunks, f, ensure_ascii=False)
        
        print(f"[SemanticSearch] Built index with {len(self.chunks)} chunks")
    
    def search(self, query, k=5):
        """
        Semantic search: find top-k most similar chunks.
        Returns list of (source, text, score) tuples.
        """
        if not self.chunks:
            return []
        
        # Embed query
        query_vec = self._embed([query])
        query_vec = query_vec / np.linalg.norm(query_vec)
        query_vec = query_vec.astype('float32')
        
        # Search
        try:
            import faiss
            scores, indices = self.index.search(query_vec, k)
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx >= 0 and idx < len(self.chunks):
                    source, text = self.chunks[idx]
                    results.append((source, text, float(score)))
            return results
        except ImportError:
            # Fallback: brute force cosine similarity
            query_vec = query_vec[0]
            vectors = self.index  # numpy array
            scores = np.dot(vectors, query_vec)
            top_k_idx = np.argsort(scores)[-k:][::-1]
            results = []
            for idx in top_k_idx:
                source, text = self.chunks[idx]
                results.append((source, text, float(scores[idx])))
            return results

# Singleton instance
_search_instance = None

def get_search():
    """Get or create singleton SemanticSearch instance."""
    global _search_instance
    if _search_instance is None:
        _search_instance = SemanticSearch()
    return _search_instance

def search(query, k=5):
    """Convenience function for semantic search."""
    return get_search().search(query, k=k)

def add_chunk_to_index(text: str, source: str = "summarizer"):
    """
    Stage 3: Add a single new chunk to the semantic index in real-time.
    Called after summarization to immediately make compressed_memory searchable.
    
    Args:
        text: The compressed_memory sentence
        source: Source identifier (default: 'summarizer')
        
    Returns:
        bool: True if successful
    """
    search_instance = get_search()
    
    # 1. Generate embedding using all-MiniLM-L6-v2
    print(f"[SemanticSearch] Generating embedding for new chunk...")
    vector = search_instance._embed([text])
    vector = vector / np.linalg.norm(vector, axis=1, keepdims=True)
    vector = vector.astype('float32')
    
    # 2. Append to semantic_chunks.json
    new_chunk = (source, text)
    search_instance.chunks.append(new_chunk)
    
    with open(CHUNKS_PATH, 'w', encoding='utf-8') as f:
        json.dump(search_instance.chunks, f, ensure_ascii=False)
    
    # 3. Update FAISS index (semantic.index)
    try:
        import faiss
        if search_instance.index is None:
            # Create new index if doesn't exist
            search_instance.index = faiss.IndexFlatIP(search_instance.dimension)
        search_instance.index.add(vector)
        faiss.write_index(search_instance.index, INDEX_PATH)
        print(f"[SemanticSearch] Added chunk. Total: {len(search_instance.chunks)}")
    except ImportError:
        # Fallback: rebuild numpy index
        print("[SemanticSearch] FAISS not available, rebuilding numpy index...")
        search_instance.build_index()
    
    return True


def rebuild_index():
    """Rebuild the semantic index from scratch."""
    return get_search().build_index()
