import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, get_args, get_origin

from pydantic import BaseModel

from .config import Config
from .exceptions import APIKeyError, RateLimitError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

PROVIDER_MODELS: Dict[str, List[str]] = {
    "openai": ["gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano", "gpt-5.4", "gpt-5.4-mini", "gpt-5.4-nano"],
    "google": ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-pro", "gemini-3-flash-preview", "gemini-3.1-pro-preview", "gemini-3.1-flash-lite-preview"],
    "anthropic": ["claude-sonnet-4-6", "claude-opus-4-6", "claude-haiku-4-5-20251001"],
    "mock": [],
}


def get_supported_providers() -> List[str]:
    return list(PROVIDER_MODELS.keys())


def get_provider_models(provider_name: str) -> List[str]:
    return PROVIDER_MODELS.get(provider_name.lower(), [])


def _is_local_base_url(base_url: Optional[str]) -> bool:
    if not base_url:
        return False
    try:
        from urllib.parse import urlparse
        hostname = urlparse(base_url).hostname
        return hostname in ("localhost", "127.0.0.1", "::1")
    except Exception:
        return False


def _is_rate_limit_error(exc: Exception) -> bool:
    status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
    if status == 429:
        return True
    message = str(exc).lower()
    return "429" in message or "rate_limit" in message or "rate limit" in message or "quota" in message


def _is_transient_error(exc: Exception) -> bool:
    """Check if the error is a transient server error worth retrying."""
    status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
    if isinstance(status, int) and status in (500, 502, 503, 529):
        return True
    message = str(exc).lower()
    transient_signals = (
        "connection reset", "connection refused", "connection closed",
        "timeout", "timed out", "temporarily", "overloaded",
        "internal server error", "bad gateway", "service unavailable",
    )
    return any(signal in message for signal in transient_signals)


def _run_with_retries(provider_name: str, operation: Callable[[], Any]) -> Any:
    if Config.API_RETRY_ATTEMPTS < 1:
        raise ValueError(f"API_RETRY_ATTEMPTS must be >= 1, got {Config.API_RETRY_ATTEMPTS}")
    last_exc: Optional[Exception] = None
    for attempt in range(Config.API_RETRY_ATTEMPTS):
        try:
            return operation()
        except Exception as exc:
            last_exc = exc
            is_last = attempt >= Config.API_RETRY_ATTEMPTS - 1
            if _is_rate_limit_error(exc):
                if not is_last:
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
            if _is_transient_error(exc):
                if not is_last:
                    delay = min(Config.TRANSIENT_RETRY_BASE_SECONDS * (2 ** attempt), Config.API_RETRY_DELAY_SECONDS)
                    logger.warning(
                        "Transient error for %s, retrying in %ss... (attempt %s/%s): %s",
                        provider_name,
                        delay,
                        attempt + 1,
                        Config.API_RETRY_ATTEMPTS,
                        exc,
                    )
                    time.sleep(delay)
                    continue
            raise
    raise RuntimeError(f"Exhausted {Config.API_RETRY_ATTEMPTS} retry attempts") from last_exc


class BaseLLMProvider(ABC):
    @abstractmethod
    def generate_text(self, prompt: str, system_prompt: str = "") -> str:
        pass

    @abstractmethod
    def generate_structure(self, prompt: str, schema: Type[T], system_prompt: str = "") -> T:
        pass


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: str = "gpt-4.1"):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError("Please install openai: pip install openai") from exc

        Config.initialize()
        env_base = os.getenv("OPENAI_API_BASE")
        base = base_url or env_base

        if base and not _is_local_base_url(base):
            logger.warning("Non-local OpenAI base URL configured: %s", base)

        if base and _is_local_base_url(base):
            from urllib.parse import urlparse
            if not urlparse(base).path.rstrip("/").endswith("/v1"):
                base = f"{base.rstrip('/')}/v1"

        resolved_api_key = api_key or Config.OPENAI_API_KEY
        if not resolved_api_key and not _is_local_base_url(base):
            raise APIKeyError("openai")

        self.client = OpenAI(
            api_key=resolved_api_key or "local-dev",
            base_url=base,
        )
        self.model = model

    @staticmethod
    def _build_messages(prompt: str, system_prompt: str) -> List[Dict[str, str]]:
        msgs: List[Dict[str, str]] = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        msgs.append({"role": "user", "content": prompt})
        return msgs

    def generate_text(self, prompt: str, system_prompt: str = "") -> str:
        msgs = self._build_messages(prompt, system_prompt)
        response = _run_with_retries(
            "openai",
            lambda: self.client.chat.completions.create(
                model=self.model,
                messages=msgs,  # type: ignore[arg-type]
                temperature=0.7,
            ),
        )
        if not response.choices:
            raise ValueError("OpenAI returned no choices in the response")
        result: Optional[str] = response.choices[0].message.content
        if result is None:
            raise ValueError("OpenAI returned a message with no content")
        return result

    def generate_structure(self, prompt: str, schema: Type[T], system_prompt: str = "") -> T:
        msgs = self._build_messages(prompt, system_prompt)
        completion = _run_with_retries(
            "openai",
            lambda: self.client.beta.chat.completions.parse(
                model=self.model,
                messages=msgs,  # type: ignore[arg-type]
                response_format=schema,
            ),
        )
        if not completion.choices:
            raise ValueError("OpenAI returned no choices in the response")
        parsed: Optional[T] = completion.choices[0].message.parsed
        if parsed is None:
            raise ValueError("OpenAI structured output parsing returned None")
        return parsed


class GoogleProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.5-flash"):
        try:
            from google import genai as _genai
        except ImportError as exc:
            raise ImportError("Please install google-genai: pip install google-genai") from exc

        Config.initialize()
        resolved_api_key = api_key or Config.GOOGLE_API_KEY
        if not resolved_api_key:
            raise APIKeyError("google")
        self.client = _genai.Client(api_key=resolved_api_key)
        self.model_id = model

    def generate_text(self, prompt: str, system_prompt: str = "") -> str:
        from google.genai import types
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
        try:
            text: Optional[str] = response.text
        except ValueError as e:
            raise ValueError(f"Google response blocked or empty: {e}") from e
        if text is None:
            raise ValueError("Google returned a response with no text content")
        return text

    def generate_structure(self, prompt: str, schema: Type[T], system_prompt: str = "") -> T:
        from google.genai import types
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
        try:
            parsed: Optional[T] = response.parsed
        except ValueError as e:
            raise ValueError(f"Google structured response blocked or empty: {e}") from e
        if parsed is None:
            raise ValueError("Google structured output parsing returned None")
        if isinstance(parsed, dict):
            return schema.model_validate(parsed)
        return parsed


class AnthropicProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: Optional[str] = None):
        try:
            import anthropic
        except ImportError as exc:
            raise ImportError("Please install anthropic: pip install anthropic") from exc

        Config.initialize()
        resolved_api_key = api_key or Config.ANTHROPIC_API_KEY
        if not resolved_api_key:
            raise APIKeyError("anthropic")

        base_url = base_url or os.getenv("ANTHROPIC_BASE_URL")
        if base_url and not _is_local_base_url(base_url):
            logger.warning("Non-local Anthropic base URL configured: %s", base_url)
        self.client = anthropic.Anthropic(api_key=resolved_api_key, base_url=base_url)
        self.model = model or Config.DEFAULT_ANTHROPIC_MODEL

    def generate_text(self, prompt: str, system_prompt: str = "") -> str:
        kwargs: dict[str, Any] = dict(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        if system_prompt:
            kwargs["system"] = system_prompt
        message = _run_with_retries(
            "anthropic",
            lambda: self.client.messages.create(**kwargs),
        )
        if not message.content:
            raise ValueError("Anthropic returned an empty response")
        for block in message.content:
            if hasattr(block, "text"):
                result: str = block.text
                return result
        raise ValueError("Anthropic response contained no text block")

    def generate_structure(self, prompt: str, schema: Type[T], system_prompt: str = "") -> T:
        import json

        schema_description = schema.model_json_schema()
        enhanced_prompt = f"""
{prompt}

You MUST respond with valid JSON that matches this schema:
{json.dumps(schema_description, indent=2)}

Respond ONLY with the JSON object, no additional text.
"""
        kwargs: dict[str, Any] = dict(
            model=self.model,
            max_tokens=8192,
            messages=[{"role": "user", "content": enhanced_prompt}],
        )
        if system_prompt:
            kwargs["system"] = system_prompt
        message = _run_with_retries(
            "anthropic",
            lambda: self.client.messages.create(**kwargs),
        )
        if not message.content:
            raise ValueError("Anthropic returned an empty response")
        if getattr(message, "stop_reason", None) == "max_tokens":
            raise ValueError("Anthropic structured response was truncated (max_tokens reached); output is likely invalid JSON")
        response_text = ""
        for block in message.content:
            if hasattr(block, "text"):
                response_text = block.text
                break
        if not response_text:
            raise ValueError("Anthropic response contained no text block")
        logger.debug("Raw Anthropic response length: %d chars", len(response_text))
        if "```json" in response_text:
            response_text = response_text.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in response_text:
            fenced = response_text.split("```", 1)[1].split("```", 1)[0]
            lines = fenced.split("\n", 1)
            if len(lines) > 1 and not lines[0].strip().startswith(("{", "[")):
                fenced = lines[1]
            response_text = fenced.strip()

        try:
            data = json.loads(response_text)
        except json.JSONDecodeError:
            # Fallback: use raw_decode to find the largest JSON object
            decoder = json.JSONDecoder()
            best: tuple[dict | None, int, int] = (None, -1, 0)  # (data, offset, length)
            for i, ch in enumerate(response_text):
                if ch == "{":
                    try:
                        obj, end = decoder.raw_decode(response_text, i)
                        span = end - i
                        if span > best[2]:
                            best = (obj, i, span)
                    except json.JSONDecodeError:
                        continue
            data, offset, _ = best
            if data is None:
                raise ValueError(
                    f"Anthropic returned invalid JSON: {response_text[:200]}"
                )
            logger.warning("Anthropic response required raw_decode fallback (offset %d)", offset)
        return schema.model_validate(data)


class MockProvider(BaseLLMProvider):
    def _extract_hint(self, prompt_lower: str, label: str) -> str:
        marker = f"{label.lower()}: '"
        if marker not in prompt_lower:
            return ""
        raw = prompt_lower.split(marker, 1)[1].split("'", 1)[0].strip()
        return raw[:200]

    def generate_text(self, prompt: str, system_prompt: str = "") -> str:
        return (
            "This is a high-quality researched content for your presentation. "
            "It covers the key aspects of the requested topic with depth and clarity, "
            "ensuring a professional delivery. Citation: [Source 2026]"
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

        def _is_str_type(annotation: Any) -> bool:
            """Check if annotation is str or Optional[str]."""
            if annotation is str:
                return True
            args = get_args(annotation)
            # Handle Optional[str] (Union[str, None])
            if args and str in args and type(None) in args and len(args) == 2:
                return True
            return False

        def _is_list_str_type(annotation: Any) -> bool:
            """Check if annotation is List[str], list[str], or Optional variants."""
            origin = get_origin(annotation)
            args = get_args(annotation)
            if origin is list and args == (str,):
                return True
            # Handle Optional[List[str]]
            if args and type(None) in args:
                for arg in args:
                    if arg is type(None):
                        continue
                    inner_origin = get_origin(arg)
                    inner_args = get_args(arg)
                    if inner_origin is list and inner_args == (str,):
                        return True
            return False

        def _is_list_section_type(annotation: Any) -> bool:
            """Check if annotation is List[PresentationSection] or similar."""
            origin = get_origin(annotation)
            args = get_args(annotation)
            if origin is list and args and args[0] is PresentationSection:
                return True
            return False

        dummy_data: Dict[str, Any] = {}
        for field_name, field in schema.model_fields.items():
            if _is_str_type(field.annotation):
                if field_name == "left_title":
                    dummy_data[field_name] = left_title_hint.title() if left_title_hint else "Current State"
                elif field_name == "right_title":
                    dummy_data[field_name] = right_title_hint.title() if right_title_hint else "Future State"
                elif "title" in field_name.lower():
                    dummy_data[field_name] = f"Overview of {topic}"
                elif "image_query" in field_name.lower():
                    dummy_data[field_name] = f"professional artistic image of {topic}"
                elif "quote_text" in field_name.lower():
                    dummy_data[field_name] = f"{topic.title()} rewards disciplined execution over vague ambition."
                elif "quote_author" in field_name.lower():
                    dummy_data[field_name] = quote_author_hint.title() if quote_author_hint else "AutoPPT Research Desk"
                elif "quote_context" in field_name.lower():
                    dummy_data[field_name] = quote_context_hint.title() if quote_context_hint else "Mock analysis"
                else:
                    dummy_data[field_name] = f"Comprehensive analysis and professional insight into {topic}."
            elif _is_list_str_type(field.annotation):
                if field_name == "left_bullets":
                    dummy_data[field_name] = [
                        f"Current operating model for {topic}",
                        f"Existing bottlenecks affecting {topic}",
                        "Baseline metrics and constraints",
                    ]
                elif field_name == "right_bullets":
                    dummy_data[field_name] = [
                        f"Target operating model for {topic}",
                        f"Expected gains from improving {topic}",
                        "Next-step execution priorities",
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
                    StatisticData(value="$4.2B", label="Revenue 2026"),
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
            elif _is_list_section_type(field.annotation):
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
