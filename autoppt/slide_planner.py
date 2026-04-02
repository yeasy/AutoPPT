import re

from .data_types import SlideConfig, SlidePlan, SlideSpec, SlideType


class SlidePlanner:
    """Heuristic planner that nudges the generator toward intentional layouts."""

    _COMPARISON_PAIRS = (
        ("current", "future"),
        ("today", "tomorrow"),
        ("benefits", "risks"),
        ("opportunities", "challenges"),
        ("pros", "cons"),
        ("legacy", "modern"),
        ("before", "after"),
    )

    _LAYOUT_TO_TYPE = {
        "comparison": SlideType.COMPARISON,
        "two_column": SlideType.TWO_COLUMN,
        "quote": SlideType.QUOTE,
    }

    def plan(
        self,
        slide_title: str,
        section_title: str,
        topic: str,
        language: str = "English",
        context: str = "",
        remix_instruction: str | None = None,
        current_slide: SlideSpec | None = None,
        force_slide_type: SlideType | None = None,
    ) -> SlidePlan:
        slide_title = str(slide_title or "").strip() or section_title or "Untitled Slide"
        title_lower = slide_title.lower()
        context_lower = (context or "").lower()
        remix_lower = (remix_instruction or "").lower()
        plan = SlidePlan(
            title=slide_title,
            section_title=section_title,
            topic=topic,
            language=language,
            slide_type=SlideType.CONTENT,
            objective=f"Explain why {slide_title} matters for {topic}.",
            evidence_focus=[s.strip() for s in (section_title, topic, slide_title) if s and s.strip()],
            research_queries=[
                f"{slide_title} {section_title} {topic}".strip(),
                f"{topic} {slide_title} latest evidence".strip(),
            ],
            rationale="Default content slide for explanatory material.",
            remix_instruction=remix_instruction,
        )

        if current_slide:
            plan.visual_intent = current_slide.layout.value
            if not remix_instruction:
                plan.rationale = f"Preserve the existing {current_slide.layout.value} layout unless a better fit is obvious."

        if force_slide_type is not None:
            plan.slide_type = force_slide_type
            plan.layout_locked = True
            plan.rationale = f"Explicitly requested {force_slide_type.value} layout."
            self._fill_layout_hints(plan, slide_title, section_title, topic)
            return plan

        if any(token in remix_lower for token in ("quote", "principle", "vision", "mantra")):
            plan.slide_type = SlideType.QUOTE
            plan.quote_author = current_slide.quote_author if current_slide else "Industry Perspective"
            plan.quote_context = current_slide.quote_context if current_slide else (section_title or topic)
            plan.visual_intent = "Use one memorable quote with clean whitespace."
            plan.rationale = "Remix instruction explicitly requests a quote-centric slide."
            return plan

        if any(token in remix_lower for token in ("compare", "comparison", "versus", "tradeoff")) or re.search(r"\bvs\b", remix_lower):
            plan.slide_type = SlideType.COMPARISON
            self._fill_layout_hints(plan, slide_title, section_title, topic)
            plan.visual_intent = "Show two contrasted sides with parallel bullets."
            plan.rationale = "Remix instruction explicitly requests a comparison."
            return plan

        if any(token in remix_lower for token in ("two column", "two-column", "framework", "pillars", "split")):
            plan.slide_type = SlideType.TWO_COLUMN
            self._fill_layout_hints(plan, slide_title, section_title, topic)
            plan.visual_intent = "Split the slide into two balanced columns."
            plan.rationale = "Remix instruction explicitly requests a two-column layout."
            return plan

        if self._looks_like_quote(title_lower, context_lower):
            plan.slide_type = SlideType.QUOTE
            plan.quote_author = "Industry Perspective"
            plan.quote_context = section_title or topic
            plan.visual_intent = "Use one memorable quote with clean whitespace."
            plan.rationale = "Title suggests a principle, vision, or memorable statement."
            return plan

        comparison_titles = self._infer_comparison_titles(slide_title)
        if comparison_titles:
            plan.slide_type = SlideType.COMPARISON
            plan.left_title, plan.right_title = comparison_titles
            plan.visual_intent = "Show two contrasted sides with parallel bullets."
            plan.rationale = "Title implies a direct contrast between two named sides."
            return plan

        if self._looks_like_chart(title_lower, context_lower):
            plan.slide_type = SlideType.CHART
            plan.visual_intent = "Use a chart to show the trend or categorical comparison."
            plan.rationale = "Title and context suggest the message depends on a visible trend or benchmark."
            return plan

        if self._looks_like_statistics(title_lower, context_lower):
            plan.slide_type = SlideType.STATISTICS
            plan.visual_intent = "Lead with a compact set of high-signal numbers."
            plan.rationale = "Title and context suggest key metrics should dominate the slide."
            return plan

        if self._looks_like_two_column(title_lower):
            plan.slide_type = SlideType.TWO_COLUMN
            titles = self._infer_two_column_titles(slide_title)
            if titles:
                plan.left_title, plan.right_title = titles
            plan.visual_intent = "Split the slide into two balanced columns."
            plan.rationale = "Title suggests a framework, phases, or parallel buckets."
            return plan

        if self._looks_like_image(title_lower):
            plan.slide_type = SlideType.IMAGE
            plan.visual_intent = "Use a strong visual with minimal supporting text."
            plan.rationale = "Title suggests a product, scene, or visual showcase."
            return plan

        if current_slide and current_slide.layout is not None and current_slide.layout.value in self._LAYOUT_TO_TYPE:
            plan.slide_type = self._LAYOUT_TO_TYPE[current_slide.layout.value]
            plan.left_title = current_slide.left_title
            plan.right_title = current_slide.right_title
            plan.quote_author = current_slide.quote_author
            plan.quote_context = current_slide.quote_context
            plan.rationale = f"Preserve the existing {current_slide.layout.value} layout as the remix baseline."

        return plan

    def apply_plan(self, slide_config: SlideConfig, plan: SlidePlan) -> SlideConfig:
        """Normalize slide config using the precomputed plan when the model is underspecified."""
        data = slide_config.model_dump()

        inferred_type = self._infer_from_content(slide_config)
        effective_type = inferred_type or slide_config.slide_type
        if plan.layout_locked:
            effective_type = plan.slide_type
        elif effective_type == SlideType.CONTENT and plan.slide_type != SlideType.CONTENT:
            effective_type = plan.slide_type

        if effective_type == SlideType.QUOTE:
            quote_text = slide_config.quote_text or (self._first_sentence(slide_config.bullets[0]) if slide_config.bullets else None)
            if quote_text and (slide_config.quote_author or plan.quote_author):
                data["slide_type"] = SlideType.QUOTE
                data["quote_text"] = quote_text
                data["quote_author"] = slide_config.quote_author or plan.quote_author
                data["quote_context"] = slide_config.quote_context or plan.quote_context
            else:
                data["slide_type"] = SlideType.CONTENT

        elif effective_type == SlideType.COMPARISON:
            left_bullets, right_bullets = self._split_bullets(slide_config)
            data["slide_type"] = SlideType.COMPARISON
            data["left_title"] = slide_config.left_title or plan.left_title or "Option A"
            data["right_title"] = slide_config.right_title or plan.right_title or "Option B"
            data["left_bullets"] = slide_config.left_bullets or left_bullets
            data["right_bullets"] = slide_config.right_bullets or right_bullets

        elif effective_type == SlideType.TWO_COLUMN:
            left_bullets, right_bullets = self._split_bullets(slide_config)
            data["slide_type"] = SlideType.TWO_COLUMN
            data["left_title"] = slide_config.left_title or plan.left_title or "Column A"
            data["right_title"] = slide_config.right_title or plan.right_title or "Column B"
            data["left_bullets"] = slide_config.left_bullets or left_bullets
            data["right_bullets"] = slide_config.right_bullets or right_bullets

        else:
            data["slide_type"] = effective_type

        return SlideConfig.model_validate(data)

    def _looks_like_quote(self, title_lower: str, context_lower: str) -> bool:
        quote_tokens = ("quote", "vision", "principle", "leadership", "philosophy", "mantra", "lesson")
        if any(token in title_lower for token in quote_tokens):
            return True
        has_quote = any(q in context_lower for q in ('"', '\u201c', '\u201d'))
        return has_quote and "\u2014" in context_lower

    def _looks_like_two_column(self, title_lower: str) -> bool:
        two_column_tokens = (
            "framework",
            "pillars",
            "dimensions",
            "roadmap",
            "phases",
            "checklist",
            "strategy",
            "operating model",
            "playbook",
            "workflow",
        )
        return any(token in title_lower for token in two_column_tokens)

    def _looks_like_statistics(self, title_lower: str, context_lower: str) -> bool:
        stat_tokens = ("metrics", "kpi", "benchmarks", "numbers", "snapshot", "scorecard", "market size")
        if any(token in title_lower for token in stat_tokens):
            return True
        return len(re.findall(r"\b\d+(?:\.\d+)?%?\b", context_lower)) >= 4 and any(
            token in context_lower for token in ("revenue", "growth", "share", "adoption", "margin", "users")
        )

    def _looks_like_chart(self, title_lower: str, context_lower: str) -> bool:
        chart_tokens = ("trend", "growth", "forecast", "timeline", "trajectory", "adoption curve", "comparison by")
        if any(token in title_lower for token in chart_tokens):
            return True
        return any(token in context_lower for token in ("year-over-year", "quarter", "trend", "forecast")) and len(
            re.findall(r"\b20\d{2}\b", context_lower)
        ) >= 2

    def _looks_like_image(self, title_lower: str) -> bool:
        image_tokens = ("showcase", "demo", "scene", "photo", "gallery", "portfolio")
        return any(token in title_lower for token in image_tokens)

    def _infer_comparison_titles(self, slide_title: str) -> tuple[str, str] | None:
        compact = re.sub(r"\s+", " ", slide_title.strip())
        if " vs " in compact.lower() or " vs." in compact.lower():
            left, right = re.split(r"\bvs\.?\s*", compact, maxsplit=1, flags=re.IGNORECASE)
            left = left.strip(" :-.")
            right = right.strip(" :-.")
            if left and right:
                return left, right

        lower = compact.lower()
        for left, right in self._COMPARISON_PAIRS:
            if re.search(rf"\b{re.escape(left)}\b", lower) and re.search(rf"\b{re.escape(right)}\b", lower):
                return left.title(), right.title()

        comparison_tokens = ("compare", "comparison", "tradeoff", "versus", "benefits and risks")
        if any(token in lower for token in comparison_tokens):
            return "Current Approach", "Alternative Approach"
        return None

    def _infer_two_column_titles(self, slide_title: str) -> tuple[str, str] | None:
        lower = slide_title.lower()
        for left, right in self._COMPARISON_PAIRS:
            if re.search(rf"\b{re.escape(left)}\b", lower) and re.search(rf"\b{re.escape(right)}\b", lower):
                return left.title(), right.title()
        if "framework" in lower or "pillars" in lower:
            return "Core Elements", "Execution Moves"
        if "roadmap" in lower or "phases" in lower:
            return "Near Term", "Next Phase"
        return None

    def _infer_from_content(self, slide_config: SlideConfig) -> SlideType | None:
        if slide_config.quote_text and slide_config.quote_author:
            return SlideType.QUOTE
        if slide_config.statistics:
            return SlideType.STATISTICS
        if slide_config.chart_data:
            return SlideType.CHART
        if slide_config.image_query and not slide_config.bullets:
            return SlideType.IMAGE
        if slide_config.left_bullets and slide_config.right_bullets:
            if self._infer_comparison_titles(slide_config.title):
                return SlideType.COMPARISON
            return SlideType.TWO_COLUMN
        return None

    def _split_bullets(self, slide_config: SlideConfig) -> tuple[list[str], list[str]]:
        if slide_config.left_bullets and slide_config.right_bullets:
            return slide_config.left_bullets, slide_config.right_bullets
        if len(slide_config.bullets) < 2:
            return slide_config.bullets, []
        midpoint = max(1, len(slide_config.bullets) // 2)
        return slide_config.bullets[:midpoint], slide_config.bullets[midpoint:]

    def _first_sentence(self, text: str) -> str:
        return re.split(r"(?<=[.!?])\s+", text.strip(), maxsplit=1)[0].strip()

    def _fill_layout_hints(self, plan: SlidePlan, slide_title: str, section_title: str, topic: str) -> None:
        if plan.slide_type == SlideType.QUOTE:
            plan.quote_author = plan.quote_author or "Industry Perspective"
            plan.quote_context = plan.quote_context or section_title or topic
        if plan.slide_type == SlideType.COMPARISON:
            titles = self._infer_comparison_titles(slide_title)
            if titles:
                plan.left_title, plan.right_title = titles
            plan.left_title = plan.left_title or "Current State"
            plan.right_title = plan.right_title or "Alternative"
        if plan.slide_type == SlideType.TWO_COLUMN:
            titles = self._infer_two_column_titles(slide_title)
            if titles:
                plan.left_title, plan.right_title = titles
            plan.left_title = plan.left_title or "Core Ideas"
            plan.right_title = plan.right_title or "Execution Moves"
