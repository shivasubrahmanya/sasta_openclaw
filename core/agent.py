from core.session import SessionStore, Session
from core.gemini import GeminiClient
from core.memory import MemoryStore
from core.tools import registry

class GeminiAgent:
    def __init__(self, session_store: SessionStore, gemini_client: GeminiClient, memory_store: MemoryStore = None):
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
                    # In a real system, we'd inject this via system instruction update or specific message structure.
                    # For now, we append it to the user message with a delimiter, 
                    # invisible to the 'user' role ideally, but here we just prepend context.
                    print(f"Injecting memory: {relevant_context[:50]}...")
                    # We don't want to save the augmented message as the *user's* message in history strictly speaking,
                    # but for simplicity we will. Or we can pass it as a separate 'system' part if Gemini supports it per-turn.
                    # Let's just prepend to user content for now.
                    user_message_with_context = f"Context: {relevant_context}\n\nUser: {user_message}"
                else:
                    user_message_with_context = user_message
            except Exception as e:
                print(f"Memory retrieval failed: {e}")
                user_message_with_context = user_message
        else:
            user_message_with_context = user_message

        # 3. Get Response from Gemini
        # gemini_client.send_message handles adding user/model messages to the session object
        response_text = self.gemini_client.send_message(session, user_message_with_context)
        
        # 4. Save Session updates to disk
        # We know GeminiClient adds 2 messages (User + Model)
        # We need to save them.
        # Since SessionStore.save_message appends, we can just save the new ones.
        # However, to be safe and robust against crashes during send_message, 
        # we should probably have saved the user message *before* calling generate, 
        # and the assistant message *after*. 
        # But GeminiClient handles the addition.
        
        # Let's save the last 2 messages from history.
        if len(session.history) >= 2:
            self.session_store.save_message(session_id, session.history[-2]) # User
            self.session_store.save_message(session_id, session.history[-1]) # Assistant
            
        return response_text
