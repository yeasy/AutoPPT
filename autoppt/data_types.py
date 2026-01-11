from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


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


class SlideType(str, Enum):
    """Types of slides available for generation."""
    CONTENT = "content"       # Standard bullet points
    CHART = "chart"           # Data visualization
    STATISTICS = "statistics" # Key numbers highlight
    IMAGE = "image"           # Fullscreen image


class StatisticData(BaseModel):
    """Data for a single statistic highlight."""
    value: str = Field(description="The number/value to highlight (e.g., '85%', '$4B')")
    label: str = Field(description="Short description label")


class SlideConfig(BaseModel):
    """Configuration for a single slide's content."""
    title: str = Field(description="The main title of the slide")
    slide_type: SlideType = Field(default=SlideType.CONTENT, description="Type of slide layout to use")
    bullets: List[str] = Field(description="List of 5-8 detailed bullet points (for content slides)")
    image_query: Optional[str] = Field(None, description="A search query to find an image for this slide")
    speaker_notes: Optional[str] = Field(None, description="Speaker notes for this slide")
    citations: List[str] = Field(default_factory=list, description="List of source URLs used for this slide")
    chart_data: Optional[ChartData] = Field(None, description="Data for chart slides")
    statistics: Optional[List[StatisticData]] = Field(None, description="List of 3-4 key stats for statistics slides")


class PresentationSection(BaseModel):
    """A section/chapter of the presentation containing multiple slides."""
    title: str = Field(description="Title of the section or chapter")
    slides: List[str] = Field(description="List of slide topics within this section")


class PresentationOutline(BaseModel):
    """Complete outline of a presentation with hierarchical sections."""
    title: str = Field(description="Main title of the presentation")
    sections: List[PresentationSection] = Field(description="List of hierarchical sections/chapters")


class UserPresentation(BaseModel):
    """User-defined presentation structure."""
    title: str
    sections: List[PresentationSection]

