from autoppt.data_types import ChartData, ChartType, SlideConfig, SlideLayout, SlideType, StatisticData
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
