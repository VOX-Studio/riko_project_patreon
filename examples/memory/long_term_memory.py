import faiss
import os
import pickle
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Optional
from pathlib import Path



class MemoryManager:
    def __init__(self, model_name="all-MiniLM-L12-v2", faiss_path=os.path.join("faiss_cache", "memory.index"), metadata_path=os.path.join("faiss_cache", "memory_meta.pkl")):
        self.embedder = SentenceTransformer(model_name)
        self.faiss_path = faiss_path
        self.metadata_path = metadata_path
        self.dim = self.embedder.get_sentence_embedding_dimension()

        # Ensure cache dir exists
        os.makedirs(os.path.dirname(self.faiss_path), exist_ok=True)

        
        # Initialize or load FAISS index
        if os.path.exists(faiss_path) and os.path.exists(metadata_path):
            self.index = faiss.read_index(faiss_path)
            with open(metadata_path, "rb") as f:
                self.metadata = pickle.load(f)
        else:
            self.index = faiss.IndexFlatL2(self.dim)
            self.metadata = []

    def add_memory(self, text: str, metadata: Optional[dict] = None):
        vector = self.embedder.encode([text])
        self.index.add(np.array(vector).astype("float32"))
        self.metadata.append({
            "text": text,
            "metadata": metadata or {}
        })

    def query(self, text: str, top_k: int = 5) -> List[dict]:
        if self.index.ntotal == 0:
            return []
        
        query_vec = self.embedder.encode([text])
        D, I = self.index.search(np.array(query_vec).astype("float32"), top_k)
        
        results = []
        for idx in I[0]:
            if idx < len(self.metadata):
                results.append(self.metadata[idx])
        return results

    def get_context_block(self, text: str, top_k: int = 5) -> str:
        memories = self.query(text, top_k=top_k)
        if not memories:
            return ""
        lines = [f"- {m['text']}" for m in memories]
        return "Riko Memory:\n" + "\n".join(lines) + "\n"

    def save_index(self):
        faiss.write_index(self.index, self.faiss_path)
        with open(self.metadata_path, "wb") as f:
            pickle.dump(self.metadata, f)


if __name__ == "__main__":
    import time 

    start_time = time.perf_counter()
    memory = MemoryManager()
    end_time = time.perf_counter()

    elapsed_time = end_time - start_time

    print(f"Execution time loading: {elapsed_time:.4f} seconds")


    # # Add memory
    start_time = time.perf_counter()
    memory.add_memory("Rayen's favourite foods are 1.Sushi, 2.His own hand pulled wide noodles, 3. free food from other people.")
    memory.add_memory("Rayen likes to earn money with zero effort")
    memory.add_memory("Rayen is rated 1700 on chess.com")
    memory.add_memory("Rayen is gold DPS player on overwatch")
    memory.add_memory("Rayen's favorite anime is code geass.")

    memory.save_index()
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time

    print(f"Execution time adding memeory: {elapsed_time:.4f} seconds")

    # On new message
    query = ["what anime does rayen like?", "what game does rayen play?", "does rayen like mecha anime?", "what's rayen's overwatch rank?"]

    q = "what is rayen's chess rating?"
    context = memory.get_context_block(q)
    print(context)


    for q in query:
        # print("QUERY:", q, "\n")
        # start_time = time.perf_counter()
        # context = memory.get_context_block(q)
        # end_time = time.perf_counter()
        # elapsed_time = end_time - start_time
        # print(context)
        # print(f"Execution time: {elapsed_time:.4f} seconds")
        

        q = "what is rayen's chess rating?"
        context = memory.get_context_block(q)
