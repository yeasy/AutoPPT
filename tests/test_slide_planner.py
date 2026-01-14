from autoppt.data_types import SlideType
from autoppt.slide_planner import SlidePlanner


def test_slide_planner_honors_forced_layout():
    planner = SlidePlanner()

    plan = planner.plan(
        slide_title="Execution Priorities",
        section_title="Strategy",
        topic="AI Transformation",
        force_slide_type=SlideType.COMPARISON,
    )

    assert plan.slide_type == SlideType.COMPARISON
    assert plan.left_title is not None
    assert plan.right_title is not None


def test_slide_planner_detects_chart_titles():
    planner = SlidePlanner()

    plan = planner.plan(
        slide_title="Adoption Trend by Year",
        section_title="Metrics",
        topic="AI Transformation",
        context="2023 adoption 18%, 2024 adoption 27%, 2025 forecast 39%",
    )

    assert plan.slide_type == SlideType.CHART
