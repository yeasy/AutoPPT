"""
Tests for style_selector module.
"""
import pytest
from autoppt.style_selector import (
    auto_select_style,
    get_style_description,
    get_all_styles,
    DEFAULT_STYLE,
    STYLE_KEYWORDS
)


class TestAutoSelectStyle:
    """Test auto_select_style function."""
    
    def test_technology_keywords(self):
        """Test that technology-related topics select technology style."""
        assert auto_select_style("Introduction to Machine Learning") == "technology"
        assert auto_select_style("AI and Deep Learning") == "technology"
        assert auto_select_style("Software Development Best Practices") == "technology"
    
    def test_academic_keywords(self):
        """Test that academic topics select academic style."""
        assert auto_select_style("Research Methods in Psychology") == "academic"
        assert auto_select_style("PhD Thesis Defense") == "academic"
        assert auto_select_style("University Course Introduction") == "academic"
    
    def test_corporate_keywords(self):
        """Test that business topics select corporate style."""
        assert auto_select_style("Q3 Investor Report") == "corporate"
        assert auto_select_style("Business Strategy Proposal") == "corporate"
        assert auto_select_style("Financial Market Analysis") == "corporate"
    
    def test_startup_keywords(self):
        """Test that startup topics select startup style."""
        assert auto_select_style("Startup Pitch Deck") == "startup"
        assert auto_select_style("MVP Launch Plan") == "startup"
        assert auto_select_style("Seed Funding Round") == "startup"
    
    def test_nature_keywords(self):
        """Test that environmental topics select nature style."""
        assert auto_select_style("Climate Change Solutions") == "nature"
        assert auto_select_style("Environmental Sustainability") == "nature"
        assert auto_select_style("Green Energy Future") == "nature"
    
    def test_chalkboard_keywords(self):
        """Test that classroom topics select chalkboard style."""
        assert auto_select_style("Classroom Teaching Methods") == "chalkboard"
        assert auto_select_style("School Curriculum Design") == "chalkboard"
    
    def test_sketch_keywords(self):
        """Test that tutorial topics select sketch style."""
        assert auto_select_style("Beginner's Guide to Python") == "sketch"
        assert auto_select_style("Step by Step Tutorial") == "sketch"
    
    def test_blueprint_keywords(self):
        """Test that architecture topics select blueprint style."""
        assert auto_select_style("System Architecture Design") == "blueprint"
        assert auto_select_style("Database Schema Overview") == "blueprint"
    
    def test_neon_keywords(self):
        """Test that entertainment topics select neon style."""
        assert auto_select_style("Gaming Industry Trends") == "neon"
        assert auto_select_style("Music Festival Planning") == "neon"
    
    def test_retro_keywords(self):
        """Test that historical topics select retro style."""
        assert auto_select_style("History of Computing") == "retro"
        assert auto_select_style("Vintage Fashion Trends") == "retro"
    
    def test_chinese_keywords(self):
        """Test that Chinese keywords work correctly."""
        assert auto_select_style("人工智能发展历史") == "technology"
        assert auto_select_style("大学研究方法论") == "academic"
        assert auto_select_style("创业融资计划") == "startup"
        assert auto_select_style("气候变化解决方案") == "nature"
    
    def test_default_style_for_unknown(self):
        """Test that unknown topics return default style."""
        assert auto_select_style("Random Topic XYZ") == DEFAULT_STYLE
        assert auto_select_style("") == DEFAULT_STYLE
    
    def test_empty_topic(self):
        """Test that empty topic returns default style."""
        assert auto_select_style("") == DEFAULT_STYLE
        assert auto_select_style(None) == DEFAULT_STYLE  # type: ignore
    
    def test_case_insensitive(self):
        """Test that matching is case-insensitive."""
        assert auto_select_style("MACHINE LEARNING") == "technology"
        assert auto_select_style("Machine Learning") == "technology"
        assert auto_select_style("machine learning") == "technology"


class TestGetStyleDescription:
    """Test get_style_description function."""
    
    def test_known_styles(self):
        """Test that known styles return descriptions."""
        assert "Clean" in get_style_description("minimalist")
        assert "blue" in get_style_description("technology").lower()
        assert "chalkboard" in get_style_description("chalkboard").lower()
    
    def test_unknown_style(self):
        """Test that unknown styles return default description."""
        assert get_style_description("unknown_style") == "Custom style"


class TestGetAllStyles:
    """Test get_all_styles function."""
    
    def test_returns_list(self):
        """Test that function returns a list."""
        styles = get_all_styles()
        assert isinstance(styles, list)
    
    def test_contains_expected_styles(self):
        """Test that list contains expected styles."""
        styles = get_all_styles()
        expected = ["minimalist", "technology", "chalkboard", "blueprint", "neon"]
        for style in expected:
            assert style in styles
    
    def test_minimum_count(self):
        """Test that we have at least 18 styles."""
        styles = get_all_styles()
        assert len(styles) >= 18


class TestStyleKeywordsIntegrity:
    """Test STYLE_KEYWORDS dictionary integrity."""
    
    def test_all_styles_have_keywords(self):
        """Test that all styles in keywords have at least one keyword."""
        for style, keywords in STYLE_KEYWORDS.items():
            assert len(keywords) > 0, f"Style '{style}' has no keywords"
    
    def test_keywords_are_lowercase(self):
        """Test that all keywords are lowercase."""
        for style, keywords in STYLE_KEYWORDS.items():
            for keyword in keywords:
                assert keyword == keyword.lower(), f"Keyword '{keyword}' in style '{style}' is not lowercase"
