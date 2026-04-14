import logging

from .data_types import DeckSpec, SlideConfig, SlideLayout, SlidePlan, SlideSpec, SlideType

logger = logging.getLogger(__name__)


class LayoutSelector:
    """Translate generated slide content into renderer-facing slide specs."""

    def create_deck(
        self,
        title: str,
        topic: str,
        style: str = "minimalist",
        language: str = "English",
        template_path: str | None = None,
    ) -> DeckSpec:
        return DeckSpec(title=title, topic=topic, style=style, language=language, template_path=template_path, slides=[])

    def title_slide(self, title: str, subtitle: str = "") -> SlideSpec:
        return SlideSpec(layout=SlideLayout.TITLE, title=title, subtitle=subtitle)

    def section_slide(self, title: str) -> SlideSpec:
        return SlideSpec(layout=SlideLayout.SECTION, title=title)

    @staticmethod
    def _safe_layout_from_plan(plan: SlidePlan | None) -> SlideLayout | None:
        if plan is None:
            return None
        try:
            return SlideLayout(plan.slide_type.value)
        except ValueError:
            return None

    def _split_bullets_into_columns(self, bullets: list[str]) -> tuple[list[str], list[str]]:
        if len(bullets) < 2:
            return bullets, []
        midpoint = max(1, len(bullets) // 2)
        return bullets[:midpoint], bullets[midpoint:]

    def slide_from_config(
        self,
        slide_config: SlideConfig,
        image_path: str | None = None,
        plan: SlidePlan | None = None,
    ) -> SlideSpec:
        metadata = {
            "editable": plan is not None,
            "source_topic": plan.topic if plan else None,
            "source_section": plan.section_title if plan else None,
            "source_title": plan.title if plan else slide_config.title,
            "planned_layout": self._safe_layout_from_plan(plan),
            "layout_rationale": plan.rationale if plan else None,
            "plan": plan,
            "source_config": slide_config,
        }

        if slide_config.slide_type == SlideType.STATISTICS and slide_config.statistics:
            return SlideSpec(
                layout=SlideLayout.STATISTICS,
                title=slide_config.title,
                bullets=slide_config.bullets,
                speaker_notes=slide_config.speaker_notes,
                citations=slide_config.citations,
                statistics=slide_config.statistics,
                **metadata,
            )

        if slide_config.slide_type == SlideType.QUOTE:
            if slide_config.quote_text and slide_config.quote_author:
                return self.quote_slide(
                    title=slide_config.title,
                    quote_text=slide_config.quote_text,
                    quote_author=slide_config.quote_author,
                    quote_context=slide_config.quote_context or "",
                    speaker_notes=slide_config.speaker_notes,
                    citations=slide_config.citations,
                    **metadata,
                )
            logger.warning("QUOTE slide '%s' missing quote_text or author, demoting to CONTENT", slide_config.title)

        if slide_config.slide_type == SlideType.COMPARISON:
            if slide_config.left_bullets or slide_config.right_bullets:
                left_b = slide_config.left_bullets or []
                right_b = slide_config.right_bullets or []
            else:
                left_b, right_b = self._split_bullets_into_columns(slide_config.bullets)
            if not left_b or not right_b:
                logger.warning("COMPARISON slide '%s' has empty column(s), demoting to CONTENT", slide_config.title)
            else:
                return self.comparison_slide(
                    title=slide_config.title,
                    item_a={
                        "name": slide_config.left_title or "Option A",
                        "points": left_b,
                    },
                    item_b={
                        "name": slide_config.right_title or "Option B",
                        "points": right_b,
                    },
                    speaker_notes=slide_config.speaker_notes,
                    citations=slide_config.citations,
                    **metadata,
                )

        if slide_config.slide_type == SlideType.TWO_COLUMN:
            if slide_config.left_bullets or slide_config.right_bullets:
                left_b = slide_config.left_bullets or []
                right_b = slide_config.right_bullets or []
            else:
                left_b, right_b = self._split_bullets_into_columns(slide_config.bullets)
            if not left_b or not right_b:
                logger.warning("TWO_COLUMN slide '%s' has empty column(s), demoting to CONTENT", slide_config.title)
            else:
                return self.two_column_slide(
                    title=slide_config.title,
                    left_bullets=left_b,
                    right_bullets=right_b,
                    left_title=slide_config.left_title or "Column A",
                    right_title=slide_config.right_title or "Column B",
                    speaker_notes=slide_config.speaker_notes,
                    citations=slide_config.citations,
                    **metadata,
                )

        if slide_config.slide_type == SlideType.IMAGE:
            return SlideSpec(
                layout=SlideLayout.IMAGE,
                title=slide_config.title,
                bullets=slide_config.bullets,
                speaker_notes=slide_config.speaker_notes,
                citations=slide_config.citations,
                image_path=image_path,
                image_caption=slide_config.bullets[0] if slide_config.bullets else "",
                **metadata,
            )

        if slide_config.slide_type == SlideType.CHART:
            if slide_config.chart_data:
                return SlideSpec(
                    layout=SlideLayout.CHART,
                    title=slide_config.title,
                    bullets=slide_config.bullets,
                    speaker_notes=slide_config.speaker_notes,
                    citations=slide_config.citations,
                    chart_data=slide_config.chart_data,
                    **metadata,
                )
            logger.warning("CHART slide '%s' missing chart_data, demoting to CONTENT", slide_config.title)

        return SlideSpec(
            layout=SlideLayout.CONTENT,
            title=slide_config.title,
            bullets=slide_config.bullets,
            speaker_notes=slide_config.speaker_notes,
            citations=slide_config.citations,
            image_path=image_path,
            **metadata,
        )

    def two_column_slide(
        self,
        title: str,
        left_bullets: list[str],
        right_bullets: list[str],
        left_title: str = "",
        right_title: str = "",
        speaker_notes: str | None = None,
        citations: list[str] | None = None,
        **metadata,
    ) -> SlideSpec:
        return SlideSpec(
            layout=SlideLayout.TWO_COLUMN,
            title=title,
            left_bullets=left_bullets,
            right_bullets=right_bullets,
            left_title=left_title,
            right_title=right_title,
            speaker_notes=speaker_notes,
            citations=citations or [],
            **metadata,
        )

    def comparison_slide(
        self,
        title: str,
        item_a: dict[str, list[str] | str],
        item_b: dict[str, list[str] | str],
        speaker_notes: str | None = None,
        citations: list[str] | None = None,
        **metadata,
    ) -> SlideSpec:
        return SlideSpec(
            layout=SlideLayout.COMPARISON,
            title=title,
            left_title=str(item_a.get("name", "Option A")),
            right_title=str(item_b.get("name", "Option B")),
            left_bullets=self._coerce_points(item_a.get("points", [])),
            right_bullets=self._coerce_points(item_b.get("points", [])),
            speaker_notes=speaker_notes,
            citations=citations or [],
            **metadata,
        )

    def quote_slide(
        self,
        title: str,
        quote_text: str,
        quote_author: str,
        quote_context: str = "",
        speaker_notes: str | None = None,
        citations: list[str] | None = None,
        **metadata,
    ) -> SlideSpec:
        return SlideSpec(
            layout=SlideLayout.QUOTE,
            title=title,
            quote_text=quote_text,
            quote_author=quote_author,
            quote_context=quote_context,
            speaker_notes=speaker_notes,
            citations=citations or [],
            **metadata,
        )

    def citations_slide(self, citations: list[str]) -> SlideSpec:
        return SlideSpec(layout=SlideLayout.CITATIONS, title="References", citations=citations)

    def error_slide(self, slide_title: str, error_message: str) -> SlideSpec:
        return SlideSpec(
            layout=SlideLayout.CONTENT,
            title=slide_title,
            bullets=[f"Content generation failed: {error_message[:50]}{'...' if len(error_message) > 50 else ''}"],
            speaker_notes="Please regenerate this slide.",
        )

    def remix_slide(self, slide_spec: SlideSpec, target_layout: SlideLayout) -> SlideSpec:
        metadata = {
            "editable": slide_spec.editable,
            "source_topic": slide_spec.source_topic,
            "source_section": slide_spec.source_section,
            "source_title": slide_spec.source_title,
            "planned_layout": target_layout,
            "layout_rationale": slide_spec.layout_rationale,
            "plan": slide_spec.plan,
            "source_config": slide_spec.source_config,
        }

        if target_layout == SlideLayout.CONTENT:
            return SlideSpec(
                layout=SlideLayout.CONTENT,
                title=slide_spec.title,
                bullets=self._flatten_slide_bullets(slide_spec),
                speaker_notes=slide_spec.speaker_notes,
                citations=slide_spec.citations,
                image_path=slide_spec.image_path,
                **metadata,
            )

        if target_layout == SlideLayout.TWO_COLUMN:
            left_bullets, right_bullets = self._columns_for_slide(slide_spec)
            return self.two_column_slide(
                title=slide_spec.title,
                left_bullets=left_bullets,
                right_bullets=right_bullets,
                left_title=slide_spec.left_title or "Core Ideas",
                right_title=slide_spec.right_title or "Execution Moves",
                speaker_notes=slide_spec.speaker_notes,
                citations=slide_spec.citations,
                **metadata,
            )

        if target_layout == SlideLayout.COMPARISON:
            left_bullets, right_bullets = self._columns_for_slide(slide_spec)
            return self.comparison_slide(
                title=slide_spec.title,
                item_a={"name": slide_spec.left_title or "Current State", "points": left_bullets},
                item_b={"name": slide_spec.right_title or "Future State", "points": right_bullets},
                speaker_notes=slide_spec.speaker_notes,
                citations=slide_spec.citations,
                **metadata,
            )

        if target_layout == SlideLayout.QUOTE:
            quote_text = slide_spec.quote_text or self._quote_text_for_slide(slide_spec)
            quote_author = slide_spec.quote_author or slide_spec.source_title or "AutoPPT Research Desk"
            return self.quote_slide(
                title=slide_spec.title,
                quote_text=quote_text,
                quote_author=quote_author,
                quote_context=slide_spec.quote_context or slide_spec.source_section or "",
                speaker_notes=slide_spec.speaker_notes,
                citations=slide_spec.citations,
                **metadata,
            )

        logger.warning("remix_slide: unsupported target layout %s, returning copy", target_layout.value)
        return slide_spec.model_copy(deep=True)

    @staticmethod
    def _coerce_points(points: list[str] | str | None) -> list[str]:
        """Ensure points is a list of strings, not a bare string iterated char-by-char."""
        if points is None:
            return []
        if isinstance(points, str):
            return [points]
        return [str(p) for p in points]

    def _columns_for_slide(self, slide_spec: SlideSpec) -> tuple[list[str], list[str]]:
        if slide_spec.left_bullets and slide_spec.right_bullets:
            return slide_spec.left_bullets, slide_spec.right_bullets
        return self._split_bullets_into_columns(self._flatten_slide_bullets(slide_spec))

    def _flatten_slide_bullets(self, slide_spec: SlideSpec) -> list[str]:
        if slide_spec.bullets:
            return slide_spec.bullets
        if slide_spec.left_bullets or slide_spec.right_bullets:
            return [*(slide_spec.left_bullets or []), *(slide_spec.right_bullets or [])]
        if slide_spec.quote_text:
            return [slide_spec.quote_text]
        if slide_spec.statistics:
            return [f"{stat.label}: {stat.value}" for stat in slide_spec.statistics]
        if slide_spec.chart_data:
            return [
                f"{category}: {value}"
                for category, value in zip(slide_spec.chart_data.categories, slide_spec.chart_data.values)
            ]
        return []

    def _quote_text_for_slide(self, slide_spec: SlideSpec) -> str:
        bullets = self._flatten_slide_bullets(slide_spec)
        if bullets:
            return bullets[0]
        return slide_spec.title
