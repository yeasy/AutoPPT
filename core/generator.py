import os
import shutil
import logging
import time
from typing import Optional

from tqdm import tqdm

from .llm_provider import get_provider, BaseLLMProvider, MockProvider
from .researcher import Researcher
from .ppt_renderer import PPTRenderer
from .data_types import PresentationOutline, SlideConfig, UserPresentation
from .exceptions import AutoPPTError, RateLimitError, ResearchError, RenderError
from config import Config

logger = logging.getLogger(__name__)


class Generator:
    """Main presentation generator class."""
    
    def __init__(self, provider_name: str = "openai", api_key: str = None, model: str = None):
        self.llm = get_provider(provider_name, model=model)
        self.researcher = Researcher()
        self.renderer = PPTRenderer()
        self.provider_name = provider_name

    def generate(
        self, 
        topic: str, 
        style: str = "minimalist", 
        output_file: str = "output.pptx", 
        slides_count: int = 10, 
        language: str = "English"
    ) -> str:
        """
        Generate a complete presentation on the given topic.
        
        Args:
            topic: The main topic of the presentation
            style: Visual theme (minimalist, technology, nature, creative, corporate, academic, startup, dark)
            output_file: Output file path
            slides_count: Target number of slides
            language: Output language
            
        Returns:
            Path to the generated presentation file
        """
        logger.info(f"Starting generation for topic: {topic}")
        logger.info(f"Style: {style}, Slides: {slides_count}, Language: {language}")
        
        # Ensure fresh renderer for each call
        self.renderer = PPTRenderer()
        
        # 0. Apply Style
        self.renderer.apply_style(style)
        
        # 1. Generate Outline
        logger.info("Generating presentation outline...")
        outline = self._create_outline(topic, slides_count, language)
        logger.info(f"Outline created: {len(outline.sections)} sections")
        
        # Count total slides for progress bar
        total_slides = sum(len(section.slides) for section in outline.sections)

        # 2. Research & Create Content for each section and slide
        all_citations = []
        
        # Ensure temp directory for images
        temp_dir = "temp_images"
        os.makedirs(temp_dir, exist_ok=True)
        
        self.renderer.add_title_slide(outline.title, f"Topic: {topic}")
        
        # Progress bar for sections and slides
        with tqdm(total=total_slides, desc="Generating slides", unit="slide") as pbar:
            for s_idx, section in enumerate(outline.sections):
                logger.info(f"Processing Section {s_idx+1}/{len(outline.sections)}: {section.title}")
                self.renderer.add_section_header(section.title)
                
                for i, slide_title in enumerate(section.slides):
                    pbar.set_description(f"Slide: {slide_title[:30]}...")
                    
                    # Rate limiting safety for paid APIs (skip for mock)
                    if not isinstance(self.llm, MockProvider):
                        delay = Config.API_RETRY_DELAY_SECONDS
                        logger.debug(f"Rate limit delay: {delay}s")
                        time.sleep(delay)
                    
                    try:
                        # Research
                        search_query = f"{slide_title} {section.title} {topic}"
                        context = self.researcher.gather_context([search_query])
                        
                        # Draft Content
                        slide_config = self._create_slide_content(slide_title, context, style, language, topic)
                        
                        # Fetch Image
                        image_path = None
                        if slide_config.image_query:
                            image_results = self.researcher.search_images(slide_config.image_query, max_results=1)
                            if image_results:
                                img_url = image_results[0]['image']
                                local_path = os.path.join(temp_dir, f"section_{s_idx}_slide_{i}.jpg")
                                if self.researcher.download_image(img_url, local_path):
                                    image_path = local_path
                        
                        # Render Slide
                        self.renderer.add_content_slide(
                            slide_config.title, 
                            slide_config.bullets, 
                            slide_config.speaker_notes, 
                            image_path=image_path
                        )
                        all_citations.extend(slide_config.citations)
                        
                    except Exception as e:
                        logger.error(f"Error generating slide '{slide_title}': {e}")
                        # Add a placeholder slide instead of failing
                        self.renderer.add_content_slide(
                            slide_title,
                            [f"Content generation failed: {str(e)[:50]}"],
                            "Please regenerate this slide."
                        )
                    
                    pbar.update(1)

        # 3. Finalize PPT
        logger.info("Finalizing presentation...")
        
        # Add References
        unique_citations = list(set(all_citations))
        if unique_citations:
            self.renderer.add_citations_slide(unique_citations)
            
        self.renderer.save(output_file)
        
        # Cleanup temp images
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            
        logger.info(f"✅ Done! Saved to {output_file}")
        return output_file

    def _create_outline(self, topic: str, slides_count: int, language: str) -> PresentationOutline:
        """Generate a hierarchical outline for the presentation."""
        prompt = f"""
        Create a professional hierarchical outline for a {slides_count}-slide presentation on: '{topic}'.
        Divide the presentation into 3-5 logical sections (chapters).
        Each section should contain a list of relevant slide topics.
        Ensure the structure flows logically from introduction to conclusion.
        Language: {language}.
        """
        return self.llm.generate_structure(prompt, PresentationOutline)

    def _create_slide_content(
        self, 
        slide_title: str, 
        context: str, 
        style: str, 
        language: str, 
        topic: str
    ) -> SlideConfig:
        """Generate content for a single slide using research context."""
        system_prompt = f"""You are a top-tier research analyst and professional presentation architect. 
Style: {style}. 
Your objective is to transform raw data into high-density, substantive insights (Dry Goods / 干货). 
Output Language: {language}."""

        prompt = f"""
        Objective: Create substantive, authoritative content for a slide titled: '{slide_title}' as part of a presentation on '{topic}'.
        
        Research Context (from Web/Wikipedia):
        {context[:8000]}
        
        Mandatory Content Standards:
        1. NO FLUFF. Avoid generic or obvious statements.
        2. DATA-RICH: Include specific technical specifications, historical dates, statistical figures, or key academic concepts found in the context.
        3. WIKIPEDIA QUALITY: Each bullet point must convey a clear, factual, and significant piece of information.
        4. STRUCTURE: 3-5 detailed bullet points. Use sub-bullets if necessary to explain complex points.
        5. LANGUAGE: {language}.
        6. SPEAKER NOTES: 3-4 professional sentences expanding on the data-driven points, providing additional background or analysis.
        7. IMAGE QUERY: A highly specific artistic keyword (e.g., '4k macro photograph of integrated circuit with light trails' not 'technology').
        8. CITATIONS: List the exact source URLs from the context for every factual claim.
        """
        return self.llm.generate_structure(prompt, SlideConfig, system_prompt=system_prompt)

