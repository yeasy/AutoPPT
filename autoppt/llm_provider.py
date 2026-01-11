import os
import logging
import time
from abc import ABC, abstractmethod
from typing import List, Type, TypeVar

from pydantic import BaseModel
from openai import OpenAI
from google import genai
from google.genai import types

from .exceptions import APIKeyError, RateLimitError
from .config import Config

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

class BaseLLMProvider(ABC):
    @abstractmethod
    def generate_text(self, prompt: str, system_prompt: str = "") -> str:
        """Generate a simple text response."""
        pass

    @abstractmethod
    def generate_structure(self, prompt: str, schema: Type[T], system_prompt: str = "") -> T:
        """Generate a structured Pydantic object."""
        pass

class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str = None, model: str = "gpt-5.2"):
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = model

    def generate_text(self, prompt: str, system_prompt: str = "") -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content

    def generate_structure(self, prompt: str, schema: Type[T], system_prompt: str = "") -> T:
        completion = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            response_format=schema,
        )
        return completion.choices[0].message.parsed

class GoogleProvider(BaseLLMProvider):
    def __init__(self, api_key: str = None, model: str = "gemini-2.0-flash"):
        api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.client = genai.Client(api_key=api_key)
        self.model_id = model

    def generate_text(self, prompt: str, system_prompt: str = "") -> str:
        import time
        for attempt in range(3):
            try:
                response = self.client.models.generate_content(
                    model=self.model_id,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=0.7
                    ),
                    contents=prompt
                )
                return response.text
            except Exception as e:
                if "429" in str(e) and attempt < 2:
                    print(f"Rate limit hit, retrying in 60s... (Attempt {attempt+1}/3)")
                    time.sleep(60)
                else:
                    raise e

    def generate_structure(self, prompt: str, schema: Type[T], system_prompt: str = "") -> T:
        import time
        for attempt in range(3):
            try:
                response = self.client.models.generate_content(
                    model=self.model_id,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        response_mime_type="application/json",
                        response_schema=schema,
                        temperature=0.2
                    ),
                    contents=prompt
                )
                return response.parsed
            except Exception as e:
                if "429" in str(e) and attempt < 2:
                    logger.warning(f"Rate limit hit, retrying in {Config.API_RETRY_DELAY_SECONDS}s... (Attempt {attempt+1}/{Config.API_RETRY_ATTEMPTS})")
                    time.sleep(Config.API_RETRY_DELAY_SECONDS)
                else:
                    raise RateLimitError("google", Config.API_RETRY_DELAY_SECONDS)


class AnthropicProvider(BaseLLMProvider):
    """Provider for Anthropic Claude models."""
    
    def __init__(self, api_key: str = None, model: str = None):
        try:
            import anthropic
        except ImportError:
            raise ImportError("Please install anthropic: pip install anthropic")
        
        api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise APIKeyError("anthropic")
        
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model or Config.DEFAULT_ANTHROPIC_MODEL

    def generate_text(self, prompt: str, system_prompt: str = "") -> str:
        for attempt in range(Config.API_RETRY_ATTEMPTS):
            try:
                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                return message.content[0].text
            except Exception as e:
                if "rate" in str(e).lower() and attempt < Config.API_RETRY_ATTEMPTS - 1:
                    logger.warning(f"Rate limit hit, retrying in {Config.API_RETRY_DELAY_SECONDS}s... (Attempt {attempt+1}/{Config.API_RETRY_ATTEMPTS})")
                    time.sleep(Config.API_RETRY_DELAY_SECONDS)
                else:
                    raise e

    def generate_structure(self, prompt: str, schema: Type[T], system_prompt: str = "") -> T:
        import json
        
        # Anthropic doesn't have native structured output, so we prompt for JSON
        schema_description = schema.model_json_schema()
        enhanced_prompt = f"""
{prompt}

You MUST respond with valid JSON that matches this schema:
{json.dumps(schema_description, indent=2)}

Respond ONLY with the JSON object, no additional text.
"""
        for attempt in range(Config.API_RETRY_ATTEMPTS):
            try:
                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": enhanced_prompt}
                    ]
                )
                response_text = message.content[0].text
                # Parse and validate against schema
                data = json.loads(response_text)
                return schema.model_validate(data)
            except Exception as e:
                if "rate" in str(e).lower() and attempt < Config.API_RETRY_ATTEMPTS - 1:
                    logger.warning(f"Rate limit hit, retrying in {Config.API_RETRY_DELAY_SECONDS}s... (Attempt {attempt+1}/{Config.API_RETRY_ATTEMPTS})")
                    time.sleep(Config.API_RETRY_DELAY_SECONDS)
                else:
                    raise e


class MockProvider(BaseLLMProvider):
    """Mock provider for testing without API keys."""
    
    def generate_text(self, prompt: str, system_prompt: str = "") -> str:
        return f"This is a high-quality researched content for your presentation. It covers the key aspects of the requested topic with depth and clarity, ensuring a professional delivery. Citation: [Source 2025]"

    def generate_structure(self, prompt: str, schema: Type[T], system_prompt: str = "") -> T:
        from .data_types import PresentationSection
        
        # Try to extract topic for better mock data
        topic = "Current Topic"
        if "topic:" in prompt.lower():
            topic = prompt.lower().split("topic:")[1].split("\n")[0].strip()
        elif "about" in prompt.lower():
            topic = prompt.lower().split("about")[1].split("\n")[0].strip()

        dummy_data = {}
        for field_name, field in schema.model_fields.items():
            if field.annotation == str:
                if "title" in field_name.lower():
                    dummy_data[field_name] = f"Overview of {topic}"
                elif "image_query" in field_name.lower():
                    dummy_data[field_name] = f"professional artistic image of {topic}"
                else:
                    dummy_data[field_name] = f"Comprehensive analysis and professional insight into {topic}."
            elif field.annotation == List[str]:
                dummy_data[field_name] = [
                    f"Key innovation and strategic importance of {topic}",
                    f"Global impact and future trends in {topic}",
                    f"Practical applications and case studies of {topic}"
                ]
            elif "slide_type" in field_name:
                from .data_types import SlideType
                dummy_data[field_name] = SlideType.CONTENT
            elif field.annotation == List[PresentationSection]:
                dummy_data[field_name] = [
                    PresentationSection(title=f"Fundamentals of {topic}", slides=[f"Introduction to {topic}", f"Core Concepts of {topic}"]),
                    PresentationSection(title=f"Advanced Applications: {topic}", slides=[f"Case Study: {topic}", f"Economic Impact"]),
                    PresentationSection(title=f"The Future of {topic}", slides=[f"Predictions for {topic}", f"Strategic Roadmap"])
                ]
            else:
                dummy_data[field_name] = None
                
        return schema.model_validate(dummy_data)


def get_provider(provider_name: str, model: str = None) -> BaseLLMProvider:
    """Factory function to get the appropriate LLM provider."""
    provider_name = provider_name.lower()
    
    if provider_name == "openai":
        return OpenAIProvider(model=model) if model else OpenAIProvider()
    elif provider_name == "google":
        return GoogleProvider(model=model) if model else GoogleProvider()
    elif provider_name == "anthropic":
        return AnthropicProvider(model=model) if model else AnthropicProvider()
    elif provider_name == "mock":
        return MockProvider()
    else:
        raise ValueError(f"Unknown provider: {provider_name}. Supported: openai, google, anthropic, mock")

