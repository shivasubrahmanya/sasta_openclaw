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
        Handles history conversion, multi-round tool calls, and response processing.
        """
        
        MAX_TOOL_ROUNDS = 3  # Prevent infinite tool call loops
        
        # 1. Prepare history for Ollama
        messages = []
        
        # Add system instruction if present
        if self.system_instruction:
            messages.append({"role": "system", "content": self.system_instruction})
            
        # Convert session history
        for msg in session.history:
            role = msg.role
            if role == "model": role = "assistant"
            messages.append({"role": role, "content": msg.content})
        
        # 2. Call Ollama with tool call loop
        try:
            round_num = 0
            
            while round_num <= MAX_TOOL_ROUNDS:
                # Decide whether to offer tools this round
                # On the last round, don't offer tools to force a text response
                use_tools = self.tools if round_num < MAX_TOOL_ROUNDS else None
                
                print(f"DEBUG: Calling Ollama (round {round_num + 1}/{MAX_TOOL_ROUNDS + 1}, tools={'yes' if use_tools else 'no'})...")
                
                import time as _time
                _start = _time.time()
                response = ollama.chat(
                    model=self.model_name,
                    messages=messages,
                    tools=use_tools
                )
                _elapsed = _time.time() - _start
                
                response_msg = response['message']
                response_content = response_msg.get('content', '') or ''
                tool_calls = response_msg.get('tool_calls', []) or []
                
                print(f"DEBUG: Ollama responded in {_elapsed:.1f}s — content={len(response_content)} chars, tool_calls={len(tool_calls)}")

                # If no tool calls, we have our final answer
                if not tool_calls:
                    final_content = response_content or "I processed the request but have no additional response."
                    print(f"DEBUG: Final response: {final_content[:200]}...")
                    session.add_message(role="assistant", content=final_content)
                    return final_content

                # Execute tool calls
                messages.append(response_msg)
                
                for tool in tool_calls:
                    function_name = tool['function']['name']
                    arguments = tool['function']['arguments']
                    
                    print(f"DEBUG: Tool Call (round {round_num + 1}): {function_name}({arguments})")
                    
                    func = registry.get_tool(function_name)
                    if func:
                        try:
                            result = func(**arguments)
                        except Exception as e:
                            result = f"Error executing tool {function_name}: {e}"
                    else:
                        result = f"Error: Tool {function_name} not found."
                    
                    # Truncate large tool results to prevent Ollama from choking
                    result_str = str(result)
                    if len(result_str) > 4000:
                        print(f"DEBUG: Truncating tool result from {len(result_str)} to 4000 chars")
                        result_str = result_str[:4000] + "\n\n[... truncated for length. Present the above results to the user.]"
                    
                    messages.append({
                        "role": "tool",
                        "content": result_str,
                    })
                
                round_num += 1
            
            # If we exhausted all rounds, force a text-only final call
            print(f"DEBUG: Max tool rounds exhausted, forcing text-only response...")
            messages.append({
                "role": "system",
                "content": "You must now respond to the user with the information gathered. Do not call any more tools."
            })
            
            final_response = ollama.chat(
                model=self.model_name,
                messages=messages
                # No tools parameter = model can only respond with text
            )
            final_content = final_response['message'].get('content', '')
            print(f"DEBUG: Forced final response: {len(final_content)} chars")
            
            if not final_content:
                # Last resort: synthesize from tool results
                tool_results = [m['content'] for m in messages if m.get('role') == 'tool']
                final_content = "\n\n".join(tool_results[-2:]) if tool_results else "I processed the request but couldn't generate a summary."
                print(f"DEBUG: Using last-resort tool result passthrough ({len(final_content)} chars)")
            
            session.add_message(role="assistant", content=final_content)
            return final_content

        except Exception as e:
            error_msg = f"Error communicating with Ollama: {e}"
            print(error_msg)
            fallback = "I encountered an error communicating with my local brain."
            session.add_message(role="assistant", content=f"{fallback} (Debug: {e})")
            return fallback
