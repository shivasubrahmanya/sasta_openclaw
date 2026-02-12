import os
import sys
import time
import argparse
from config import Config
from core.session import SessionStore
from core.gemini import GeminiClient
from core.memory import MemoryStore
from core.agent import GeminiAgent
from core.scheduler import Scheduler
from core.tools import set_memory_store
from gateways.telegram_bot import TelegramGateway
from gateways.http_api import HttpGateway

def main():
    # Parse Command Line Arguments
    parser = argparse.ArgumentParser(description="Gemini Gateway")
    parser.add_argument("--model", type=str, default=Config.GEMINI_MODEL, help="Gemini Model to use")
    args = parser.parse_args()

    print(f"Starting Gemini Gateway with model: {args.model}...")
    
    # Validate configuration
    try:
        Config.validate()
    except Exception as e:
        print(f"Configuration Error: {e}")
        sys.exit(1)

    # Ensure directories exist
    os.makedirs(Config.SESSION_DIR, exist_ok=True)
    os.makedirs(Config.MEMORY_DIR, exist_ok=True)

    # Initialize Core Components
    session_store = SessionStore(Config.SESSION_DIR)
    
    # Initialize Memory Store
    try:
        memory_store = MemoryStore(Config.MEMORY_DIR, Config.GOOGLE_API_KEY)
        set_memory_store(memory_store) # Inject into tools
        print("Memory Store initialized.")
    except Exception as e:
        print(f"Warning: Could not initialize Memory Store: {e}")
        memory_store = None

    # Initialize Gemini Client with system instruction to enforce tool usage
    system_instruction = """You are Gemini Gateway, a helpful AI assistant with access to tools.

IMPORTANT RULES:
- When asked to create, write, or modify files, you MUST use the write_file tool. Do NOT just describe what you would do.
- When asked to read files, you MUST use the read_file tool.
- When asked to run commands, you MUST use the run_command tool.
- When asked to save or search memories, use the save_memory and memory_search tools.
- Always use the actual tools provided to you. Never pretend or hallucinate that you performed an action.
- If you cannot perform a task (e.g., playing music on Spotify), clearly explain that you don't have a tool for that.
- For file paths on Windows, use backslash paths like C:\\Users\\... or relative paths like .\\filename.txt"""

    gemini_client = GeminiClient(Config.GOOGLE_API_KEY, model_name=args.model, system_instruction=system_instruction)
    
    # Initialize Agent
    agent = GeminiAgent(session_store, gemini_client, memory_store)
    
    # Initialize Scheduler
    if Config.SCHEDULER_ENABLED:
        scheduler = Scheduler()
        scheduler.start()
        # Example job: Morning briefing (placeholder)
        # scheduler.add_job("08:00", lambda: print("Morning briefing job triggered!"))

    # Initialize Gateways
    gateways = []
    
    # HTTP Gateway
    http_gateway = HttpGateway(Config.GATEWAY_PORT, agent.process_message)
    http_gateway.start()
    gateways.append(http_gateway)

    # Telegram Gateway
    if Config.TELEGRAM_BOT_TOKEN and ":" in Config.TELEGRAM_BOT_TOKEN:
        try:
            telegram_gateway = TelegramGateway(Config.TELEGRAM_BOT_TOKEN, agent.process_message)
            telegram_gateway.start()
            gateways.append(telegram_gateway)
        except Exception as e:
            print(f"Error initializing Telegram Gateway: {e}")
            print("Continuing without Telegram support.")
    elif Config.TELEGRAM_BOT_TOKEN:
         print(f"Warning: Invalid Telegram token format: {Config.TELEGRAM_BOT_TOKEN[:10]}...")
         print("Continuing without Telegram support.")

    print("Gemini Gateway is running. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping Gemini Gateway...")
        for gateway in gateways:
            gateway.stop()
        if Config.SCHEDULER_ENABLED:
            scheduler.stop()
        print("Goodbye!")

if __name__ == "__main__":
    main()
