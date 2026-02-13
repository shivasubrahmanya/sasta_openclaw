from google import genai
from google.genai import types
from core.session import Session, Message
from core.tools import registry
import os


class GeminiClient:
    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash", system_instruction: str = None):
        if not api_key:
            raise ValueError("API Key is required for GeminiClient")
        
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        self.system_instruction = system_instruction
        
        # Get tools from registry
        self.tools = registry.get_tools()

    def send_message(self, session: Session, content: str) -> str:
        """
        Sends a message to Gemini within the context of a session.
        Handles history conversion and response processing.
        Updates the session with the model response.
        Permissions check: assumed done by tools.
        """
        
        # 1. Prepare history
        # The user message is ALREADY in the session (added by Agent).
        # We need to send everything *except* the last message (which is the new user message) as history,
        # and send the last message as the new content.
        # core.session.to_gemini_history() converts the whole history.
        
        full_gemini_history = session.to_gemini_history()
        
        # If this is the very first message, history is empty for the API call, content is the message.
        # If history has [User1, Model1, User2], we send history=[User1, Model1] and content=User2.
        
        if len(full_gemini_history) > 1:
            api_history = full_gemini_history[:-1]
        else:
            api_history = []
            
        # The content to send is technically the last message in the session, 
        # but the method signature takes `content`. We should verify they match or just use `content`.
        # For safety/consistency with the Agent calling convention, we use `content`.
        
        # 2. Build config with tools and system instruction
        config = types.GenerateContentConfig(
            tools=self.tools if self.tools else None,
            system_instruction=self.system_instruction,
        )
        
        # 3. Create chat and send message
        chat = self.client.chats.create(
            model=self.model_name,
            history=api_history,
            config=config,
        )
        
        try:
            response = chat.send_message(content)
            
            response_text = response.text
            
            # Add model response to session
            session.add_message(role="assistant", content=response_text)
            
            return response_text
            
        except Exception as e:
            error_msg = f"Error communicating with Gemini: {e}"
            print(error_msg)
            
            # Add error message to session so state doesn't get desynced (User said something, Assistant needs to reply)
            fallback_response = "I encountered an error processing your request."
            session.add_message(role="assistant", content=f"{fallback_response} (Debug: {e})")
            
            return fallback_response
