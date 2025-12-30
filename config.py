import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    
    # Defaults
    DEFAULT_MODEL = "openai/gpt-4o"
    OUTPUT_DIR = "output"

    @staticmethod
    def validate():
        if not Config.OPENAI_API_KEY and not Config.ANTHROPIC_API_KEY and not Config.GOOGLE_API_KEY:
            print("Warning: No API keys found in .env file.")
