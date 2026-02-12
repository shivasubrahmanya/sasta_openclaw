import json
import os
import time
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

class Message(BaseModel):
    role: str
    content: str
    timestamp: float = Field(default_factory=time.time)
    metadata: Optional[Dict[str, Any]] = None

class Session(BaseModel):
    session_id: str
    history: List[Message] = []
    metadata: Dict[str, Any] = {}
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        msg = Message(role=role, content=content, metadata=metadata)
        self.history.append(msg)
        return msg

    def to_gemini_history(self):
        # Maps internal role 'assistant' to Gemini's 'model' if needed, though Gemini uses 'model'
        # The API usually expects 'user' and 'model'.
        gemini_history = []
        for m in self.history:
            role = "model" if m.role == "assistant" else m.role
            gemini_history.append({"role": role, "parts": [m.content]})
        return gemini_history

class SessionStore:
    def __init__(self, session_dir: str):
        self.session_dir = session_dir
        os.makedirs(session_dir, exist_ok=True)
    
    def _get_path(self, session_id: str) -> str:
        # Sanitize session_id to prevent path traversal
        safe_id = "".join([c for c in session_id if c.isalnum() or c in ('-','_')])
        return os.path.join(self.session_dir, f"{safe_id}.jsonl")

    def load_session(self, session_id: str) -> Session:
        path = self._get_path(session_id)
        if not os.path.exists(path):
            return Session(session_id=session_id)
        
        history = []
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            data = json.loads(line)
                            history.append(Message(**data))
                        except json.JSONDecodeError:
                            print(f"Skipping invalid JSON line in session {session_id}")
                            continue 
        except Exception as e:
            print(f"Error loading session {session_id}: {e}")
            
        return Session(session_id=session_id, history=history)

    def save_message(self, session_id: str, message: Message):
        path = self._get_path(session_id)
        try:
            with open(path, 'a', encoding='utf-8') as f:
                f.write(message.model_dump_json() + "\n")
        except Exception as e:
            print(f"Error saving message to session {session_id}: {e}")
