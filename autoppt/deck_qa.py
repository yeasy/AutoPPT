import logging
from typing import List

from pydantic import BaseModel, Field

from .data_types import DeckSpec, SlideLayout, SlideSpec

logger = logging.getLogger(__name__)


class DeckIssue(BaseModel):
    code: str = Field(description="Stable issue code")
    message: str = Field(description="Human-readable issue message")
    slide_index: int = Field(description="1-based slide index")
    slide_title: str = Field(description="Slide title at the time of analysis")


class DeckQualityReport(BaseModel):
    issues: List[DeckIssue] = Field(default_factory=list)

    @property
    def has_issues(self) -> bool:
        return bool(self.issues)


class DeckQA:
    """Lightweight linting for normalized deck specs."""

    def analyze(self, deck_spec: DeckSpec) -> DeckQualityReport:
        issues: list[DeckIssue] = []
        seen_titles: dict[str, int] = {}

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

        if slide.layout == SlideLayout.CONTENT:
            if not slide.bullets:
                issues.append(self._issue("empty_content", "Content slide has no bullet points.", index, slide))
            elif len(slide.bullets) > 8:
                issues.append(self._issue("dense_content", "Content slide has more than 8 bullet points.", index, slide))

        if slide.layout == SlideLayout.TWO_COLUMN:
            if not slide.left_bullets or not slide.right_bullets:
                issues.append(self._issue("incomplete_columns", "Two-column slide is missing content on one side.", index, slide))

        if slide.layout == SlideLayout.COMPARISON:
            if not slide.left_bullets or not slide.right_bullets:
                issues.append(self._issue("incomplete_comparison", "Comparison slide is missing points for one option.", index, slide))

        if slide.layout == SlideLayout.QUOTE:
            if not slide.quote_text or not slide.quote_author:
                issues.append(self._issue("incomplete_quote", "Quote slide is missing quote text or author attribution.", index, slide))

        if slide.layout == SlideLayout.STATISTICS and (not slide.statistics or len(slide.statistics) < 2):
            issues.append(self._issue("thin_statistics", "Statistics slide should contain at least two key stats.", index, slide))

        if slide.layout == SlideLayout.CHART and slide.chart_data:
            if len(slide.chart_data.categories) != len(slide.chart_data.values):
                issues.append(self._issue("chart_mismatch", "Chart categories and values length do not match.", index, slide))
        elif slide.layout == SlideLayout.CHART:
            issues.append(self._issue("missing_chart", "Chart slide has no chart data.", index, slide))

        if slide.layout == SlideLayout.IMAGE and not slide.image_path:
            issues.append(self._issue("missing_image", "Image slide has no resolved image asset.", index, slide))

        return issues

    def _issue(self, code: str, message: str, index: int, slide: SlideSpec) -> DeckIssue:
        return DeckIssue(code=code, message=message, slide_index=index, slide_title=slide.title or slide.layout.value)
