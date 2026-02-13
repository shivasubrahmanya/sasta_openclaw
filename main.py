import os
import sys
import time
import argparse
from config import Config
from core.session import SessionStore
from core.ollama_client import OllamaClient
from core.memory import MemoryStore
from core.agent import GeminiAgent
from core.scheduler import Scheduler
from core.tools import set_memory_store
from gateways.telegram_bot import TelegramGateway
from gateways.http_api import HttpGateway

def main():
    # Parse Command Line Arguments
    parser = argparse.ArgumentParser(description="Gemini Gateway (Ollama Edition)")
    parser.add_argument("--model", type=str, default=Config.OLLAMA_MODEL, help="Ollama Model to use")
    args = parser.parse_args()

    print(f"Starting Gemini Gateway with model: {args.model}...")
    
    # Validate configuration
    try:
        Config.validate()
    except Exception as e:
        print(f"Configuration Error: {e}")
        # sys.exit(1) # Don't exit on config error to allow partial operation if possible

    # Ensure directories exist
    os.makedirs(Config.SESSION_DIR, exist_ok=True)
    os.makedirs(Config.MEMORY_DIR, exist_ok=True)

    # Initialize Core Components
    session_store = SessionStore(Config.SESSION_DIR)
    
    # Initialize Memory Store
    try:
        memory_store = MemoryStore(Config.MEMORY_DIR, model_name=Config.OLLAMA_MODEL)
        set_memory_store(memory_store) # Inject into tools
        print(f"Memory Store initialized with {Config.OLLAMA_MODEL} embeddings.")
    except Exception as e:
        print(f"Warning: Could not initialize Memory Store: {e}")
        memory_store = None

    # System instruction for the AI agent
    # Detect user environment
    user_home = os.path.expanduser("~")
    user_name = os.getenv("USERNAME", "User")
    
    system_instruction = (
        f"You are Gemini Gateway, a powerful AI assistant that can control this Windows laptop remotely for user '{user_name}'.\n"
        f"The user's home directory is: {user_home}\n"
        f"The user's Desktop is at: {os.path.join(user_home, 'Desktop')}\n"
        "You have access to tools that let you perform real actions on this computer.\n\n"
        "CRITICAL RULES:\n"
        "- ALWAYS use your tools to perform actions. NEVER just describe what you would do - actually DO it.\n"
        "- Never pretend or hallucinate that you performed an action. Use the tools.\n\n"
        "AVAILABLE CAPABILITIES:\n"
        "- Files: Use write_file, read_file to create/read files\n"
        "- Commands: Use run_command to execute any shell command\n"
        "- YouTube: Use play_on_youtube to search and play videos/songs/cartoons on YouTube\n"
        "- Spotify: Use play_on_spotify to play music on the Spotify app\n"
        "- Browser: Use open_website to open any URL in the browser\n"
        "- Apps: Use open_application to launch apps (notepad, calc, chrome, spotify, discord, code, etc.)\n"
        "- Media Control: Use media_control for play/pause, next, previous, volume_up/down, mute (controls system media)\n"
        "- WhatsApp: Use send_whatsapp_message to send messages via WhatsApp Desktop (requires app installed & logged in)\n"
        "- System: Use system_control for volume, brightness, screenshot, lock, shutdown, restart, sleep\n"
        "- Info: Use get_system_info for battery, IP, disk space, WiFi, processes, uptime\n"
        "- Memory: Use save_memory and memory_search for remembering things\n\n"
        "EXAMPLES:\n"
        '- "Play Ninja Hattori on YouTube" -> use play_on_youtube("Ninja Hattori")\n'
        '- "Play Night Changes on Spotify" -> use play_on_spotify("Night Changes")\n'
        '- "Open Google" -> use open_website("https://www.google.com")\n'
        '- "Increase volume" -> use system_control("volume_up")\n'
        '- "What is my battery?" -> use get_system_info("battery")\n'
        '- "Lock my laptop" -> use system_control("lock")\n'
        '- "Play/Pause media" -> use media_control("play_pause")\n'
        '- "Next song" -> use media_control("next")\n'
        '- "Send WhatsApp to Mom saying Hello" -> use send_whatsapp_message("Mom", "Hello")\n'
        '- "Send WhatsApp to +919999999999 saying Hello" -> use send_whatsapp_message("+919999999999", "Hello")\n'
        '- "Open Notepad" -> use open_application("notepad")\n'
    )

    ollama_client = OllamaClient(Config.OLLAMA_BASE_URL, model_name=args.model, system_instruction=system_instruction)
    
    # Initialize Agent
    agent = GeminiAgent(session_store, ollama_client, memory_store)
    
    # Initialize Scheduler
    if Config.SCHEDULER_ENABLED:
        scheduler = Scheduler()
        scheduler.start()

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
