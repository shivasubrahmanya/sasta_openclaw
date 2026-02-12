from abc import ABC, abstractmethod
from typing import Callable, Any

class Gateway(ABC):
    def __init__(self, on_message: Callable[[str, str], str]):
        """
        Initialize the gateway.
        
        Args:
            on_message: A callback function that takes (session_id, user_message) 
                        and returns the assistant's response.
        """
        self.on_message = on_message

    @abstractmethod
    def start(self):
        """Start the gateway listener."""
        pass

    @abstractmethod
    def stop(self):
        """Stop the gateway listener."""
        pass
