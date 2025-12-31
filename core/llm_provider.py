from abc import ABC, abstractmethod
from typing import List, Type, TypeVar
from pydantic import BaseModel
from openai import OpenAI
import os
from google import genai
from google.genai import types

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
                    print(f"Rate limit hit, retrying in 60s... (Attempt {attempt+1}/3)")
                    time.sleep(60)
                else:
                    raise e

class MockProvider(BaseLLMProvider):
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
    if provider_name == "openai":
        return OpenAIProvider(model=model) if model else OpenAIProvider()
    elif provider_name == "google":
        return GoogleProvider(model=model) if model else GoogleProvider()
    elif provider_name == "mock":
        return MockProvider()
    # Add other providers here later
    raise ValueError(f"Unknown provider: {provider_name}")
