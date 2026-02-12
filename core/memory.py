import chromadb
import google.generativeai as genai
import os
from chromadb.utils import embedding_functions

class GoogleGenerativeAIEmbeddingFunction(embedding_functions.EmbeddingFunction):
    def __init__(self, api_key: str, model_name: str = "models/gemini-embedding-001"):
        self.api_key = api_key
        self.model_name = model_name
        genai.configure(api_key=api_key)

    def __call__(self, input: list) -> list:
        # returns a list of embeddings
        # Gemini batch embed API might be different, let's stick to simple loop or single call wrapper
        # The official python SDK supports embed_content(model=..., content=...)
        # We need to handle input list.
        embeddings = []
        for text in input:
            try:
                result = genai.embed_content(
                    model=self.model_name,
                    content=text,
                    task_type="retrieval_document"
                )
                embeddings.append(result['embedding'])
            except Exception as e:
                print(f"Error embedding text '{text[:50]}...': {e}")
                # Fallback to zero vector or handle appropriately
                pass 
        return embeddings

class MemoryStore:
    def __init__(self, memory_dir: str, api_key: str):
        self.client = chromadb.PersistentClient(path=memory_dir)
        self.embedding_fn = GoogleGenerativeAIEmbeddingFunction(api_key=api_key)
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
        return results['documents'][0] if results['documents'] else []
