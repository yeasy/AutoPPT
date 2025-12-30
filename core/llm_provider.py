from abc import ABC, abstractmethod
from typing import List, Type, TypeVar
from pydantic import BaseModel
from openai import OpenAI
import os
import google.generativeai as genai
import json


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
    def __init__(self, api_key: str = None, model: str = "gemini-3-flash"):
        api_key = api_key or os.getenv("GOOGLE_API_KEY")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)

    def generate_text(self, prompt: str, system_prompt: str = "") -> str:
        combined_prompt = f"{system_prompt}\n\n{prompt}"
        response = self.model.generate_content(combined_prompt)
        return response.text

    def generate_structure(self, prompt: str, schema: Type[T], system_prompt: str = "") -> T:
        # Avoid response_schema if it's causing issues, use prompt instead
        format_instructions = f"\n\nIMPORTANT: Return ONLY a valid JSON object matching this schema: {schema.model_json_schema()}"
        combined_prompt = f"{system_prompt}\n\n{prompt}{format_instructions}"
        
        response = self.model.generate_content(
            combined_prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json"
            )
        )
        
        # Clean up response text in case of markdown blocks
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        
        return schema.model_validate_json(text.strip())

class MockProvider(BaseLLMProvider):
    def generate_text(self, prompt: str, system_prompt: str = "") -> str:
        return f"Mock response for: {prompt[:50]}..."

    def generate_structure(self, prompt: str, schema: Type[T], system_prompt: str = "") -> T:
        # Generate dummy data based on schema, including nested models
        from .data_types import PresentationSection
        
        dummy_data = {}
        for field_name, field in schema.model_fields.items():
            # Basic type handling
            if field.annotation == str:
                dummy_data[field_name] = f"Mock {field_name}"
            elif field.annotation == List[str]:
                dummy_data[field_name] = [f"Mock Item {i}" for i in range(3)]
            elif field.annotation == List[PresentationSection]:
                dummy_data[field_name] = [
                    PresentationSection(title=f"Mock Section {i}", slides=[f"Slide {i}.{j}" for j in range(2)])
                    for i in range(3)
                ]
            else:
                dummy_data[field_name] = None
                
        return schema.model_validate(dummy_data)

def get_provider(provider_name: str, model: str = None) -> BaseLLMProvider:
    if provider_name == "openai":
        return OpenAIProvider(model=model) if model else OpenAIProvider()
    elif provider_name == "google":
        return GoogleProvider(model=model) if model else GoogleProvider()
    elif provider_name == "mock":
        return MockProvider()
    # Add other providers here later
    raise ValueError(f"Unknown provider: {provider_name}")
