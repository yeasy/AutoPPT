from .llm_provider import get_provider, BaseLLMProvider
from .researcher import Researcher
from .ppt_renderer import PPTRenderer
from .data_types import PresentationOutline, SlideConfig, UserPresentation
import os

class Generator:
    def __init__(self, provider_name: str = "openai", api_key: str = None, model: str = None):
        self.llm = get_provider(provider_name, model=model)
        self.researcher = Researcher()
        self.renderer = PPTRenderer()

    def generate(self, topic: str, style: str = "minimalist", output_file: str = "output.pptx", slides_count: int = 10, language: str = "English"):
        print(f"--- Starting Generation for topic: {topic} ---")
        
        # 1. Generate Outline
        print("Generating Outline...")
        outline = self._create_outline(topic, slides_count, language)
        print(f"Outline created: {len(outline.slides)} slides.")

        # 2. Research & Create Content for each slide
        slides_content = []
        all_citations = []
        
        for i, slide_title in enumerate(outline.slides):
            print(f"Processing Slide {i+1}/{len(outline.slides)}: {slide_title}")
            
            # Rate limiting safety for free tier (skip for mock)
            import time
            from .llm_provider import MockProvider
            if i > 0 and not isinstance(self.llm, MockProvider):
                print("Wait 40s for rate limit...")
                time.sleep(40)
            
            # Research
            search_query = f"{slide_title} {topic}"
            context = self.researcher.gather_context([search_query])
            
            # Draft Content
            slide_config = self._create_slide_content(slide_title, context, style, language)
            slides_content.append(slide_config)
            all_citations.extend(slide_config.citations)

        # 3. Render PPT
        print("Rendering Presentation...")
        self.renderer.add_title_slide(outline.title, f"Generated for: {topic}")
        
        for slide in slides_content:
            self.renderer.add_content_slide(slide.title, slide.bullets, slide.speaker_notes)
            
        # Add References
        unique_citations = list(set(all_citations))
        if unique_citations:
            self.renderer.add_citations_slide(unique_citations)
            
        self.renderer.save(output_file)
        print(f"Done! Saved to {output_file}")

    def _create_outline(self, topic: str, slides_count: int, language: str) -> PresentationOutline:
        prompt = f"Create a detailed {slides_count}-slide presentation outline for the topic: '{topic}'. Returns the structure with a title and list of slide topics. Language: {language}."
        return self.llm.generate_structure(prompt, PresentationOutline)

    def _create_slide_content(self, slide_title: str, context: str, style: str, language: str) -> SlideConfig:
        system_prompt = f"You are a professional presentation designer. Style: {style}. Use the provided context to write accurate content. Output Language: {language}."
        prompt = f"""
        Create content for a slide titled: '{slide_title}'.
        
        Context found from search:
        {context[:8000]} # Limit context window just in case
        
        Requirements:
        - 3-5 concise bullet points.
        - Professional tone.
        - Language: {language}.
        - Add speaker notes.
        - Include any relevant source URLs from the context in the citations list.
        """
        return self.llm.generate_structure(prompt, SlideConfig, system_prompt=system_prompt)
