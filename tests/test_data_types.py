"""
Unit tests for data types (Pydantic models).
"""
import pytest
from pydantic import ValidationError

from autoppt.data_types import (
    ChartType,
    ChartData,
    DeckSpec,
    SlideLayout,
    SlideConfig,
    SlidePlan,
    SlideSpec,
    SlideType,
    StatisticData,
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
            SlideConfig()  # Missing title (required field)

    def test_slide_config_bullets_default_empty(self):
        """Test that bullets defaults to empty list when omitted."""
        slide = SlideConfig(title="No Bullets")
        assert slide.bullets == []

    def test_rich_slide_config_fields(self):
        """Test richer layout fields on SlideConfig."""
        slide = SlideConfig(
            title="Platform Comparison",
            slide_type=SlideType.COMPARISON,
            bullets=["Shared baseline"],
            left_title="Current State",
            right_title="Future State",
            left_bullets=["Manual reviews", "Slow release cycle"],
            right_bullets=["Automated checks", "Faster iteration"],
            citations=["https://example.com"],
        )

        assert slide.slide_type == SlideType.COMPARISON
        assert slide.left_title == "Current State"
        assert len(slide.left_bullets) == 2
        assert slide.citations == ["https://example.com"]


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


class TestDeckSpec:
    """Tests for deck-level normalized data."""

    def test_deck_spec_tracks_style_language_and_plan(self):
        """Test deck metadata and slide planning fields."""
        plan = SlidePlan(
            title="Execution Priorities",
            section_title="Roadmap",
            topic="AI Transformation",
            language="English",
            slide_type=SlideType.TWO_COLUMN,
            research_queries=["AI Transformation roadmap execution priorities"],
        )
        slide = SlideSpec(
            layout=SlideLayout.TWO_COLUMN,
            title="Execution Priorities",
            left_bullets=["Stabilize infrastructure"],
            right_bullets=["Scale automation"],
            plan=plan,
        )
        deck = DeckSpec(title="Deck", topic="AI Transformation", style="technology", language="English", slides=[slide])

        assert deck.style == "technology"
        assert deck.language == "English"
        assert deck.slides[0].plan is not None
        assert deck.slides[0].plan.slide_type == SlideType.TWO_COLUMN


class TestChartDataValidation:
    """Tests for ChartData validation edge cases."""

    def test_empty_categories_raises_validation_error(self):
        """ChartData with empty categories list should raise ValidationError."""
        with pytest.raises(ValidationError, match="categories must not be empty"):
            ChartData(
                chart_type="bar",
                title="T",
                categories=[],
                values=[],
                series_name="S",
            )

    def test_nan_value_raises_validation_error(self):
        """ChartData with NaN values should raise ValidationError."""
        with pytest.raises(ValidationError, match="finite"):
            ChartData(
                chart_type="bar",
                title="T",
                categories=["A"],
                values=[float("nan")],
            )

    def test_inf_value_raises_validation_error(self):
        """ChartData with inf values should raise ValidationError."""
        with pytest.raises(ValidationError, match="finite"):
            ChartData(
                chart_type="bar",
                title="T",
                categories=["A"],
                values=[float("inf")],
            )

    def test_negative_inf_value_raises_validation_error(self):
        """ChartData with -inf values should raise ValidationError."""
        with pytest.raises(ValidationError, match="finite"):
            ChartData(
                chart_type="bar",
                title="T",
                categories=["A"],
                values=[float("-inf")],
            )

    def test_mismatched_categories_values_length(self):
        """ChartData with different-length categories and values should raise ValidationError."""
        with pytest.raises(ValidationError, match="same length"):
            ChartData(
                chart_type="bar",
                title="Mismatched",
                categories=["A", "B", "C"],
                values=[1.0, 2.0],
            )


class TestChartDataMaxLengthConstraints:
    """Tests for ChartData max_length constraints."""

    def test_title_at_max_length(self):
        """ChartData title at exactly 500 chars should be accepted."""
        chart = ChartData(chart_type="bar", title="x" * 500, categories=["A"], values=[1.0])
        assert len(chart.title) == 500

    def test_title_exceeds_max_length(self):
        """ChartData title exceeding 500 chars should raise ValidationError."""
        with pytest.raises(ValidationError):
            ChartData(chart_type="bar", title="x" * 501, categories=["A"], values=[1.0])

    def test_series_name_at_max_length(self):
        """ChartData series_name at exactly 200 chars should be accepted."""
        chart = ChartData(chart_type="bar", title="T", categories=["A"], values=[1.0], series_name="s" * 200)
        assert len(chart.series_name) == 200

    def test_series_name_exceeds_max_length(self):
        """ChartData series_name exceeding 200 chars should raise ValidationError."""
        with pytest.raises(ValidationError):
            ChartData(chart_type="bar", title="T", categories=["A"], values=[1.0], series_name="s" * 201)


class TestSlideConfigCrossFieldConsistency:
    """Tests for SlideConfig cross-field consistency edge cases."""

    def test_chart_type_with_no_chart_data(self):
        """SlideConfig with slide_type=CHART but chart_data=None should construct without error."""
        slide = SlideConfig(
            title="Chart Slide",
            slide_type=SlideType.CHART,
            bullets=["Placeholder"],
            chart_data=None,
        )
        assert slide.slide_type == SlideType.CHART
        assert slide.chart_data is None

    def test_quote_type_with_no_quote_text(self):
        """SlideConfig with slide_type=QUOTE but quote_text=None should construct without error."""
        slide = SlideConfig(
            title="Quote Slide",
            slide_type=SlideType.QUOTE,
            bullets=["Placeholder"],
            quote_text=None,
        )
        assert slide.slide_type == SlideType.QUOTE
        assert slide.quote_text is None

    def test_statistics_type_with_no_statistics(self):
        """SlideConfig with slide_type=STATISTICS but statistics=None should construct without error."""
        slide = SlideConfig(
            title="Stats Slide",
            slide_type=SlideType.STATISTICS,
            bullets=["Placeholder"],
            statistics=None,
        )
        assert slide.slide_type == SlideType.STATISTICS
        assert slide.statistics is None


class TestPresentationOutlineEdgeCases:
    """Tests for PresentationOutline edge cases."""

    def test_outline_with_empty_sections(self):
        """PresentationOutline with an empty sections list should construct without error."""
        outline = PresentationOutline(
            title="Empty Deck",
            sections=[],
        )
        assert outline.title == "Empty Deck"
        assert outline.sections == []


class TestDeckSpecEdgeCases:
    """Tests for DeckSpec edge cases."""

    def test_deck_spec_with_empty_slides(self):
        """DeckSpec with an empty slides list should construct without error."""
        deck = DeckSpec(
            title="Empty Deck",
            topic="Testing",
            slides=[],
        )
        assert deck.title == "Empty Deck"
        assert deck.slides == []


class TestStatisticDataConstraints:
    """Tests for StatisticData max_length constraints."""

    def test_statistic_data_valid(self):
        """Normal StatisticData should construct without error."""
        stat = StatisticData(value="85%", label="Adoption Rate")
        assert stat.value == "85%"
        assert stat.label == "Adoption Rate"

    def test_statistic_data_value_too_long(self):
        """StatisticData with value exceeding max_length should raise."""
        with pytest.raises(ValidationError):
            StatisticData(value="x" * 51, label="OK")

    def test_statistic_data_label_too_long(self):
        """StatisticData with label exceeding max_length should raise."""
        with pytest.raises(ValidationError):
            StatisticData(value="85%", label="x" * 201)

    def test_statistic_data_value_at_exact_max(self):
        """StatisticData with value at exactly max_length should be accepted."""
        stat = StatisticData(value="x" * 50, label="OK")
        assert len(stat.value) == 50

    def test_statistic_data_label_at_exact_max(self):
        """StatisticData with label at exactly max_length should be accepted."""
        stat = StatisticData(value="85%", label="x" * 200)
        assert len(stat.label) == 200


class TestChartTypeValidation:
    """Tests for ChartType enum validation."""

    def test_invalid_chart_type_raises(self):
        """Passing an invalid chart type string should raise ValidationError."""
        with pytest.raises(ValidationError):
            ChartData(chart_type="scatter", title="T", categories=["A"], values=[1.0])

    def test_valid_chart_type_by_string(self):
        """Passing a valid chart type string should work."""
        chart = ChartData(chart_type="bar", title="T", categories=["A"], values=[1.0])
        assert chart.chart_type == ChartType.BAR


class TestSlideSpecDefaults:
    """Tests for SlideSpec field defaults."""

    def test_minimal_construction(self):
        """SlideSpec with only layout should set all defaults."""
        spec = SlideSpec(layout=SlideLayout.CONTENT)
        assert spec.title == ""
        assert spec.subtitle is None
        assert spec.bullets == []
        assert spec.left_bullets == []
        assert spec.right_bullets == []
        assert spec.editable is False
        assert spec.planned_layout is None
        assert spec.source_config is None
        assert spec.plan is None

    def test_editable_flag(self):
        """Setting editable should be preserved."""
        spec = SlideSpec(layout=SlideLayout.CONTENT, title="Test", editable=True)
        assert spec.editable is True


class TestSlidePlanDefaults:
    """Tests for SlidePlan field defaults."""

    def test_minimal_construction(self):
        """SlidePlan with only title should set all defaults."""
        plan = SlidePlan(title="Test")
        assert plan.section_title == ""
        assert plan.topic == ""
        assert plan.language == "English"
        assert plan.slide_type == SlideType.CONTENT
        assert plan.layout_locked is False
        assert plan.left_title is None
        assert plan.right_title is None
        assert plan.quote_author is None
        assert plan.evidence_focus == []
        assert plan.research_queries == []

    def test_all_fields_construction(self):
        """SlidePlan with all fields should preserve them."""
        plan = SlidePlan(
            title="Test",
            section_title="Section",
            topic="Topic",
            language="Chinese",
            slide_type=SlideType.COMPARISON,
            left_title="A",
            right_title="B",
            layout_locked=True,
            rationale="Testing",
        )
        assert plan.slide_type == SlideType.COMPARISON
        assert plan.layout_locked is True
        assert plan.left_title == "A"


class TestSlideConfigMaxLengthConstraints:
    """Tests for SlideConfig max_length constraints."""

    def test_title_at_max_length(self):
        """SlideConfig title at exactly 500 chars should be accepted."""
        slide = SlideConfig(title="x" * 500)
        assert len(slide.title) == 500

    def test_title_exceeds_max_length(self):
        """SlideConfig title exceeding 500 chars should raise ValidationError."""
        with pytest.raises(ValidationError):
            SlideConfig(title="x" * 501)

    def test_speaker_notes_at_max_length(self):
        """SlideConfig speaker_notes at exactly 5000 chars should be accepted."""
        slide = SlideConfig(title="OK", speaker_notes="n" * 5000)
        assert len(slide.speaker_notes) == 5000

    def test_speaker_notes_exceeds_max_length(self):
        """SlideConfig speaker_notes exceeding 5000 chars should raise ValidationError."""
        with pytest.raises(ValidationError):
            SlideConfig(title="OK", speaker_notes="n" * 5001)

    def test_quote_text_at_max_length(self):
        """SlideConfig quote_text at exactly 2000 chars should be accepted."""
        slide = SlideConfig(title="OK", quote_text="q" * 2000)
        assert len(slide.quote_text) == 2000

    def test_quote_text_exceeds_max_length(self):
        """SlideConfig quote_text exceeding 2000 chars should raise ValidationError."""
        with pytest.raises(ValidationError):
            SlideConfig(title="OK", quote_text="q" * 2001)

    def test_quote_author_exceeds_max_length(self):
        """SlideConfig quote_author exceeding 200 chars should raise ValidationError."""
        with pytest.raises(ValidationError):
            SlideConfig(title="OK", quote_author="a" * 201)

    def test_image_query_exceeds_max_length(self):
        """SlideConfig image_query exceeding 500 chars should raise ValidationError."""
        with pytest.raises(ValidationError):
            SlideConfig(title="OK", image_query="q" * 501)

    def test_left_title_exceeds_max_length(self):
        """SlideConfig left_title exceeding 500 chars should raise ValidationError."""
        with pytest.raises(ValidationError):
            SlideConfig(title="OK", left_title="t" * 501)

    def test_right_title_exceeds_max_length(self):
        """SlideConfig right_title exceeding 500 chars should raise ValidationError."""
        with pytest.raises(ValidationError):
            SlideConfig(title="OK", right_title="t" * 501)

    def test_quote_context_exceeds_max_length(self):
        """SlideConfig quote_context exceeding 500 chars should raise ValidationError."""
        with pytest.raises(ValidationError):
            SlideConfig(title="OK", quote_context="c" * 501)


class TestChartDataNonFiniteValues:
    """Tests for ChartData rejecting non-finite float values."""

    def test_rejects_nan(self):
        """ChartData should reject NaN values."""
        with pytest.raises(ValidationError, match="finite"):
            ChartData(
                chart_type=ChartType.BAR,
                title="Test",
                categories=["A", "B"],
                values=[1.0, float("nan")],
            )

    def test_rejects_positive_inf(self):
        """ChartData should reject positive infinity values."""
        with pytest.raises(ValidationError, match="finite"):
            ChartData(
                chart_type=ChartType.BAR,
                title="Test",
                categories=["A"],
                values=[float("inf")],
            )

    def test_rejects_negative_inf(self):
        """ChartData should reject negative infinity values."""
        with pytest.raises(ValidationError, match="finite"):
            ChartData(
                chart_type=ChartType.BAR,
                title="Test",
                categories=["A"],
                values=[float("-inf")],
            )


