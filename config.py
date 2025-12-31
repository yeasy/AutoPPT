import os
import logging
from dotenv import load_dotenv

load_dotenv()

# Configure logging for the entire application
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    
    # Defaults - synchronized with actual provider implementations
    DEFAULT_OPENAI_MODEL = "gpt-4o"
    DEFAULT_GOOGLE_MODEL = "gemini-2.0-flash"
    DEFAULT_ANTHROPIC_MODEL = "claude-3-5-sonnet-20241022"
    OUTPUT_DIR = "output"
    
    # Performance settings
    API_RETRY_ATTEMPTS = 3
    API_RETRY_DELAY_SECONDS = 60
    IMAGE_DOWNLOAD_TIMEOUT = 30

    @staticmethod
    def validate() -> bool:
        """Validate that at least one API key is configured."""
        if not Config.OPENAI_API_KEY and not Config.ANTHROPIC_API_KEY and not Config.GOOGLE_API_KEY:
            logger.warning("No API keys found in .env file. Use --provider mock for testing.")
            return False
        return True
