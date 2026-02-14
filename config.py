import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # Gemini Configuration
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    # if not GOOGLE_API_KEY:
    #     print("Warning: GOOGLE_API_KEY not found. Gemini models will not work.")
    
    # Model Configuration
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    # Telegram Configuration
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

    # Ollama Configuration
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")

    # Gateway Configuration
    GATEWAY_HOST = os.getenv("GATEWAY_HOST", "0.0.0.0")
    GATEWAY_PORT = int(os.getenv("GATEWAY_PORT", 5000))

    # Paths
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SESSION_DIR = os.getenv("SESSION_DIR", os.path.join(BASE_DIR, "sessions"))
    MEMORY_DIR = os.getenv("MEMORY_DIR", os.path.join(BASE_DIR, "memory"))
    
    # Scheduler
    SCHEDULER_ENABLED = os.getenv("SCHEDULER_ENABLED", "true").lower() == "true"

    # WebMCP Configuration
    WEBMCP_ENABLED = os.getenv("WEBMCP_ENABLED", "true").lower() == "true"
    WEBMCP_TIMEOUT = int(os.getenv("WEBMCP_TIMEOUT", 30))  # seconds per page load
    WEBMCP_HEADLESS = os.getenv("WEBMCP_HEADLESS", "true").lower() == "true"

    @classmethod
    def validate(cls):
        if not cls.GOOGLE_API_KEY:
            print("Warning: GOOGLE_API_KEY is missing.")
        if not cls.TELEGRAM_BOT_TOKEN:
            print("Warning: TELEGRAM_BOT_TOKEN is missing. Telegram integration will be disabled.")
