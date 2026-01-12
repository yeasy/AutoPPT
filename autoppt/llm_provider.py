import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Type, TypeVar

from google import genai
from google.genai import types
from openai import OpenAI
from pydantic import BaseModel

from .config import Config
from .exceptions import APIKeyError, RateLimitError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

PROVIDER_MODELS: Dict[str, List[str]] = {
    "openai": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
    "google": ["gemini-2.0-flash", "gemini-1.5-pro"],
    "anthropic": ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229"],
    "mock": [],
}


def get_supported_providers() -> List[str]:
    return list(PROVIDER_MODELS.keys())


def get_provider_models(provider_name: str) -> List[str]:
    return PROVIDER_MODELS.get(provider_name.lower(), [])


def _is_local_base_url(base_url: Optional[str]) -> bool:
    if not base_url:
        return False
    return any(host in base_url for host in ("localhost", "127.0.0.1"))


def _is_rate_limit_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "429" in message or "rate limit" in message or "quota" in message


def _run_with_retries(provider_name: str, operation):
    for attempt in range(Config.API_RETRY_ATTEMPTS):
        try:
            return operation()
        except Exception as exc:
            if _is_rate_limit_error(exc):
                if attempt < Config.API_RETRY_ATTEMPTS - 1:
                    logger.warning(
                        "Rate limit hit for %s, retrying in %ss... (attempt %s/%s)",
                        provider_name,
                        Config.API_RETRY_DELAY_SECONDS,
                        attempt + 1,
                        Config.API_RETRY_ATTEMPTS,
                    )
                    time.sleep(Config.API_RETRY_DELAY_SECONDS)
                    continue
                raise RateLimitError(provider_name, Config.API_RETRY_DELAY_SECONDS) from exc
            raise


class BaseLLMProvider(ABC):
    @abstractmethod
    def generate_text(self, prompt: str, system_prompt: str = "") -> str:
        pass

    @abstractmethod
    def generate_structure(self, prompt: str, schema: Type[T], system_prompt: str = "") -> T:
        pass


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: str = "gpt-4o"):
        Config.initialize()
        env_base = os.getenv("OPENAI_API_BASE")
        base = base_url or env_base

        if base and "v1" not in base and "localhost" in base:
            base = f"{base.rstrip('/')}/v1"

        resolved_api_key = api_key or Config.OPENAI_API_KEY
        if not resolved_api_key and not _is_local_base_url(base):
            raise APIKeyError("openai")

        self.client = OpenAI(
            api_key=resolved_api_key or "local-dev",
            base_url=base,
        )
        self.model = model

    def generate_text(self, prompt: str, system_prompt: str = "") -> str:
        response = _run_with_retries(
            "openai",
            lambda: self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
            ),
        )
        return response.choices[0].message.content

    def generate_structure(self, prompt: str, schema: Type[T], system_prompt: str = "") -> T:
        completion = _run_with_retries(
            "openai",
            lambda: self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                response_format=schema,
            ),
        )
        return completion.choices[0].message.parsed


class GoogleProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.0-flash"):
        Config.initialize()
        resolved_api_key = api_key or Config.GOOGLE_API_KEY
        if not resolved_api_key:
            raise APIKeyError("google")
        self.client = genai.Client(api_key=resolved_api_key)
        self.model_id = model

    def generate_text(self, prompt: str, system_prompt: str = "") -> str:
        response = _run_with_retries(
            "google",
            lambda: self.client.models.generate_content(
                model=self.model_id,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.7,
                ),
                contents=prompt,
            ),
        )
        return response.text

    def generate_structure(self, prompt: str, schema: Type[T], system_prompt: str = "") -> T:
        response = _run_with_retries(
            "google",
            lambda: self.client.models.generate_content(
                model=self.model_id,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    response_schema=schema,
                    temperature=0.2,
                ),
                contents=prompt,
            ),
        )
        return response.parsed


class AnthropicProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: Optional[str] = None):
        try:
            import anthropic
        except ImportError:
            raise ImportError("Please install anthropic: pip install anthropic")

        Config.initialize()
        resolved_api_key = api_key or Config.ANTHROPIC_API_KEY
        if not resolved_api_key:
            raise APIKeyError("anthropic")

        base_url = base_url or os.getenv("ANTHROPIC_BASE_URL")
        self.client = anthropic.Anthropic(api_key=resolved_api_key, base_url=base_url)
        self.model = model or Config.DEFAULT_ANTHROPIC_MODEL

    def generate_text(self, prompt: str, system_prompt: str = "") -> str:
        message = _run_with_retries(
            "anthropic",
            lambda: self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
            ),
        )
        return message.content[0].text

    def generate_structure(self, prompt: str, schema: Type[T], system_prompt: str = "") -> T:
        import json

        schema_description = schema.model_json_schema()
        enhanced_prompt = f"""
{prompt}

You MUST respond with valid JSON that matches this schema:
{json.dumps(schema_description, indent=2)}

Respond ONLY with the JSON object, no additional text.
"""
        message = _run_with_retries(
            "anthropic",
            lambda: self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": enhanced_prompt}],
            ),
        )
        response_text = message.content[0].text
        logger.debug("Raw Anthropic response: %s", response_text)
        if "```json" in response_text:
            response_text = response_text.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```", 1)[1].split("```", 1)[0].strip()

        data = json.loads(response_text)
        return schema.model_validate(data)


class MockProvider(BaseLLMProvider):
    def _extract_hint(self, prompt_lower: str, label: str) -> str:
        marker = f"{label.lower()}: '"
        if marker not in prompt_lower:
            return ""
        return prompt_lower.split(marker, 1)[1].split("'", 1)[0].strip()

    def generate_text(self, prompt: str, system_prompt: str = "") -> str:
        return (
            "This is a high-quality researched content for your presentation. "
            "It covers the key aspects of the requested topic with depth and clarity, "
            "ensuring a professional delivery. Citation: [Source 2025]"
        )

    def generate_structure(self, prompt: str, schema: Type[T], system_prompt: str = "") -> T:
        from .data_types import PresentationSection, SlideType

        topic = "Current Topic"
        if "topic:" in prompt.lower():
            topic = prompt.lower().split("topic:")[1].split("\n")[0].strip()
        elif "about" in prompt.lower():
            topic = prompt.lower().split("about")[1].split("\n")[0].strip()

        prompt_lower = prompt.lower()
        preferred_type = self._extract_hint(prompt_lower, "preferred slide type")
        left_title_hint = self._extract_hint(prompt_lower, "left title hint")
        right_title_hint = self._extract_hint(prompt_lower, "right title hint")
        quote_author_hint = self._extract_hint(prompt_lower, "quote author hint")
        quote_context_hint = self._extract_hint(prompt_lower, "quote context hint")

        dummy_data = {}
        for field_name, field in schema.model_fields.items():
            if field.annotation == str:
                if "title" in field_name.lower():
                    dummy_data[field_name] = f"Overview of {topic}"
                elif "image_query" in field_name.lower():
                    dummy_data[field_name] = f"professional artistic image of {topic}"
                elif "quote_text" in field_name.lower():
                    dummy_data[field_name] = f"{topic.title()} rewards disciplined execution over vague ambition."
                elif "quote_author" in field_name.lower():
                    dummy_data[field_name] = quote_author_hint.title() if quote_author_hint else "AutoPPT Research Desk"
                elif "quote_context" in field_name.lower():
                    dummy_data[field_name] = quote_context_hint.title() if quote_context_hint else "Mock analysis"
                elif field_name == "left_title":
                    dummy_data[field_name] = left_title_hint.title() if left_title_hint else "Current State"
                elif field_name == "right_title":
                    dummy_data[field_name] = right_title_hint.title() if right_title_hint else "Future State"
                else:
                    dummy_data[field_name] = f"Comprehensive analysis and professional insight into {topic}."
            elif field.annotation == List[str]:
                if field_name == "left_bullets":
                    dummy_data[field_name] = [
                        f"Current operating model for {topic}",
                        f"Existing bottlenecks affecting {topic}",
                        f"Baseline metrics and constraints",
                    ]
                elif field_name == "right_bullets":
                    dummy_data[field_name] = [
                        f"Target operating model for {topic}",
                        f"Expected gains from improving {topic}",
                        f"Next-step execution priorities",
                    ]
                else:
                    dummy_data[field_name] = [
                        f"Key innovation and strategic importance of {topic}",
                        f"Global impact and future trends in {topic}",
                        f"Practical applications and case studies of {topic}",
                    ]
            elif "slide_type" in field_name:
                if preferred_type == "quote" or any(token in prompt_lower for token in ("quote", "vision", "principle", "leadership")):
                    dummy_data[field_name] = SlideType.QUOTE
                elif preferred_type == "comparison" or any(token in prompt_lower for token in ("versus", " vs ", "compare", "comparison", "tradeoff")):
                    dummy_data[field_name] = SlideType.COMPARISON
                elif preferred_type == "two_column" or any(token in prompt_lower for token in ("framework", "pillars", "dimensions", "left column", "right column")):
                    dummy_data[field_name] = SlideType.TWO_COLUMN
                elif preferred_type == "statistics" or "statistics" in prompt_lower or "market" in prompt_lower:
                    dummy_data[field_name] = SlideType.STATISTICS
                elif preferred_type == "image" or "visual" in prompt_lower or "image" in prompt_lower:
                    dummy_data[field_name] = SlideType.IMAGE
                elif preferred_type == "chart" or "chart" in prompt_lower or "growth" in prompt_lower:
                    dummy_data[field_name] = SlideType.CHART
                else:
                    dummy_data[field_name] = SlideType.CONTENT
            elif "statistics" in field_name:
                from .data_types import StatisticData

                dummy_data[field_name] = [
                    StatisticData(value="85%", label="Market Growth"),
                    StatisticData(value="$4.2B", label="Revenue 2025"),
                    StatisticData(value="150+", label="Countries"),
                ]
            elif "chart_data" in field_name:
                from .data_types import ChartData, ChartType

                dummy_data[field_name] = ChartData(
                    chart_type=ChartType.COLUMN,
                    title="Growth Prediction",
                    categories=["2023", "2024", "2025", "2026"],
                    values=[10.5, 15.2, 22.8, 35.0],
                    series_name="Revenue ($M)",
                )
            elif field.annotation == List[PresentationSection]:
                dummy_data[field_name] = [
                    PresentationSection(title=f"Fundamentals of {topic}", slides=[f"Introduction to {topic}", f"Core Concepts of {topic}"]),
                    PresentationSection(title=f"Advanced Applications: {topic}", slides=[f"Case Study: {topic}", "Economic Impact"]),
                    PresentationSection(title=f"The Future of {topic}", slides=[f"Predictions for {topic}", "Strategic Roadmap"]),
                ]
            else:
                dummy_data[field_name] = None

        return schema.model_validate(dummy_data)


def get_provider(provider_name: str, api_key: Optional[str] = None, model: Optional[str] = None) -> BaseLLMProvider:
    provider_name = provider_name.lower()

    if provider_name == "openai":
        return OpenAIProvider(api_key=api_key, model=model or Config.DEFAULT_OPENAI_MODEL)
    if provider_name == "google":
        return GoogleProvider(api_key=api_key, model=model or Config.DEFAULT_GOOGLE_MODEL)
    if provider_name == "anthropic":
        return AnthropicProvider(api_key=api_key, model=model or Config.DEFAULT_ANTHROPIC_MODEL)
    if provider_name == "mock":
        return MockProvider()
    raise ValueError(f"Unknown provider: {provider_name}. Supported: {', '.join(get_supported_providers())}")
