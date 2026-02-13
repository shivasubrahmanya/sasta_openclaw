import chromadb
import ollama
import os
from chromadb.utils import embedding_functions

class OllamaEmbeddingFunction(embedding_functions.EmbeddingFunction):
    def __init__(self, model_name: str = "llama3.1"):
        self.model_name = model_name

    def __call__(self, input: list) -> list:
        # returns a list of embeddings
        embeddings = []
        for text in input:
            try:
                response = ollama.embeddings(model=self.model_name, prompt=text)
                embeddings.append(response["embedding"])
            except Exception as e:
                print(f"Error embedding text '{text[:50]}...': {e}")
                pass 
        return embeddings

class MemoryStore:
    def __init__(self, memory_dir: str, model_name: str = "llama3.1"):
        self.client = chromadb.PersistentClient(path=memory_dir)
        self.embedding_fn = OllamaEmbeddingFunction(model_name=model_name)
        self.collection = self.client.get_or_create_collection(
            name="long_term_memory",
            embedding_function=self.embedding_fn
        )

    def add_memory(self, text: str, metadata: dict = None):
        if not text:
            return
        
        # Simple ID generation
        import uuid
        memory_id = str(uuid.uuid4())
        
        self.collection.add(
            documents=[text],
            metadatas=[metadata or {}],
            ids=[memory_id]
        )

    def search_memory(self, query: str, n_results: int = 3):
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        # Flatten results
        # Check if we have results
        if results['documents'] and len(results['documents'][0]) > 0:
            return results['documents'][0][0]
        return None
