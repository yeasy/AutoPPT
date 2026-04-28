"""
AutoPPT - AI-Powered Presentation Generator
"""
from __future__ import annotations

from PIL import Image

from .config import Config

Image.MAX_IMAGE_PIXELS = Config.MAX_IMAGE_PIXELS

from .generator import Generator
from .llm_provider import get_provider, BaseLLMProvider
from .researcher import Researcher
from .ppt_renderer import PPTRenderer
from .exceptions import AutoPPTError

__version__ = "0.5.8"
