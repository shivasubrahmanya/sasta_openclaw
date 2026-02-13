import ollama
from core.session import Session, Message
from core.tools import registry
import inspect
import json
from typing import List, Dict, Any

class OllamaClient:
    def __init__(self, base_url: str, model_name: str = "llama3.1", system_instruction: str = None):
        self.base_url = base_url
        self.model_name = model_name
        self.system_instruction = system_instruction
        
        # Configure the global ollama client if needed, or we just use the module level functions
        # which default to localhost:11434. If base_url is different, we might need to set it.
        # The ollama python library checks OLLAMA_HOST env var.
        
        # Get tools from registry and convert to Ollama/Llama 3.1 format
        self.tools = self._convert_tools(registry.get_tools())

    def _convert_tools(self, tools: List[Any]) -> List[Dict]:
        """
        Converts Python functions to Ollama tool definitions (JSON Schema).
        """
        ollama_tools = []
        for func in tools:
            sig = inspect.signature(func)
            doc = inspect.getdoc(func) or "No description provided."
            
            tool_def = {
                "type": "function",
                "function": {
                    "name": func.__name__,
                    "description": doc,
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
            
            for param_name, param in sig.parameters.items():
                param_type = "string" # Default to string for simplicity, can be inferred
                if param.annotation == int:
                    param_type = "integer"
                elif param.annotation == bool:
                    param_type = "boolean"
                elif param.annotation == float:
                    param_type = "number"
                
                tool_def["function"]["parameters"]["properties"][param_name] = {
                    "type": param_type,
                    "description": f"Parameter {param_name}" 
                    # We could parse docstrings for param descriptions if needed
                }
                
                if param.default == inspect.Parameter.empty:
                    tool_def["function"]["parameters"]["required"].append(param_name)
            
            ollama_tools.append(tool_def)
        return ollama_tools

    def send_message(self, session: Session, content: str) -> str:
        """
        Sends a message to Ollama within the context of a session.
        Handles history conversion, tool calls, and response processing.
        """
        
        # 1. Prepare history for Ollama
        messages = []
        
        # Add system instruction if present
        if self.system_instruction:
            messages.append({"role": "system", "content": self.system_instruction})
            
        # Convert session history
        # Session history contains objects with .role and .content
        for msg in session.history:
            role = msg.role
            if role == "model": role = "assistant" # Remap if needed
            messages.append({"role": role, "content": msg.content})
            
        # Add the current user message (which is passed as 'content' arg, 
        # but might also be in session history depending on how Agent calls this.
        # The Agent ADDS the user message to session BEFORE calling this.
        # So 'session.history' ALREADY contains the last user message.
        # We don't need to append 'content' again if it's already in history.
        
        # 2. Call Ollama
        try:
            response = ollama.chat(
                model=self.model_name,
                messages=messages,
                tools=self.tools
            )
            
            response_msg = response['message']
            response_content = response_msg.get('content', '')
            tool_calls = response_msg.get('tool_calls', [])

            # 3. Handle Tool Calls
            if tool_calls:
                # If tools are called, we execute them and send results back
                
                # First, add the assistant's request-to-call-tool to history
                # For Ollama chat, we usually just continue the conversation
                messages.append(response_msg)
                
                # Execute tools
                for tool in tool_calls:
                    function_name = tool['function']['name']
                    arguments = tool['function']['arguments']
                    
                    print(f"DEBUG: Tool Call: {function_name}({arguments})")
                    
                    func = registry.get_tool(function_name)
                    if func:
                        try:
                            # Arguments come as a dict, we unpack them
                            result = func(**arguments)
                        except Exception as e:
                            result = f"Error executing tool {function_name}: {e}"
                    else:
                        result = f"Error: Tool {function_name} not found."
                        
                    # Add tool result to history
                    messages.append({
                        "role": "tool",
                        "content": str(result),
                        # Some implementations might need name/tool_call_id
                    })
                    
                # 4. Get final response after tool execution
                final_response = ollama.chat(
                    model=self.model_name,
                    messages=messages,
                    # We don't verify if we should pass tools again for multi-step, 
                    # but usually yes for chained tools. Llama 3 is good at one-shot.
                    tools=self.tools 
                )
                final_content = final_response['message']['content']
                
                # Update Session with the FINAL answer provided to user
                session.add_message(role="assistant", content=final_content)
                return final_content

            else:
                # No tools called, just a normal response
                session.add_message(role="assistant", content=response_content)
                return response_content
            
        except Exception as e:
            error_msg = f"Error communicating with Ollama: {e}"
            print(error_msg)
            fallback = "I encountered an error communicating with my local brain."
            session.add_message(role="assistant", content=f"{fallback} (Debug: {e})")
            return fallback
