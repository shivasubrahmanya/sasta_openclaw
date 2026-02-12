import subprocess
import os
from typing import Callable, Dict, Any, List
from utils.permissions import check_permission

class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, Callable] = {}

    def register(self, func: Callable):
        """Decorator to register a tool."""
        self.tools[func.__name__] = func
        return func

    def get_tools(self) -> List[Callable]:
        return list(self.tools.values())
    
    def get_tool(self, name: str) -> Callable:
        return self.tools.get(name)

# Global registry instance
registry = ToolRegistry()

# Global memory store instance
_memory_store = None

def set_memory_store(store):
    global _memory_store
    _memory_store = store

@registry.register
def run_command(command: str) -> str:
    """
    Executes a shell command and returns the output.
    
    Args:
        command: The command to execute.
    """
    if not check_permission(command):
        return f"Permission Denied: Command '{command}' is not allowed."

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        return f"Output:\n{result.stdout}\nError:\n{result.stderr}"
    except Exception as e:
        return f"Error executing command: {e}"

@registry.register
def read_file(filepath: str) -> str:
    """
    Reads the content of a file.
    
    Args:
        filepath: The path to the file to read.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"

@registry.register
def write_file(filepath: str, content: str) -> str:
    """
    Writes content to a file. Overwrites if exists.
    
    Args:
        filepath: The path to the file to write.
        content: The content to write.
    """
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote to {filepath}"
    except Exception as e:
        return f"Error writing file: {e}"

@registry.register
def web_search(query: str) -> str:
    """
    Performs a web search.
    
    Args:
        query: The search query.
    """
    # Placeholder for actual search implementation (e.g., using Google Search API or similar)
    return f"Mock search result for: {query}"

@registry.register
def save_memory(content: str) -> str:
    """
    Saves a memory to long-term storage.
    
    Args:
        content: The text content to save.
    """
    if _memory_store:
        try:
            _memory_store.add_memory(content)
            return "Memory saved successfully."
        except Exception as e:
            return f"Error saving memory: {e}"
    return "Memory store not configured."

@registry.register
def memory_search(query: str) -> str:
    """
    Searches long-term memory.
    
    Args:
        query: The search query.
    """
    if _memory_store:
        try:
            result = _memory_store.search_memory(query)
            return f"Found memory: {result}" if result else "No relevant memories found."
        except Exception as e:
            return f"Error searching memory: {e}"
    return "Memory store not configured."
