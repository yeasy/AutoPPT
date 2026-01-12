import logging
import os
import tempfile
from typing import Optional

from tqdm import tqdm

from .config import Config
from .data_types import DeckSpec, PresentationOutline, SlideConfig, SlideLayout, SlidePlan, SlideType
from .deck_qa import DeckQA, DeckQualityReport
from .layout_selector import LayoutSelector
from .llm_provider import get_provider
from .ppt_renderer import PPTRenderer
from .researcher import Researcher
from .slide_planner import SlidePlanner
from .thumbnail import generate_thumbnails

logger = logging.getLogger(__name__)


class Generator:
    """Main presentation generator class."""

    def __init__(self, provider_name: str = "openai", api_key: Optional[str] = None, model: Optional[str] = None):
        self.llm = get_provider(provider_name, api_key=api_key, model=model)
        self.researcher = Researcher()
        self.renderer = PPTRenderer()
        self.layout_selector = LayoutSelector()
        self.slide_planner = SlidePlanner()
        self.deck_qa = DeckQA()
        self.last_quality_report = DeckQualityReport()
        self.last_deck_spec: Optional[DeckSpec] = None
        self.last_outline: Optional[PresentationOutline] = None
        self.provider_name = provider_name
        self.assets_dir = tempfile.mkdtemp(prefix="autoppt-assets-")

    def generate(
        self,
        topic: str,
        style: str = "minimalist",
        output_file: str = "output.pptx",
        slides_count: int = 10,
        language: str = "English",
        template_path: Optional[str] = None,
        create_thumbnails: bool = False,
    ) -> str:
        logger.info("Starting generation for topic: %s", topic)
        logger.info("Style: %s, Slides: %s, Language: %s", style, slides_count, language)

        logger.info("Generating presentation outline...")
        outline = self._create_outline(topic, slides_count, language)
        logger.info("Outline created: %s sections", len(outline.sections))

        return self._generate_from_outline_internal(
            outline=outline,
            topic=topic,
            style=style,
            output_file=output_file,
            language=language,
            template_path=template_path,
            create_thumbnails=create_thumbnails,
        )

    def _create_outline(self, topic: str, slides_count: int, language: str) -> PresentationOutline:
        prompt = f"""
        Create a professional hierarchical outline for a {slides_count}-slide presentation on: '{topic}'.
        Divide the presentation into 3-5 logical sections.
        Each section should contain a list of relevant slide topics.
        Ensure the structure flows logically from introduction to conclusion.
        Language: {language}.
        """
        return self.llm.generate_structure(prompt, PresentationOutline)

    def generate_outline(self, topic: str, slides_count: int = 10, language: str = "English") -> PresentationOutline:
        logger.info("Generating outline for topic: %s", topic)
        outline = self._create_outline(topic, slides_count, language)
        logger.info(
            "Outline created: %s sections, %s slides",
            len(outline.sections),
            sum(len(section.slides) for section in outline.sections),
        )
        return outline

    def outline_to_markdown(self, outline: PresentationOutline) -> str:
        lines = [f"# {outline.title}", ""]
        for index, section in enumerate(outline.sections, 1):
            lines.append(f"## {index}. {section.title}")
            lines.append("")
            for slide in section.slides:
                lines.append(f"- {slide}")
            lines.append("")
        return "\n".join(lines)

    def save_outline(self, outline: PresentationOutline, output_path: str) -> str:
        markdown = self.outline_to_markdown(outline)
        with open(output_path, "w", encoding="utf-8") as file_handle:
            file_handle.write(markdown)
        logger.info("Outline saved to: %s", output_path)
        return output_path

    def generate_from_outline(
        self,
        outline: PresentationOutline,
        topic: str,
        style: str = "minimalist",
        output_file: str = "output.pptx",
        language: str = "English",
        template_path: Optional[str] = None,
        create_thumbnails: bool = False,
    ) -> str:
        logger.info("Generating presentation from outline: %s", outline.title)
        logger.info("Style: %s, Language: %s", style, language)
        return self._generate_from_outline_internal(
            outline=outline,
            topic=topic,
            style=style,
            output_file=output_file,
            language=language,
            template_path=template_path,
            create_thumbnails=create_thumbnails,
        )

    def _generate_from_outline_internal(
        self,
        outline: PresentationOutline,
        topic: str,
        style: str,
        output_file: str,
        language: str,
        template_path: Optional[str],
        create_thumbnails: bool,
    ) -> str:
        output_dir = os.path.dirname(output_file) or Config.OUTPUT_DIR
        os.makedirs(output_dir, exist_ok=True)

        deck_spec = self.build_deck_spec(
            outline=outline,
            topic=topic,
            style=style,
            language=language,
            template_path=template_path,
        )
        self.last_outline = outline
        self.save_deck(
            deck_spec=deck_spec,
            output_file=output_file,
            create_thumbnails=create_thumbnails,
            template_path=template_path,
        )
        return output_file

    def build_deck_spec(
        self,
        outline: PresentationOutline,
        topic: str,
        style: str = "minimalist",
        language: str = "English",
        template_path: Optional[str] = None,
    ) -> DeckSpec:
        total_slides = sum(len(section.slides) for section in outline.sections)
        deck_spec = self.layout_selector.create_deck(
            outline.title,
            topic,
            style=style,
            language=language,
            template_path=template_path,
        )
        deck_spec.slides.append(self.layout_selector.title_slide(outline.title, f"Topic: {topic}"))

        with tqdm(total=total_slides, desc="Generating slides", unit="slide") as pbar:
            for section_index, section in enumerate(outline.sections):
                logger.info("Processing Section %s/%s: %s", section_index + 1, len(outline.sections), section.title)
                deck_spec.slides.append(self.layout_selector.section_slide(section.title))

                for slide_index, slide_title in enumerate(section.slides):
                    pbar.set_description(f"Slide: {slide_title[:30]}...")
                    try:
                        plan = self._plan_slide(
                            section_title=section.title,
                            slide_title=slide_title,
                            topic=topic,
                            language=language,
                        )
                        slide_config = self._build_slide(plan=plan, topic=topic, style=style, language=language)
                        image_path = self._fetch_slide_image(
                            slide_config=slide_config,
                            section_index=section_index,
                            slide_index=slide_index,
                        )
                        deck_spec.slides.append(
                            self.layout_selector.slide_from_config(
                                slide_config,
                                image_path=image_path,
                                plan=plan,
                            )
                        )
                    except Exception as exc:
                        logger.error("Error generating slide '%s': %s", slide_title, exc)
                        deck_spec.slides.append(self.layout_selector.error_slide(slide_title, str(exc)))
                    pbar.update(1)

        self._refresh_citations_slide(deck_spec)
        self.last_deck_spec = deck_spec.model_copy(deep=True)
        return deck_spec

    def save_deck(
        self,
        deck_spec: DeckSpec,
        output_file: str,
        create_thumbnails: bool = False,
        template_path: Optional[str] = None,
    ) -> str:
        self._prepare_renderer(deck_spec.style, template_path or deck_spec.template_path)
        self._finalize_presentation(deck_spec=deck_spec, output_file=output_file, create_thumbnails=create_thumbnails)
        self.last_deck_spec = deck_spec.model_copy(deep=True)
        return output_file

    def save_deck_spec(self, deck_spec: DeckSpec, output_path: str) -> str:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as file_handle:
            file_handle.write(deck_spec.model_dump_json(indent=2))
        return output_path

    def load_deck_spec(self, input_path: str) -> DeckSpec:
        with open(input_path, "r", encoding="utf-8") as file_handle:
            deck_spec = DeckSpec.model_validate_json(file_handle.read())
        self.last_deck_spec = deck_spec.model_copy(deep=True)
        return deck_spec

    def regenerate_slide(
        self,
        deck_spec: DeckSpec,
        slide_index: int,
        style: Optional[str] = None,
        language: Optional[str] = None,
        target_layout: SlideLayout | SlideType | str | None = None,
    ) -> DeckSpec:
        return self._update_slide(
            deck_spec=deck_spec,
            slide_index=slide_index,
            instruction=None,
            style=style,
            language=language,
            target_layout=target_layout,
        )

    def remix_slide(
        self,
        deck_spec: DeckSpec,
        slide_index: int,
        instruction: str = "",
        style: Optional[str] = None,
        language: Optional[str] = None,
        target_layout: SlideLayout | SlideType | str | None = None,
    ) -> DeckSpec:
        return self._update_slide(
            deck_spec=deck_spec,
            slide_index=slide_index,
            instruction=instruction or "Improve clarity and sharpen the slide structure.",
            style=style,
            language=language,
            target_layout=target_layout,
        )

    def _update_slide(
        self,
        deck_spec: DeckSpec,
        slide_index: int,
        instruction: Optional[str],
        style: Optional[str] = None,
        language: Optional[str] = None,
        target_layout: SlideLayout | SlideType | str | None = None,
    ) -> DeckSpec:
        updated_deck = deck_spec.model_copy(deep=True)
        target_slide = updated_deck.slides[slide_index]
        if not target_slide.editable or target_slide.layout in {SlideLayout.TITLE, SlideLayout.SECTION, SlideLayout.CITATIONS}:
            raise ValueError("Only generated content slides can be remixed.")

        remix_language = language or updated_deck.language
        remix_style = style or updated_deck.style
        forced_slide_type = self._coerce_slide_type(target_layout)
        plan = self._plan_slide(
            section_title=target_slide.source_section or "",
            slide_title=target_slide.source_title or target_slide.title,
            topic=updated_deck.topic,
            language=remix_language,
            remix_instruction=instruction or None,
            current_slide=target_slide,
            force_slide_type=forced_slide_type,
        )
        slide_config = self._build_slide(plan=plan, topic=updated_deck.topic, style=remix_style, language=remix_language)
        image_path = self._fetch_slide_image(
            slide_config=slide_config,
            section_index=0,
            slide_index=slide_index,
        )
        updated_deck.style = remix_style
        updated_deck.language = remix_language
        updated_deck.slides[slide_index] = self.layout_selector.slide_from_config(
            slide_config,
            image_path=image_path,
            plan=plan,
        )
        self._refresh_citations_slide(updated_deck)
        self.last_quality_report = self.deck_qa.analyze(updated_deck)
        self.last_deck_spec = updated_deck.model_copy(deep=True)
        return updated_deck

    def _prepare_renderer(self, style: str, template_path: Optional[str]) -> None:
        self.renderer = PPTRenderer(template_path=template_path)
        if not template_path:
            self.renderer.apply_style(style)

    def _plan_slide(
        self,
        section_title: str,
        slide_title: str,
        topic: str,
        language: str,
        remix_instruction: Optional[str] = None,
        current_slide=None,
        force_slide_type: SlideType | None = None,
    ) -> SlidePlan:
        return self.slide_planner.plan(
            slide_title=slide_title,
            section_title=section_title,
            topic=topic,
            language=language,
            remix_instruction=remix_instruction,
            current_slide=current_slide,
            force_slide_type=force_slide_type,
        )

    def _coerce_slide_type(self, target_layout: SlideLayout | SlideType | str | None) -> SlideType | None:
        if target_layout is None:
            return None
        if isinstance(target_layout, SlideType):
            return target_layout
        if isinstance(target_layout, SlideLayout):
            if target_layout in {SlideLayout.TITLE, SlideLayout.SECTION, SlideLayout.CITATIONS}:
                raise ValueError(f"{target_layout.value} cannot be used as a content slide target.")
            return SlideType(target_layout.value)
        return self._coerce_slide_type(SlideLayout(str(target_layout)))

    def _build_slide(
        self,
        plan: SlidePlan,
        topic: str,
        style: str,
        language: str,
    ) -> SlideConfig:
        research_queries = plan.research_queries or [f"{plan.title} {plan.section_title} {topic}".strip()]
        context = self.researcher.gather_context(research_queries, language=language)
        slide_config = self._create_slide_content(
            slide_title=plan.title,
            context=context,
            style=style,
            language=language,
            topic=topic,
            plan=plan,
        )
        return self._normalize_slide_config(slide_config, plan)

    def _normalize_slide_config(self, slide_config: SlideConfig, plan: SlidePlan) -> SlideConfig:
        return self.slide_planner.apply_plan(slide_config, plan)

    def _fetch_slide_image(
        self,
        slide_config: SlideConfig,
        section_index: int,
        slide_index: int,
    ) -> Optional[str]:
        if not slide_config.image_query:
            return None

        image_results = self.researcher.search_images(slide_config.image_query, max_results=1)
        if not image_results:
            return None

        image_url = image_results[0].get("image")
        if not image_url:
            return None

        local_path = os.path.join(self.assets_dir, f"section_{section_index}_slide_{slide_index}.jpg")
        if self.researcher.download_image(image_url, local_path):
            return local_path
        return None

    def _refresh_citations_slide(self, deck_spec: DeckSpec) -> None:
        deck_spec.slides = [slide for slide in deck_spec.slides if slide.layout != SlideLayout.CITATIONS]
        citations = self._collect_citations(deck_spec)
        if citations:
            deck_spec.slides.append(self.layout_selector.citations_slide(citations))

    def _collect_citations(self, deck_spec: DeckSpec) -> list[str]:
        ordered: dict[str, None] = {}
        for slide in deck_spec.slides:
            if slide.layout == SlideLayout.CITATIONS:
                continue
            for citation in slide.citations:
                if citation:
                    ordered[citation] = None
        return list(ordered.keys())

    def _finalize_presentation(
        self,
        deck_spec: DeckSpec,
        output_file: str,
        create_thumbnails: bool = False,
    ) -> None:
        logger.info("Finalizing presentation...")
        self._refresh_citations_slide(deck_spec)
        self.last_quality_report = self.deck_qa.analyze(deck_spec)
        self.renderer.render_deck(deck_spec)
        self.renderer.save(output_file)

        if create_thumbnails:
            logger.info("Generating thumbnails...")
            thumbnails_dir = os.path.join(os.path.dirname(output_file) or Config.OUTPUT_DIR, "thumbnails")
            generate_thumbnails(output_file, output_prefix=thumbnails_dir)

        logger.info("Saved to %s", output_file)

    def _create_slide_content(
        self,
        slide_title: str,
        context: str,
        style: str,
        language: str,
        topic: str,
        plan: SlidePlan,
    ) -> SlideConfig:
        system_prompt = f"""You are a world-class presentation architect and research analyst.

Standards:
- Each bullet must contain an insight and concrete evidence where possible
- Favor precision, named entities, dates, and specific metrics
- Prefer the planned layout unless the research clearly supports a stronger one

Style: {style}
Output Language: {language}
"""

        prompt = f"""
=== TASK ===
Create expert-level slide content for '{slide_title}'.
Presentation topic: '{topic}'
Section: '{plan.section_title}'

=== SLIDE PLAN ===
Preferred slide type: '{plan.slide_type.value}'
Objective: '{plan.objective or f"Explain why {slide_title} matters"}'
Evidence focus: {", ".join(plan.evidence_focus) if plan.evidence_focus else "Use the strongest evidence available"}
Visual intent: '{plan.visual_intent or "Use the clearest layout"}'
Reason for layout: '{plan.rationale or "Best fit for the title"}'
Remix instruction: '{plan.remix_instruction or "None"}'
Left title hint: '{plan.left_title or "Column A"}'
Right title hint: '{plan.right_title or "Column B"}'
Quote author hint: '{plan.quote_author or "Named source"}'
Quote context hint: '{plan.quote_context or plan.section_title or topic}'

=== RESEARCH CONTEXT ===
{context[:12000]}

=== SLIDE TYPE SELECTION ===
Choose exactly one:
- `statistics` when the slide is primarily about 3+ key numbers
- `chart` when the message depends on categorical trends or comparisons
- `comparison` when two named options, eras, products, or approaches are contrasted
- `two_column` when the slide should show two parallel buckets, phases, or frameworks
- `quote` when one memorable statement from a named source improves the message
- `image` when a strong visual is the main communication device
- `content` otherwise

=== QUALITY RULES ===
- `content` slides: provide 5-8 substantive bullets
- `comparison` and `two_column`: provide 3-4 concise bullets per side
- `quote`: keep the quote body short and put explanation in speaker notes
- `statistics`: provide 3-4 value/label pairs
- `chart`: include categories and values that support the stated point
- add speaker notes with extra context
- include all source URLs from the research context in `citations`

=== OUTPUT LANGUAGE: {language} ===
"""
        return self.llm.generate_structure(prompt, SlideConfig, system_prompt=system_prompt)
