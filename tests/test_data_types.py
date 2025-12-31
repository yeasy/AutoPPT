"""
Unit tests for data types (Pydantic models).
"""
import pytest
from pydantic import ValidationError

from core.data_types import (
    ChartType,
    ChartData,
    SlideConfig,
    PresentationSection,
    PresentationOutline,
    UserPresentation
)


class TestChartType:
    """Tests for ChartType enum."""
    
    def test_chart_types_exist(self):
        """Test that all expected chart types exist."""
        assert ChartType.BAR == "bar"
        assert ChartType.PIE == "pie"
        assert ChartType.LINE == "line"
        assert ChartType.COLUMN == "column"


class TestChartData:
    """Tests for ChartData model."""
    
    def test_valid_chart_data(self):
        """Test creating valid ChartData."""
        chart = ChartData(
            chart_type=ChartType.BAR,
            title="Sales by Region",
            categories=["North", "South", "East", "West"],
            values=[100.0, 200.0, 150.0, 180.0]
        )
        
        assert chart.chart_type == ChartType.BAR
        assert chart.title == "Sales by Region"
        assert len(chart.categories) == 4
        assert len(chart.values) == 4
        assert chart.series_name == "Series 1"  # Default value
    
    def test_chart_data_custom_series_name(self):
        """Test ChartData with custom series name."""
        chart = ChartData(
            chart_type=ChartType.PIE,
            title="Market Share",
            categories=["A", "B", "C"],
            values=[50.0, 30.0, 20.0],
            series_name="2025 Data"
        )
        
        assert chart.series_name == "2025 Data"


class TestSlideConfig:
    """Tests for SlideConfig model."""
    
    def test_minimal_slide_config(self):
        """Test SlideConfig with minimal required fields."""
        slide = SlideConfig(
            title="Introduction",
            bullets=["Point 1", "Point 2", "Point 3"]
        )
        
        assert slide.title == "Introduction"
        assert len(slide.bullets) == 3
        assert slide.image_query is None
        assert slide.speaker_notes is None
        assert slide.citations == []
        assert slide.chart_data is None
    
    def test_full_slide_config(self):
        """Test SlideConfig with all fields."""
        chart = ChartData(
            chart_type=ChartType.LINE,
            title="Growth Trend",
            categories=["Q1", "Q2", "Q3", "Q4"],
            values=[10.0, 25.0, 40.0, 60.0]
        )
        
        slide = SlideConfig(
            title="Market Analysis",
            bullets=["Growth is accelerating", "Q4 shows 50% increase"],
            image_query="business growth chart abstract",
            speaker_notes="Discuss the quarterly growth patterns.",
            citations=["https://example.com/report"],
            chart_data=chart
        )
        
        assert slide.title == "Market Analysis"
        assert slide.image_query is not None
        assert slide.speaker_notes is not None
        assert len(slide.citations) == 1
        assert slide.chart_data is not None
        assert slide.chart_data.chart_type == ChartType.LINE
    
    def test_slide_config_missing_required_fields(self):
        """Test that missing required fields raises error."""
        with pytest.raises(ValidationError):
            SlideConfig(title="Only Title")  # Missing bullets


class TestPresentationSection:
    """Tests for PresentationSection model."""
    
    def test_valid_section(self):
        """Test creating valid PresentationSection."""
        section = PresentationSection(
            title="Introduction",
            slides=["Overview", "Background", "Objectives"]
        )
        
        assert section.title == "Introduction"
        assert len(section.slides) == 3


class TestPresentationOutline:
    """Tests for PresentationOutline model."""
    
    def test_valid_outline(self):
        """Test creating valid PresentationOutline."""
        outline = PresentationOutline(
            title="AI in Healthcare",
            sections=[
                PresentationSection(title="Introduction", slides=["Overview"]),
                PresentationSection(title="Applications", slides=["Diagnosis", "Treatment"]),
                PresentationSection(title="Conclusion", slides=["Summary", "Future"])
            ]
        )
        
        assert outline.title == "AI in Healthcare"
        assert len(outline.sections) == 3
        assert outline.sections[1].title == "Applications"


class TestUserPresentation:
    """Tests for UserPresentation model."""
    
    def test_valid_user_presentation(self):
        """Test creating valid UserPresentation."""
        presentation = UserPresentation(
            title="My Presentation",
            sections=[
                PresentationSection(title="Part 1", slides=["Slide A"]),
                PresentationSection(title="Part 2", slides=["Slide B"])
            ]
        )
        
        assert presentation.title == "My Presentation"
        assert len(presentation.sections) == 2
