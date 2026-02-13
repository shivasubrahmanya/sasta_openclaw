from core.session import SessionStore, Session
from core.ollama_client import OllamaClient
from core.memory import MemoryStore
from core.tools import registry

class GeminiAgent:
    def __init__(self, session_store: SessionStore, gemini_client: OllamaClient, memory_store: MemoryStore = None):
        self.session_store = session_store
        self.gemini_client = gemini_client
        self.memory_store = memory_store

    def process_message(self, session_id: str, user_message: str) -> str:
        # 1. Load Session
        session = self.session_store.load_session(session_id)
        
        # 2. Retrieve Memory (if enabled)
        if self.memory_store:
            try:
                # We search for relevant context based on user message
                relevant_context = self.memory_store.search_memory(user_message)
                if relevant_context:
                    print(f"Injecting memory: {relevant_context[:50]}...")
                    user_message_with_context = f"Context: {relevant_context}\n\nUser: {user_message}"
                else:
                    user_message_with_context = user_message
            except Exception as e:
                print(f"Memory retrieval failed: {e}")
                user_message_with_context = user_message
        else:
            user_message_with_context = user_message

        # 3. Add User Message to Session and Save to Disk IMMEDIATELY
        # This prevents loss if the API call crashes
        user_msg = session.add_message(role="user", content=user_message_with_context)
        self.session_store.save_message(session_id, user_msg)

        # 4. Get Response from Gemini
        response_text = self.gemini_client.send_message(session, user_message_with_context)
        
        # 5. Save Assistant Message to Disk
        # We check the last message in history. If send_message worked, it should be the assistant response.
        if session.history and session.history[-1].role == "assistant":
            self.session_store.save_message(session_id, session.history[-1])
            
        return response_text
