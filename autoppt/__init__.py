"""
AutoPPT - AI-Powered Presentation Generator
"""

from .generator import Generator
from .config import Config
from .llm_provider import get_provider, BaseLLMProvider
from .researcher import Researcher
from .ppt_renderer import PPTRenderer
from .exceptions import AutoPPTError

__version__ = "0.4.0"
