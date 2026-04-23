from __future__ import annotations

import logging
from pydantic import BaseModel, Field

from .data_types import DeckSpec, SlideLayout, SlideSpec

logger = logging.getLogger(__name__)


class DeckIssue(BaseModel):
    code: str = Field(description="Stable issue code")
    message: str = Field(description="Human-readable issue message")
    slide_index: int = Field(description="1-based slide index, or 0 for deck-level issues")
    slide_title: str = Field(description="Slide title at the time of analysis")


class DeckQualityReport(BaseModel):
    issues: list[DeckIssue] = Field(default_factory=list)

    @property
    def has_issues(self) -> bool:
        return bool(self.issues)


class DeckQA:
    """Lightweight linting for normalized deck specs."""

    def analyze(self, deck_spec: DeckSpec) -> DeckQualityReport:
        issues: list[DeckIssue] = []
        seen_titles: dict[str, int] = {}

        if not deck_spec.slides:
            logger.warning("Deck QA: deck has no slides")
            issues.append(
                DeckIssue(
                    code="empty_deck",
                    message="Deck has no slides.",
                    slide_index=0,
                    slide_title="",
                )
            )
            return DeckQualityReport(issues=issues)

        for index, slide in enumerate(deck_spec.slides, start=1):
            normalized_title = slide.title.strip().lower()
            if normalized_title:
                previous_index = seen_titles.get(normalized_title)
                if previous_index is not None:
                    issues.append(
                        DeckIssue(
                            code="duplicate_title",
                            message=f"Duplicate slide title also appears on slide {previous_index}.",
                            slide_index=index,
                            slide_title=slide.title,
                        )
                    )
                else:
                    seen_titles[normalized_title] = index

            issues.extend(self._check_slide(index, slide))

        report = DeckQualityReport(issues=issues)
        for issue in report.issues:
            logger.warning("Deck QA %s on slide %s '%s': %s", issue.code, issue.slide_index, issue.slide_title, issue.message)
        return report

    def _check_slide(self, index: int, slide: SlideSpec) -> list[DeckIssue]:
        issues: list[DeckIssue] = []

        if slide.layout in (SlideLayout.TITLE, SlideLayout.SECTION):
            if not slide.title or not slide.title.strip():
                issues.append(self._issue("empty_title", f"{slide.layout.value.title()} slide has no title.", index, slide))

        elif slide.layout == SlideLayout.CONTENT:
            non_empty = [b for b in slide.bullets if b.strip()] if slide.bullets else []
            if not non_empty:
                issues.append(self._issue("empty_content", "Content slide has no bullet points.", index, slide))
            elif len(non_empty) > 8:
                issues.append(self._issue("dense_content", "Content slide has more than 8 bullet points.", index, slide))

        elif slide.layout == SlideLayout.TWO_COLUMN:
            left_non_empty = [b for b in slide.left_bullets if b.strip()] if slide.left_bullets else []
            right_non_empty = [b for b in slide.right_bullets if b.strip()] if slide.right_bullets else []
            if not left_non_empty or not right_non_empty:
                issues.append(self._issue("incomplete_columns", "Two-column slide is missing content on one side.", index, slide))
            elif len(left_non_empty) > 6 or len(right_non_empty) > 6:
                issues.append(self._issue("dense_columns", "Two-column slide has more than 6 bullet points on one side.", index, slide))

        elif slide.layout == SlideLayout.COMPARISON:
            left_non_empty = [b for b in slide.left_bullets if b.strip()] if slide.left_bullets else []
            right_non_empty = [b for b in slide.right_bullets if b.strip()] if slide.right_bullets else []
            if not left_non_empty or not right_non_empty:
                issues.append(self._issue("incomplete_comparison", "Comparison slide is missing points for one option.", index, slide))
            elif len(left_non_empty) > 6 or len(right_non_empty) > 6:
                issues.append(self._issue("dense_comparison", "Comparison slide has more than 6 bullet points on one side.", index, slide))

        elif slide.layout == SlideLayout.QUOTE:
            if not slide.quote_text or not slide.quote_author:
                issues.append(self._issue("incomplete_quote", "Quote slide is missing quote text or author attribution.", index, slide))

        elif slide.layout == SlideLayout.STATISTICS:
            if not slide.statistics or len(slide.statistics) < 2:
                issues.append(self._issue("thin_statistics", "Statistics slide should contain at least two key stats.", index, slide))

        elif slide.layout == SlideLayout.CHART:
            if not slide.chart_data:
                issues.append(self._issue("missing_chart", "Chart slide has no chart data.", index, slide))

        elif slide.layout == SlideLayout.IMAGE:
            if not slide.image_path:
                issues.append(self._issue("missing_image", "Image slide has no resolved image asset.", index, slide))

        elif slide.layout == SlideLayout.CITATIONS:
            if not slide.citations:
                issues.append(self._issue("empty_citations", "Citations slide has no citation entries.", index, slide))

        return issues

    def _issue(self, code: str, message: str, index: int, slide: SlideSpec) -> DeckIssue:
        return DeckIssue(code=code, message=message, slide_index=index, slide_title=slide.title or slide.layout.value)
