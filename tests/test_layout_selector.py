from autoppt.data_types import ChartData, ChartType, SlideConfig, SlideLayout, SlideSpec, SlideType, StatisticData
from autoppt.layout_selector import LayoutSelector


def test_layout_selector_maps_statistics_slide():
    selector = LayoutSelector()
    slide_config = SlideConfig(
        title="Stats",
        bullets=[],
        slide_type=SlideType.STATISTICS,
        statistics=[StatisticData(value="42%", label="Growth")],
        citations=["https://example.com"],
    )

    slide_spec = selector.slide_from_config(slide_config)

    assert slide_spec.layout == SlideLayout.STATISTICS
    assert slide_spec.statistics is not None


def test_layout_selector_maps_chart_slide():
    selector = LayoutSelector()
    slide_config = SlideConfig(
        title="Chart",
        bullets=[],
        slide_type=SlideType.CHART,
        chart_data=ChartData(
            chart_type=ChartType.COLUMN,
            title="Quarterly Growth",
            categories=["Q1", "Q2"],
            values=[1.0, 2.0],
        ),
    )

    slide_spec = selector.slide_from_config(slide_config)

    assert slide_spec.layout == SlideLayout.CHART
    assert slide_spec.chart_data is not None


def test_layout_selector_maps_quote_slide():
    selector = LayoutSelector()
    slide_config = SlideConfig(
        title="Quote",
        bullets=[],
        slide_type=SlideType.QUOTE,
        quote_text="Execution beats intention.",
        quote_author="AutoPPT",
        quote_context="Mock source",
        citations=["https://example.com/quote"],
        speaker_notes="Quote notes",
    )

    slide_spec = selector.slide_from_config(slide_config)

    assert slide_spec.layout == SlideLayout.QUOTE
    assert slide_spec.title == "Quote"
    assert slide_spec.quote_author == "AutoPPT"
    assert slide_spec.citations == ["https://example.com/quote"]
    assert slide_spec.speaker_notes == "Quote notes"


def test_layout_selector_maps_comparison_slide():
    selector = LayoutSelector()
    slide_config = SlideConfig(
        title="Comparison",
        bullets=[],
        slide_type=SlideType.COMPARISON,
        left_title="Option A",
        right_title="Option B",
        left_bullets=["Fast", "Cheap"],
        right_bullets=["Reliable", "Scalable"],
        citations=["https://example.com/compare"],
    )

    slide_spec = selector.slide_from_config(slide_config)

    assert slide_spec.layout == SlideLayout.COMPARISON
    assert slide_spec.left_title == "Option A"
    assert slide_spec.citations == ["https://example.com/compare"]


def test_layout_selector_maps_two_column_slide():
    selector = LayoutSelector()
    slide_config = SlideConfig(
        title="Framework",
        bullets=[],
        slide_type=SlideType.TWO_COLUMN,
        left_title="Build",
        right_title="Scale",
        left_bullets=["Pilot workflow", "Measure outcomes"],
        right_bullets=["Expand coverage", "Automate reporting"],
        citations=["https://example.com/framework"],
        speaker_notes="Walk the audience through both phases.",
    )

    slide_spec = selector.slide_from_config(slide_config)

    assert slide_spec.layout == SlideLayout.TWO_COLUMN
    assert slide_spec.left_title == "Build"
    assert slide_spec.right_title == "Scale"
    assert slide_spec.citations == ["https://example.com/framework"]
    assert slide_spec.speaker_notes == "Walk the audience through both phases."


def test_layout_selector_splits_bullets_for_rich_layout_fallback():
    selector = LayoutSelector()
    slide_config = SlideConfig(
        title="Current vs Future",
        bullets=["Legacy tooling", "Manual QA", "Automated checks", "Faster delivery"],
        slide_type=SlideType.COMPARISON,
    )

    slide_spec = selector.slide_from_config(slide_config)

    assert slide_spec.layout == SlideLayout.COMPARISON
    assert slide_spec.left_bullets == ["Legacy tooling", "Manual QA"]
    assert slide_spec.right_bullets == ["Automated checks", "Faster delivery"]


def test_layout_selector_maps_image_slide():
    selector = LayoutSelector()
    slide_config = SlideConfig(
        title="Visual",
        bullets=["Caption text"],
        slide_type=SlideType.IMAGE,
    )

    slide_spec = selector.slide_from_config(slide_config, image_path="/tmp/test.jpg")

    assert slide_spec.layout == SlideLayout.IMAGE
    assert slide_spec.image_path == "/tmp/test.jpg"
    assert slide_spec.image_caption == "Caption text"


def test_layout_selector_content_fallback_for_chart_without_data():
    selector = LayoutSelector()
    slide_config = SlideConfig(
        title="Trend",
        bullets=["Point 1", "Point 2"],
        slide_type=SlideType.CHART,
        chart_data=None,
    )

    slide_spec = selector.slide_from_config(slide_config)

    assert slide_spec.layout == SlideLayout.CONTENT


def test_remix_slide_to_two_column():
    selector = LayoutSelector()
    original = SlideSpec(
        layout=SlideLayout.CONTENT,
        title="Overview",
        bullets=["A", "B", "C", "D"],
        editable=True,
    )

    result = selector.remix_slide(original, SlideLayout.TWO_COLUMN)

    assert result.layout == SlideLayout.TWO_COLUMN
    assert result.left_bullets == ["A", "B"]
    assert result.right_bullets == ["C", "D"]


def test_remix_slide_to_quote():
    selector = LayoutSelector()
    original = SlideSpec(
        layout=SlideLayout.CONTENT,
        title="Insight",
        bullets=["The future belongs to the bold."],
        editable=True,
        source_title="Research Desk",
    )

    result = selector.remix_slide(original, SlideLayout.QUOTE)

    assert result.layout == SlideLayout.QUOTE
    assert result.quote_text == "The future belongs to the bold."
    assert result.quote_author == "Research Desk"


def test_split_single_bullet_puts_all_in_left():
    """Single bullet should go to left column only; right column stays empty."""
    selector = LayoutSelector()
    left, right = selector._split_bullets_into_columns(["Only bullet"])
    assert left == ["Only bullet"]
    assert right == []


def test_comparison_slide_single_bullet_demotes_to_content():
    """A COMPARISON slide with a single bullet should demote to CONTENT (empty column)."""
    selector = LayoutSelector()
    slide_config = SlideConfig(
        title="Comparison Single",
        bullets=["Only point"],
        slide_type=SlideType.COMPARISON,
    )

    slide_spec = selector.slide_from_config(slide_config)

    assert slide_spec.layout == SlideLayout.CONTENT


def test_split_empty_bullets():
    """Empty bullet list should return two empty lists."""
    selector = LayoutSelector()
    left, right = selector._split_bullets_into_columns([])
    assert left == []
    assert right == []


def test_split_two_bullets():
    """Two bullets should split evenly."""
    selector = LayoutSelector()
    left, right = selector._split_bullets_into_columns(["A", "B"])
    assert left == ["A"]
    assert right == ["B"]


# --- remix_slide coverage (lines 224-299) ---


def test_remix_slide_to_content_from_two_column():
    """Convert a two-column slide to content layout by flattening bullets."""
    selector = LayoutSelector()
    original = SlideSpec(
        layout=SlideLayout.TWO_COLUMN,
        title="Framework",
        left_bullets=["Build", "Test"],
        right_bullets=["Deploy", "Monitor"],
        editable=True,
    )
    result = selector.remix_slide(original, SlideLayout.CONTENT)
    assert result.layout == SlideLayout.CONTENT
    assert result.bullets == ["Build", "Test", "Deploy", "Monitor"]


def test_remix_slide_to_comparison_from_content():
    """Convert a content slide to comparison layout."""
    selector = LayoutSelector()
    original = SlideSpec(
        layout=SlideLayout.CONTENT,
        title="Analysis",
        bullets=["Fast", "Cheap", "Reliable", "Scalable"],
        editable=True,
    )
    result = selector.remix_slide(original, SlideLayout.COMPARISON)
    assert result.layout == SlideLayout.COMPARISON
    assert result.left_title == "Current State"
    assert result.right_title == "Future State"
    assert result.left_bullets == ["Fast", "Cheap"]
    assert result.right_bullets == ["Reliable", "Scalable"]


def test_remix_slide_to_quote_from_content():
    """Convert a content slide to quote layout using first bullet as quote text."""
    selector = LayoutSelector()
    original = SlideSpec(
        layout=SlideLayout.CONTENT,
        title="Insight",
        bullets=["Innovation drives growth.", "Second point."],
        editable=True,
        source_title="Research Team",
        source_section="Strategy",
    )
    result = selector.remix_slide(original, SlideLayout.QUOTE)
    assert result.layout == SlideLayout.QUOTE
    assert result.quote_text == "Innovation drives growth."
    assert result.quote_author == "Research Team"
    assert result.quote_context == "Strategy"


def test_remix_slide_fallback_unsupported_returns_deep_copy():
    """Unsupported target layout (e.g. IMAGE) returns a deep copy of the original."""
    selector = LayoutSelector()
    original = SlideSpec(
        layout=SlideLayout.CONTENT,
        title="Test",
        bullets=["A", "B"],
        editable=True,
    )
    result = selector.remix_slide(original, SlideLayout.IMAGE)
    assert result.layout == SlideLayout.CONTENT
    assert result.title == "Test"
    assert result.bullets == ["A", "B"]
    # Verify it is a deep copy, not the same object
    assert result is not original


# --- _flatten_slide_bullets coverage (lines 286-293) ---


def test_flatten_slide_bullets_from_statistics():
    """Statistics data should be flattened into label: value strings."""
    selector = LayoutSelector()
    slide = SlideSpec(
        layout=SlideLayout.STATISTICS,
        title="KPIs",
        statistics=[
            StatisticData(value="42%", label="Growth"),
            StatisticData(value="$1.2M", label="Revenue"),
        ],
    )
    result = selector._flatten_slide_bullets(slide)
    assert result == ["Growth: 42%", "Revenue: $1.2M"]


def test_flatten_slide_bullets_from_chart_data():
    """Chart data should be flattened into category: value strings."""
    selector = LayoutSelector()
    slide = SlideSpec(
        layout=SlideLayout.CHART,
        title="Quarterly",
        chart_data=ChartData(
            chart_type=ChartType.COLUMN,
            title="Revenue",
            categories=["Q1", "Q2", "Q3"],
            values=[100.0, 200.0, 350.0],
        ),
    )
    result = selector._flatten_slide_bullets(slide)
    assert result == ["Q1: 100.0", "Q2: 200.0", "Q3: 350.0"]


# --- _quote_text_for_slide coverage (line 299) ---


def test_quote_text_for_slide_empty_bullets_returns_title():
    """When no bullets exist at all, _quote_text_for_slide returns the title."""
    selector = LayoutSelector()
    slide = SlideSpec(
        layout=SlideLayout.CONTENT,
        title="Fallback Title",
    )
    result = selector._quote_text_for_slide(slide)
    assert result == "Fallback Title"


# --- Uncovered line coverage ---


def test_quote_slide_missing_quote_text_demotes_to_content():
    """QUOTE slide without quote_text or author should demote to CONTENT layout."""
    selector = LayoutSelector()
    slide_config = SlideConfig(
        title="Missing Quote",
        bullets=["Fallback bullet"],
        slide_type=SlideType.QUOTE,
        quote_text="",
        quote_author="",
    )

    slide_spec = selector.slide_from_config(slide_config)

    assert slide_spec.layout == SlideLayout.CONTENT
    assert slide_spec.title == "Missing Quote"
    assert slide_spec.bullets == ["Fallback bullet"]


def test_columns_for_slide_fallback_without_left_right_bullets():
    """_columns_for_slide should split flattened bullets when no left/right bullets exist."""
    selector = LayoutSelector()
    slide = SlideSpec(
        layout=SlideLayout.CONTENT,
        title="Plain",
        bullets=["Alpha", "Beta", "Gamma", "Delta"],
    )

    left, right = selector._columns_for_slide(slide)

    assert left == ["Alpha", "Beta"]
    assert right == ["Gamma", "Delta"]


def test_flatten_slide_bullets_from_quote_text_only():
    """Slide with only quote_text (no bullets, no left/right) returns [quote_text]."""
    selector = LayoutSelector()
    slide = SlideSpec(
        layout=SlideLayout.QUOTE,
        title="Wisdom",
        quote_text="Knowledge is power.",
    )

    result = selector._flatten_slide_bullets(slide)

    assert result == ["Knowledge is power."]


def test_safe_layout_from_plan_returns_none_for_no_plan():
    selector = LayoutSelector()
    assert selector._safe_layout_from_plan(None) is None


def test_safe_layout_from_plan_maps_valid_type():
    from autoppt.data_types import SlidePlan
    selector = LayoutSelector()
    plan = SlidePlan(
        title="Test",
        topic="Test",
        section_title="Section",
        slide_type=SlideType.CONTENT,
        evidence_focus=[],
        rationale="test",
    )
    result = selector._safe_layout_from_plan(plan)
    assert result == SlideLayout.CONTENT


def test_safe_layout_from_plan_returns_none_for_unknown_type():
    """If slide_type value has no matching SlideLayout, return None."""
    from unittest.mock import MagicMock
    selector = LayoutSelector()
    plan = MagicMock()
    plan.slide_type.value = "nonexistent_layout"
    result = selector._safe_layout_from_plan(plan)
    assert result is None


def test_flatten_slide_bullets_with_partial_none_columns():
    """When one of left/right bullets is None and the other is a list,
    _flatten_slide_bullets should not raise TypeError.

    Uses model_construct to bypass validation, simulating data that
    arrives with a None column (e.g. from deserialized or LLM output).
    """
    selector = LayoutSelector()
    slide = SlideSpec.model_construct(
        layout=SlideLayout.TWO_COLUMN,
        title="Partial",
        left_bullets=["Alpha", "Beta"],
        right_bullets=None,
    )
    result = selector._flatten_slide_bullets(slide)
    assert result == ["Alpha", "Beta"]

    slide2 = SlideSpec.model_construct(
        layout=SlideLayout.TWO_COLUMN,
        title="Partial Reverse",
        left_bullets=None,
        right_bullets=["Gamma", "Delta"],
    )
    result2 = selector._flatten_slide_bullets(slide2)
    assert result2 == ["Gamma", "Delta"]


def test_columns_for_slide_with_existing_columns():
    """_columns_for_slide should return existing columns when both are set."""
    selector = LayoutSelector()
    slide_spec = SlideSpec(
        layout=SlideLayout.TWO_COLUMN,
        title="Test",
        bullets=[],
        left_bullets=["Left A", "Left B"],
        right_bullets=["Right A", "Right B"],
    )
    left, right = selector._columns_for_slide(slide_spec)
    assert left == ["Left A", "Left B"]
    assert right == ["Right A", "Right B"]


def test_coerce_points_with_string_wraps_in_list():
    """_coerce_points should wrap a bare string in a list instead of iterating chars."""
    result = LayoutSelector._coerce_points("single bullet point")
    assert result == ["single bullet point"]


def test_coerce_points_with_none_returns_empty():
    result = LayoutSelector._coerce_points(None)
    assert result == []


def test_coerce_points_with_list_passes_through():
    result = LayoutSelector._coerce_points(["a", "b", "c"])
    assert result == ["a", "b", "c"]


def test_comparison_slide_string_points_handled():
    """comparison_slide should handle string points without character-level iteration."""
    selector = LayoutSelector()
    spec = selector.comparison_slide(
        title="A vs B",
        item_a={"name": "Option A", "points": "This is a single point"},
        item_b={"name": "Option B", "points": ["Point 1", "Point 2"]},
    )
    assert spec.left_bullets == ["This is a single point"]
    assert spec.right_bullets == ["Point 1", "Point 2"]


def test_comparison_uses_explicit_left_right_bullets_over_split():
    """When a SlideConfig has both left_bullets and right_bullets set,
    slide_from_config should use them directly instead of splitting bullets."""
    selector = LayoutSelector()
    slide_config = SlideConfig(
        title="Explicit Comparison",
        bullets=["Should", "Not", "Be", "Used"],
        slide_type=SlideType.COMPARISON,
        left_title="Pros",
        right_title="Cons",
        left_bullets=["Fast", "Cheap"],
        right_bullets=["Fragile", "Limited"],
    )

    slide_spec = selector.slide_from_config(slide_config)

    assert slide_spec.layout == SlideLayout.COMPARISON
    assert slide_spec.left_bullets == ["Fast", "Cheap"]
    assert slide_spec.right_bullets == ["Fragile", "Limited"]
    assert slide_spec.left_title == "Pros"
    assert slide_spec.right_title == "Cons"


def test_comparison_one_side_explicit_demotes_to_content():
    """When a SlideConfig has left_bullets set but right_bullets empty,
    slide_from_config should demote to CONTENT (empty column is lopsided)."""
    selector = LayoutSelector()
    slide_config = SlideConfig(
        title="One-Sided Comparison",
        bullets=["Fallback A", "Fallback B", "Fallback C", "Fallback D"],
        slide_type=SlideType.COMPARISON,
        left_bullets=["A", "B"],
        right_bullets=[],
    )

    slide_spec = selector.slide_from_config(slide_config)

    assert slide_spec.layout == SlideLayout.CONTENT


def test_two_column_uses_explicit_left_right_bullets_over_split():
    """When a SlideConfig has both left_bullets and right_bullets set,
    slide_from_config should use them directly instead of splitting bullets."""
    selector = LayoutSelector()
    slide_config = SlideConfig(
        title="Explicit Two Column",
        bullets=["Should", "Not", "Be", "Used"],
        slide_type=SlideType.TWO_COLUMN,
        left_title="Phase 1",
        right_title="Phase 2",
        left_bullets=["Plan", "Design"],
        right_bullets=["Build", "Ship"],
    )

    slide_spec = selector.slide_from_config(slide_config)

    assert slide_spec.layout == SlideLayout.TWO_COLUMN
    assert slide_spec.left_bullets == ["Plan", "Design"]
    assert slide_spec.right_bullets == ["Build", "Ship"]
    assert slide_spec.left_title == "Phase 1"
    assert slide_spec.right_title == "Phase 2"


def test_two_column_one_side_explicit_demotes_to_content():
    """When a SlideConfig has left_bullets set but right_bullets empty,
    slide_from_config should demote to CONTENT (empty column is lopsided)."""
    selector = LayoutSelector()
    slide_config = SlideConfig(
        title="One-Sided Two Column",
        bullets=["Fallback A", "Fallback B", "Fallback C", "Fallback D"],
        slide_type=SlideType.TWO_COLUMN,
        left_bullets=["A", "B"],
        right_bullets=[],
    )

    slide_spec = selector.slide_from_config(slide_config)

    assert slide_spec.layout == SlideLayout.CONTENT


def test_comparison_both_explicit_empty_falls_back_to_split():
    """When both left_bullets and right_bullets are empty lists,
    slide_from_config should fall back to splitting from bullets."""
    selector = LayoutSelector()
    slide_config = SlideConfig(
        title="Both Empty Explicit",
        bullets=["A", "B", "C", "D"],
        slide_type=SlideType.COMPARISON,
        left_bullets=[],
        right_bullets=[],
    )

    slide_spec = selector.slide_from_config(slide_config)

    assert slide_spec.layout == SlideLayout.COMPARISON
    assert slide_spec.left_bullets == ["A", "B"]
    assert slide_spec.right_bullets == ["C", "D"]


def test_two_column_both_explicit_empty_falls_back_to_split():
    """When both left_bullets and right_bullets are empty lists for TWO_COLUMN,
    slide_from_config should fall back to splitting from bullets."""
    selector = LayoutSelector()
    slide_config = SlideConfig(
        title="Both Empty Two Column",
        bullets=["X", "Y", "Z", "W"],
        slide_type=SlideType.TWO_COLUMN,
        left_bullets=[],
        right_bullets=[],
    )

    slide_spec = selector.slide_from_config(slide_config)

    assert slide_spec.layout == SlideLayout.TWO_COLUMN
    assert slide_spec.left_bullets == ["X", "Y"]
    assert slide_spec.right_bullets == ["Z", "W"]


def test_remix_unsupported_layout_returns_copy():
    """When remix_slide is called with an unsupported target layout like STATISTICS,
    it should return a deep copy of the original slide (not crash)."""
    selector = LayoutSelector()
    original = SlideSpec(
        layout=SlideLayout.CONTENT,
        title="Deep Copy Check",
        bullets=["Point 1", "Point 2"],
        editable=True,
    )

    result = selector.remix_slide(original, SlideLayout.STATISTICS)

    assert result.layout == SlideLayout.CONTENT
    assert result.title == "Deep Copy Check"
    assert result.bullets == ["Point 1", "Point 2"]
    assert result is not original
