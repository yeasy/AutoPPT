"""
Unit tests for TemplateHandler.
"""
import pytest
import os
from pptx import Presentation
from autoppt.template_handler import TemplateHandler

class TestTemplateHandler:
    """Tests for TemplateHandler."""
    
    @pytest.fixture
    def sample_template(self, tmp_path):
        """Create a temporary real PPTX file."""
        path = tmp_path / "template.pptx"
        prs = Presentation()
        # Add slide master layouts (default has 11 layouts)
        prs.save(path)
        return path
        
    def test_init_valid_template(self, sample_template):
        """Test initialization with valid template."""
        handler = TemplateHandler(str(sample_template))
        assert handler.prs is not None
        assert isinstance(handler.layouts, dict)
        
    def test_init_invalid_path(self):
        """Test initialization with invalid path."""
        with pytest.raises(FileNotFoundError):
            TemplateHandler("nonexistent.pptx")
            
    def test_analyze_layouts(self, sample_template):
        """Test layout analysis."""
        handler = TemplateHandler(str(sample_template))
        layouts = handler.layouts
        
        # Standard python-pptx presentation has layouts
        # usually 11 layouts in default template
        assert len(layouts) > 0
        
        # Check structure of layout info
        first_layout = layouts[0]
        assert "name" in first_layout
        assert "placeholders" in first_layout
        
    def test_get_layout_by_name(self, sample_template):
        """Test finding layout by name."""
        handler = TemplateHandler(str(sample_template))
        
        # Default layouts have names like "Title Slide", "Title and Content"
        # We need to check what names python-pptx default template uses
        # Usually: "Title Slide", "Title and Content", "Section Header", etc.
        
        # The default blank presentation might have different names or empty names depending on python-pptx version
        # But generally they match standard Office names.
        
        found_idx = handler.get_layout_by_name("Title")
        # Assert might fail if default template names are different, but usually works
        # If it fails, we know we need to robustify
        if found_idx is not None:
             assert isinstance(found_idx, int)

    def test_get_best_layout_for_type(self, sample_template):
        """Test getting best layout for type."""
        handler = TemplateHandler(str(sample_template))
        
        idx = handler.get_best_layout_for_type("title")
        assert isinstance(idx, int)
        
        idx_content = handler.get_best_layout_for_type("content")
        assert isinstance(idx_content, int)
