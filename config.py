import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # Gemini Configuration
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY not found in environment variables. Please set it in .env file.")
    
    # Model Configuration
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    # Telegram Configuration
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

    # Gateway Configuration
    GATEWAY_HOST = os.getenv("GATEWAY_HOST", "0.0.0.0")
    GATEWAY_PORT = int(os.getenv("GATEWAY_PORT", 5000))

    # Paths
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SESSION_DIR = os.getenv("SESSION_DIR", os.path.join(BASE_DIR, "sessions"))
    MEMORY_DIR = os.getenv("MEMORY_DIR", os.path.join(BASE_DIR, "memory"))
    
    # Scheduler
    SCHEDULER_ENABLED = os.getenv("SCHEDULER_ENABLED", "true").lower() == "true"

    @classmethod
    def validate(cls):
        if not cls.GOOGLE_API_KEY:
            print("Warning: GOOGLE_API_KEY is missing.")
        if not cls.TELEGRAM_BOT_TOKEN:
            print("Warning: TELEGRAM_BOT_TOKEN is missing. Telegram integration will be disabled.")
