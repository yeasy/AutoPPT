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
        
        # Ensure fresh renderer for each call
        self.renderer = PPTRenderer()
        
        # 0. Apply Style
        self.renderer.apply_style(style)
        
        # 1. Generate Outline
        print("Generating Outline...")
        outline = self._create_outline(topic, slides_count, language)
        print(f"Outline created: {len(outline.sections)} sections.")

        # 2. Research & Create Content for each section and slide
        all_citations = []
        
        # Ensure temp directory for images
        temp_dir = "temp_images"
        os.makedirs(temp_dir, exist_ok=True)
        
        self.renderer.add_title_slide(outline.title, f"Topic: {topic}")
        
        for s_idx, section in enumerate(outline.sections):
            print(f"Processing Section {s_idx+1}/{len(outline.sections)}: {section.title}")
            self.renderer.add_section_header(section.title)
            
            for i, slide_title in enumerate(section.slides):
                print(f"  Slide {i+1}/{len(section.slides)}: {slide_title}")
                
                # Rate limiting safety for free tier (skip for mock)
                import time
                from .llm_provider import MockProvider
                if not isinstance(self.llm, MockProvider):
                    print("Wait 60s for rate limit...")
                    time.sleep(60)
                
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
                self.renderer.add_content_slide(slide_config.title, slide_config.bullets, slide_config.speaker_notes, image_path=image_path)
                all_citations.extend(slide_config.citations)

        # 3. Finalize PPT
        print("Finalizing Presentation...")
        # Add References
        unique_citations = list(set(all_citations))
        if unique_citations:
            self.renderer.add_citations_slide(unique_citations)
            
        self.renderer.save(output_file)
        
        # Cleanup temp images
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            
        print(f"Done! Saved to {output_file}")

    def _create_outline(self, topic: str, slides_count: int, language: str) -> PresentationOutline:
        prompt = f"""
        Create a professional hierarchical outline for a {slides_count}-slide presentation on: '{topic}'.
        Divide the presentation into 3-5 logical sections (chapters).
        Each section should contain a list of relevant slide topics.
        Ensure the structure flows logically from introduction to conclusion.
        Language: {language}.
        """
        return self.llm.generate_structure(prompt, PresentationOutline)

    def _create_slide_content(self, slide_title: str, context: str, style: str, language: str, topic: str) -> SlideConfig:
        system_prompt = f"You are a top-tier research analyst and professional presentation architect. Style: {style}. Your objective is to transform raw data into high-density, substantive insights (Dry Goods / 干货). Output Language: {language}."
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
