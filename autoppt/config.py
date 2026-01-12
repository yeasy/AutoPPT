import logging
import os
from typing import Optional

from dotenv import load_dotenv

from .exceptions import APIKeyError

DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

logger = logging.getLogger(__name__)


class Config:
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    OFFLINE_MODE = False

    DEFAULT_OPENAI_MODEL = "gpt-4o"
    DEFAULT_GOOGLE_MODEL = "gemini-2.0-flash"
    DEFAULT_ANTHROPIC_MODEL = "claude-3-5-sonnet-20241022"
    OUTPUT_DIR = "output"

    API_RETRY_ATTEMPTS = 3
    API_RETRY_DELAY_SECONDS = 60
    IMAGE_DOWNLOAD_TIMEOUT = 30
    IMAGE_DOWNLOAD_MAX_BYTES = 10 * 1024 * 1024
    RESEARCH_CACHE_SIZE = 128
    RESEARCH_FETCH_WORKERS = 4

    _env_loaded = False

    @classmethod
    def initialize(cls, configure_logging: bool = False, log_level: int = logging.INFO) -> None:
        if not cls._env_loaded:
            load_dotenv()
            cls._env_loaded = True
        cls.refresh()
        if configure_logging:
            cls.configure_logging(log_level)

    @classmethod
    def refresh(cls) -> None:
        cls.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        cls.ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
        cls.GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
        cls.OFFLINE_MODE = os.getenv("AUTOPPT_OFFLINE", "").strip().lower() in {"1", "true", "yes", "on"}

    @classmethod
    def configure_logging(cls, level: int = logging.INFO) -> None:
        root_logger = logging.getLogger()
        if root_logger.handlers:
            root_logger.setLevel(level)
            return
        logging.basicConfig(
            level=level,
            format=DEFAULT_LOG_FORMAT,
            datefmt=DEFAULT_DATE_FORMAT,
        )

    @classmethod
    def provider_api_key(cls, provider_name: str) -> Optional[str]:
        cls.initialize()
        provider_name = provider_name.lower()
        return {
            "openai": cls.OPENAI_API_KEY,
            "anthropic": cls.ANTHROPIC_API_KEY,
            "google": cls.GOOGLE_API_KEY,
        }.get(provider_name)

    @classmethod
    def has_api_key(cls, provider_name: str) -> bool:
        if provider_name.lower() == "mock":
            return True
        return bool(cls.provider_api_key(provider_name))

    @classmethod
    def validate(cls, provider_name: Optional[str] = None) -> bool:
        cls.initialize()

        if provider_name:
            if provider_name.lower() == "mock":
                return True
            if not cls.has_api_key(provider_name):
                raise APIKeyError(provider_name)
            return True

        if not cls.OPENAI_API_KEY and not cls.ANTHROPIC_API_KEY and not cls.GOOGLE_API_KEY:
            logger.warning("No API keys found in .env file. Use --provider mock for testing.")
            return False
        return True

    @classmethod
    def is_offline_mode(cls) -> bool:
        cls.initialize()
        return cls.OFFLINE_MODE
