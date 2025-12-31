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


class SlideConfig(BaseModel):
    """Configuration for a single slide's content."""
    title: str = Field(description="The main title of the slide")
    bullets: List[str] = Field(description="List of 3-5 bullet points")
    image_query: Optional[str] = Field(None, description="A search query to find an image for this slide")
    speaker_notes: Optional[str] = Field(None, description="Speaker notes for this slide")
    citations: List[str] = Field(default_factory=list, description="List of source URLs used for this slide")
    chart_data: Optional[ChartData] = Field(None, description="Optional chart data for data visualization slides")


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

