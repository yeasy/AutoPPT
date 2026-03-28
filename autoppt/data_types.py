from enum import Enum
from typing import List, Optional

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
    title: str = Field(description="Chart title")
    categories: List[str] = Field(description="Category labels for the X-axis or pie slices")
    values: List[float] = Field(description="Numeric values corresponding to each category")
    series_name: str = Field(default="Series 1", description="Name of the data series")

    @model_validator(mode="after")
    def _check_lengths(self) -> "ChartData":
        if len(self.categories) != len(self.values):
            raise ValueError(
                f"categories ({len(self.categories)}) and values ({len(self.values)}) must have the same length"
            )
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
    value: str = Field(description="The number/value to highlight (e.g., '85%', '$4B')")
    label: str = Field(description="Short description label")


class SlideConfig(BaseModel):
    """Configuration for a single slide's content."""
    title: str = Field(description="The main title of the slide")
    slide_type: SlideType = Field(default=SlideType.CONTENT, description="Type of slide layout to use")
    bullets: List[str] = Field(description="List of 5-8 detailed bullet points (for content slides)")
    left_bullets: List[str] = Field(default_factory=list, description="Bullets for the left column when using two-column or comparison layouts")
    right_bullets: List[str] = Field(default_factory=list, description="Bullets for the right column when using two-column or comparison layouts")
    left_title: Optional[str] = Field(None, description="Title for the left column or first comparison item")
    right_title: Optional[str] = Field(None, description="Title for the right column or second comparison item")
    image_query: Optional[str] = Field(None, description="A search query to find an image for this slide")
    quote_text: Optional[str] = Field(None, description="Primary quote text when using a quote layout")
    quote_author: Optional[str] = Field(None, description="Author attribution for a quote layout")
    quote_context: Optional[str] = Field(None, description="Context for a quote layout such as title, source, or year")
    speaker_notes: Optional[str] = Field(None, description="Speaker notes for this slide")
    citations: List[str] = Field(default_factory=list, description="List of source URLs used for this slide")
    chart_data: Optional[ChartData] = Field(None, description="Data for chart slides")
    statistics: Optional[List[StatisticData]] = Field(None, description="List of 3-4 key stats for statistics slides")


class SlidePlan(BaseModel):
    """Planning-time intent for a slide before final content generation."""
    title: str = Field(description="Slide title being planned")
    section_title: str = Field(default="", description="Section title that contains the slide")
    topic: str = Field(default="", description="Overall deck topic")
    language: str = Field(default="English", description="Requested output language")
    slide_type: SlideType = Field(default=SlideType.CONTENT, description="Preferred layout type")
    left_title: Optional[str] = Field(None, description="Suggested left column title")
    right_title: Optional[str] = Field(None, description="Suggested right column title")
    quote_author: Optional[str] = Field(None, description="Suggested author if using a quote slide")
    quote_context: Optional[str] = Field(None, description="Suggested source or context for quote slides")
    objective: Optional[str] = Field(None, description="Primary message this slide should deliver")
    evidence_focus: List[str] = Field(default_factory=list, description="Named evidence, entities, or facts to emphasize")
    research_queries: List[str] = Field(default_factory=list, description="Targeted research queries for this slide")
    visual_intent: Optional[str] = Field(None, description="Optional visual direction for the slide")
    remix_instruction: Optional[str] = Field(None, description="Optional instruction for remixing an existing slide")
    layout_locked: bool = Field(default=False, description="Whether the requested layout should override automatic inference")
    rationale: Optional[str] = Field(None, description="Brief reason for the preferred layout")


class SlideSpec(BaseModel):
    """Normalized renderer input for a single slide."""
    layout: SlideLayout = Field(description="Renderer layout choice")
    title: str = Field(default="", description="Slide title")
    subtitle: Optional[str] = Field(None, description="Subtitle for title slides")
    bullets: List[str] = Field(default_factory=list, description="Bullet content")
    left_bullets: List[str] = Field(default_factory=list, description="Left column bullet content")
    right_bullets: List[str] = Field(default_factory=list, description="Right column bullet content")
    left_title: Optional[str] = Field(None, description="Left column title")
    right_title: Optional[str] = Field(None, description="Right column title")
    speaker_notes: Optional[str] = Field(None, description="Speaker notes")
    citations: List[str] = Field(default_factory=list, description="Citations for the slide or citations page")
    chart_data: Optional[ChartData] = Field(None, description="Chart payload")
    statistics: Optional[List[StatisticData]] = Field(None, description="Statistics payload")
    image_path: Optional[str] = Field(None, description="Resolved image path for image-backed slides")
    image_caption: Optional[str] = Field(None, description="Caption for image layouts")
    quote_text: Optional[str] = Field(None, description="Quote body for quote layout")
    quote_author: Optional[str] = Field(None, description="Quote author attribution")
    quote_context: Optional[str] = Field(None, description="Quote context such as title or year")
    editable: bool = Field(default=False, description="Whether the slide can be regenerated or remixed")
    source_topic: Optional[str] = Field(None, description="Original deck topic used to generate this slide")
    source_section: Optional[str] = Field(None, description="Section title that produced this slide")
    source_title: Optional[str] = Field(None, description="Original outline slide title")
    planned_layout: Optional[SlideLayout] = Field(None, description="Planned layout before final normalization")
    layout_rationale: Optional[str] = Field(None, description="Reason for the selected layout")
    plan: Optional[SlidePlan] = Field(None, description="Planning metadata used to generate this slide")
    source_config: Optional[SlideConfig] = Field(None, description="Generated slide config used to produce this slide")


class PresentationSection(BaseModel):
    """A section/chapter of the presentation containing multiple slides."""
    title: str = Field(description="Title of the section or chapter")
    slides: List[str] = Field(description="List of slide topics within this section")


class PresentationOutline(BaseModel):
    """Complete outline of a presentation with hierarchical sections."""
    title: str = Field(description="Main title of the presentation")
    sections: List[PresentationSection] = Field(description="List of hierarchical sections/chapters")


class DeckSpec(BaseModel):
    """Normalized renderer input for a full presentation deck."""
    title: str = Field(description="Presentation title")
    topic: str = Field(description="Original topic or prompt")
    style: str = Field(default="minimalist", description="Theme used for rendering")
    language: str = Field(default="English", description="Language requested for deck generation")
    template_path: Optional[str] = Field(None, description="Optional PPTX template path used for rendering")
    slides: List[SlideSpec] = Field(default_factory=list, description="Slides to render in order")


class UserPresentation(BaseModel):
    """User-defined presentation structure."""
    title: str
    sections: List[PresentationSection]
