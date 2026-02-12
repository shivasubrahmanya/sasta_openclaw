import google.generativeai as genai
from core.session import Session, Message
from core.tools import registry
import os

class GeminiClient:
    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash", system_instruction: str = None):
        if not api_key:
            raise ValueError("API Key is required for GeminiClient")
        
        genai.configure(api_key=api_key)
        
        # Initialize model with tools from registry
        # We need to convert our registry tools to a list of functions/tools for Gemini
        # For now, we assume simple function passing works (Gemini Python SDK handles this)
        self.tools = registry.get_tools()
        
        self.model = genai.GenerativeModel(
            model_name=model_name,
            tools=self.tools if self.tools else None,
            system_instruction=system_instruction
        )

    def send_message(self, session: Session, content: str) -> str:
        """
        Sends a message to Gemini within the context of a session.
        Handles history conversion and response processing.
        Updates the session with the user message and model response.
        """
        
        # 1. Add user message to session
        session.add_message(role="user", content=content)
        
        # 2. Prepare history for Gemini
        # Gemini's start_chat expects history to NOT include the potential new message if we use send_message
        # But if we use generate_content, we pass everything.
        # Let's use start_chat to get a chat session initialized with previous history.
        
        # Convert persistent history to Gemini format (excluding the just-added message for start_chat?)
        # Actually start_chat(history=...) initializes the state.
        # We should accept that start_chat expects the history *before* the new message.
        
        previous_history = session.to_gemini_history()[:-1] # Exclude the user message we just added
        
        chat = self.model.start_chat(history=previous_history, enable_automatic_function_calling=True)
        
        try:
            response = chat.send_message(content)
            
            response_text = response.text
            
            # Add model response to session
            session.add_message(role="assistant", content=response_text)
            
            return response_text
            
        except Exception as e:
            error_msg = f"Error communicating with Gemini: {e}"
            print(error_msg)
            return "I encountered an error processing your request."

