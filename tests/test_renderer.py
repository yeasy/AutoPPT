"""
Unit tests for PPT renderer.
"""
import pytest
import os
import tempfile

from autoppt.ppt_renderer import PPTRenderer
from autoppt.data_types import ChartData, ChartType


class TestPPTRendererInit:
    """Tests for PPTRenderer initialization."""
    
    def test_renderer_instantiation(self):
        """Test that PPTRenderer can be instantiated."""
        renderer = PPTRenderer()
        assert renderer is not None
        assert renderer.prs is not None
    
    def test_renderer_with_no_template(self):
        """Test renderer creates empty presentation without template."""
        renderer = PPTRenderer(template_path=None)
        assert len(renderer.prs.slides) == 0


class TestApplyStyle:
    """Tests for apply_style method."""
    
    def test_apply_minimalist_style(self):
        """Test applying minimalist style."""
        renderer = PPTRenderer()
        renderer.apply_style("minimalist")
        
        assert hasattr(renderer, 'current_style')
        assert 'title_color' in renderer.current_style
        assert 'text_color' in renderer.current_style
        assert 'bg_color' in renderer.current_style
        assert 'font_name' in renderer.current_style
    
    def test_apply_all_styles(self):
        """Test that all styles can be applied without error."""
        styles = [
            "minimalist", "technology", "nature", "creative",
            "corporate", "academic", "startup", "dark"
        ]
        
        for style in styles:
            renderer = PPTRenderer()
            renderer.apply_style(style)
            assert hasattr(renderer, 'current_style')
    
    def test_apply_unknown_style_defaults(self):
        """Test that unknown style defaults to minimalist."""
        renderer = PPTRenderer()
        renderer.apply_style("unknown_style")
        
        # Should not raise, should default to minimalist
        assert hasattr(renderer, 'current_style')


class TestAddSlides:
    """Tests for slide addition methods."""
    
    def test_add_title_slide(self):
        """Test adding a title slide."""
        renderer = PPTRenderer()
        renderer.apply_style("minimalist")
        
        initial_count = len(renderer.prs.slides)
        renderer.add_title_slide("Test Title", "Test Subtitle")
        
        assert len(renderer.prs.slides) == initial_count + 1
    
    def test_add_section_header(self):
        """Test adding a section header slide."""
        renderer = PPTRenderer()
        renderer.apply_style("minimalist")
        
        initial_count = len(renderer.prs.slides)
        renderer.add_section_header("Section 1")
        
        assert len(renderer.prs.slides) == initial_count + 1
    
    def test_add_content_slide(self, sample_bullets):
        """Test adding a content slide with bullets."""
        renderer = PPTRenderer()
        renderer.apply_style("minimalist")
        
        initial_count = len(renderer.prs.slides)
        renderer.add_content_slide(
            title="Content Slide",
            bullets=sample_bullets,
            notes="Speaker notes here"
        )
        
        assert len(renderer.prs.slides) == initial_count + 1
    
    def test_add_citations_slide(self):
        """Test adding a citations slide."""
        renderer = PPTRenderer()
        renderer.apply_style("minimalist")
        
        citations = [
            "https://example.com/source1",
            "https://example.com/source2"
        ]
        
        initial_count = len(renderer.prs.slides)
        renderer.add_citations_slide(citations)
        
        assert len(renderer.prs.slides) == initial_count + 1
    
    def test_add_citations_slide_empty_list(self):
        """Test that empty citations list adds no slide."""
        renderer = PPTRenderer()
        renderer.apply_style("minimalist")
        
        initial_count = len(renderer.prs.slides)
        renderer.add_citations_slide([])
        
        assert len(renderer.prs.slides) == initial_count


class TestChartSlide:
    """Tests for chart slide functionality."""
    
    def test_add_chart_slide(self):
        """Test adding a chart slide."""
        renderer = PPTRenderer()
        renderer.apply_style("corporate")
        
        chart_data = ChartData(
            chart_type=ChartType.COLUMN,
            title="Quarterly Revenue",
            categories=["Q1", "Q2", "Q3", "Q4"],
            values=[100.0, 150.0, 200.0, 250.0],
            series_name="2025"
        )
        
        initial_count = len(renderer.prs.slides)
        renderer.add_chart_slide("Revenue Analysis", chart_data)
        
        assert len(renderer.prs.slides) == initial_count + 1


class TestSave:
    """Tests for save functionality."""
    
    def test_save_presentation(self, temp_dir, sample_bullets):
        """Test saving a presentation to file."""
        renderer = PPTRenderer()
        renderer.apply_style("minimalist")
        
        renderer.add_title_slide("Test Presentation", "Subtitle")
        renderer.add_section_header("Section 1")
        renderer.add_content_slide("Slide 1", sample_bullets)
        
        output_path = os.path.join(temp_dir, "test_output.pptx")
        renderer.save(output_path)
        
        assert os.path.exists(output_path)
        assert os.path.getsize(output_path) > 0
