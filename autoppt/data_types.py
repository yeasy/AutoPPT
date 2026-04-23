from __future__ import annotations

import math
from enum import Enum

from pydantic import BaseModel, Field, model_validator


class ChartType(str, Enum):
    """Supported chart types for PPT generation."""
    BAR = "bar"
    PIE = "pie"
    LINE = "line"
    COLUMN = "column"


class ChartData(BaseModel):
    """Data structure for chart generation."""
    chart_type: ChartType = Field(description="Type of chart: bar, pie, line, or column")
    title: str = Field(max_length=500, description="Chart title")
    categories: list[str] = Field(description="Category labels for the X-axis or pie slices")
    values: list[float] = Field(description="Numeric values corresponding to each category")
    series_name: str = Field(default="Series 1", max_length=200, description="Name of the data series")

    @model_validator(mode="after")
    def _check_lengths(self) -> ChartData:
        if not self.categories:
            raise ValueError("categories must not be empty")
        if len(self.categories) != len(self.values):
            raise ValueError(
                f"categories ({len(self.categories)}) and values ({len(self.values)}) must have the same length"
            )
        if any(not math.isfinite(v) for v in self.values):
            raise ValueError("values must be finite numbers (no NaN or inf)")
        return self


class SlideType(str, Enum):
    """Types of slides available for generation."""
    CONTENT = "content"       # Standard bullet points
    TWO_COLUMN = "two_column" # Parallel bullets across two columns
    COMPARISON = "comparison" # Two options or entities contrasted
    QUOTE = "quote"           # Quote-centric slide
    CHART = "chart"           # Data visualization
    STATISTICS = "statistics" # Key numbers highlight
    IMAGE = "image"           # Fullscreen image


class SlideLayout(str, Enum):
    """Renderer-facing layout choices."""
    TITLE = "title"
    SECTION = "section"
    CONTENT = "content"
    TWO_COLUMN = "two_column"
    COMPARISON = "comparison"
    QUOTE = "quote"
    CHART = "chart"
    STATISTICS = "statistics"
    IMAGE = "image"
    CITATIONS = "citations"


class StatisticData(BaseModel):
    """Data for a single statistic highlight."""
    value: str = Field(max_length=50, description="The number/value to highlight (e.g., '85%', '$4B')")
    label: str = Field(max_length=200, description="Short description label")


class SlideConfig(BaseModel):
    """Configuration for a single slide's content."""
    title: str = Field(max_length=500, description="The main title of the slide")
    slide_type: SlideType = Field(default=SlideType.CONTENT, description="Type of slide layout to use")
    bullets: list[str] = Field(default_factory=list, description="List of 5-8 detailed bullet points (for content slides)")
    left_bullets: list[str] = Field(default_factory=list, description="Bullets for the left column when using two-column or comparison layouts")
    right_bullets: list[str] = Field(default_factory=list, description="Bullets for the right column when using two-column or comparison layouts")
    left_title: str | None = Field(None, max_length=500, description="Title for the left column or first comparison item")
    right_title: str | None = Field(None, max_length=500, description="Title for the right column or second comparison item")
    image_query: str | None = Field(None, max_length=500, description="A search query to find an image for this slide")
    quote_text: str | None = Field(None, max_length=2000, description="Primary quote text when using a quote layout")
    quote_author: str | None = Field(None, max_length=200, description="Author attribution for a quote layout")
    quote_context: str | None = Field(None, max_length=500, description="Context for a quote layout such as title, source, or year")
    speaker_notes: str | None = Field(None, max_length=5000, description="Speaker notes for this slide")
    citations: list[str] = Field(default_factory=list, description="List of source URLs used for this slide")
    chart_data: ChartData | None = Field(None, description="Data for chart slides")
    statistics: list[StatisticData] | None = Field(None, description="List of 3-4 key stats for statistics slides")


class SlidePlan(BaseModel):
    """Planning-time intent for a slide before final content generation."""
    title: str = Field(description="Slide title being planned")
    section_title: str = Field(default="", description="Section title that contains the slide")
    topic: str = Field(default="", description="Overall deck topic")
    language: str = Field(default="English", description="Requested output language")
    slide_type: SlideType = Field(default=SlideType.CONTENT, description="Preferred layout type")
    left_title: str | None = Field(None, description="Suggested left column title")
    right_title: str | None = Field(None, description="Suggested right column title")
    quote_author: str | None = Field(None, description="Suggested author if using a quote slide")
    quote_context: str | None = Field(None, description="Suggested source or context for quote slides")
    objective: str | None = Field(None, description="Primary message this slide should deliver")
    evidence_focus: list[str] = Field(default_factory=list, description="Named evidence, entities, or facts to emphasize")
    research_queries: list[str] = Field(default_factory=list, description="Targeted research queries for this slide")
    visual_intent: str | None = Field(None, description="Optional visual direction for the slide")
    remix_instruction: str | None = Field(None, description="Optional instruction for remixing an existing slide")
    layout_locked: bool = Field(default=False, description="Whether the requested layout should override automatic inference")
    rationale: str | None = Field(None, description="Brief reason for the preferred layout")


class SlideSpec(BaseModel):
    """Normalized renderer input for a single slide."""
    layout: SlideLayout = Field(description="Renderer layout choice")
    title: str = Field(default="", description="Slide title")
    subtitle: str | None = Field(None, description="Subtitle for title slides")
    bullets: list[str] = Field(default_factory=list, description="Bullet content")
    left_bullets: list[str] = Field(default_factory=list, description="Left column bullet content")
    right_bullets: list[str] = Field(default_factory=list, description="Right column bullet content")
    left_title: str | None = Field(None, description="Left column title")
    right_title: str | None = Field(None, description="Right column title")
    speaker_notes: str | None = Field(None, description="Speaker notes")
    citations: list[str] = Field(default_factory=list, description="Citations for the slide or citations page")
    chart_data: ChartData | None = Field(None, description="Chart payload")
    statistics: list[StatisticData] | None = Field(None, description="Statistics payload")
    image_path: str | None = Field(None, description="Resolved image path for image-backed slides")
    image_caption: str | None = Field(None, description="Caption for image layouts")
    quote_text: str | None = Field(None, description="Quote body for quote layout")
    quote_author: str | None = Field(None, description="Quote author attribution")
    quote_context: str | None = Field(None, description="Quote context such as title or year")
    editable: bool = Field(default=False, description="Whether the slide can be regenerated or remixed")
    source_topic: str | None = Field(None, description="Original deck topic used to generate this slide")
    source_section: str | None = Field(None, description="Section title that produced this slide")
    source_title: str | None = Field(None, description="Original outline slide title")
    planned_layout: SlideLayout | None = Field(None, description="Planned layout before final normalization")
    layout_rationale: str | None = Field(None, description="Reason for the selected layout")
    plan: SlidePlan | None = Field(None, description="Planning metadata used to generate this slide")
    source_config: SlideConfig | None = Field(None, description="Generated slide config used to produce this slide")


class PresentationSection(BaseModel):
    """A section/chapter of the presentation containing multiple slides."""
    title: str = Field(description="Title of the section or chapter")
    slides: list[str] = Field(description="List of slide topics within this section")


class PresentationOutline(BaseModel):
    """Complete outline of a presentation with hierarchical sections."""
    title: str = Field(description="Main title of the presentation")
    sections: list[PresentationSection] = Field(description="List of hierarchical sections/chapters")


class DeckSpec(BaseModel):
    """Normalized renderer input for a full presentation deck."""
    title: str = Field(description="Presentation title")
    topic: str = Field(description="Original topic or prompt")
    style: str = Field(default="minimalist", description="Theme used for rendering")
    language: str = Field(default="English", description="Language requested for deck generation")
    template_path: str | None = Field(None, description="Optional PPTX template path used for rendering")
    slides: list[SlideSpec] = Field(default_factory=list, description="Slides to render in order")


class UserPresentation(BaseModel):
    """User-defined presentation structure."""
    title: str
    sections: list[PresentationSection]
