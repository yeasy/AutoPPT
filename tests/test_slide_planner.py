from autoppt.data_types import SlideConfig, SlideLayout, SlidePlan, SlideSpec, SlideType
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


def test_slide_planner_detects_quote_from_title():
    planner = SlidePlanner()
    plan = planner.plan(
        slide_title="Leadership Vision",
        section_title="Culture",
        topic="Digital Transformation",
    )
    assert plan.slide_type == SlideType.QUOTE


def test_slide_planner_detects_vs_comparison():
    planner = SlidePlanner()
    plan = planner.plan(
        slide_title="Cloud vs On-Premise",
        section_title="Infrastructure",
        topic="IT Strategy",
    )
    assert plan.slide_type == SlideType.COMPARISON
    assert plan.left_title == "Cloud"
    assert plan.right_title == "On-Premise"


def test_slide_planner_detects_statistics():
    planner = SlidePlanner()
    plan = planner.plan(
        slide_title="Key Metrics and KPIs",
        section_title="Performance",
        topic="Sales Growth",
    )
    assert plan.slide_type == SlideType.STATISTICS


def test_slide_planner_detects_two_column_framework():
    planner = SlidePlanner()
    plan = planner.plan(
        slide_title="Implementation Framework",
        section_title="Execution",
        topic="DevOps",
    )
    assert plan.slide_type == SlideType.TWO_COLUMN


def test_slide_planner_detects_image_showcase():
    planner = SlidePlanner()
    plan = planner.plan(
        slide_title="Product Showcase",
        section_title="Launch",
        topic="Mobile App",
    )
    assert plan.slide_type == SlideType.IMAGE


def test_slide_planner_defaults_to_content():
    planner = SlidePlanner()
    plan = planner.plan(
        slide_title="General Overview",
        section_title="Introduction",
        topic="Quarterly Update",
    )
    assert plan.slide_type == SlideType.CONTENT


def test_slide_planner_remix_instruction_quote():
    planner = SlidePlanner()
    plan = planner.plan(
        slide_title="Core Values",
        section_title="Culture",
        topic="Company",
        remix_instruction="Turn this into a quote slide",
    )
    assert plan.slide_type == SlideType.QUOTE


def test_slide_planner_remix_instruction_comparison():
    planner = SlidePlanner()
    plan = planner.plan(
        slide_title="Options",
        section_title="Strategy",
        topic="Migration",
        remix_instruction="Compare the two approaches",
    )
    assert plan.slide_type == SlideType.COMPARISON


def test_apply_plan_normalizes_comparison_from_content():
    planner = SlidePlanner()
    from autoppt.data_types import SlidePlan
    plan = SlidePlan(
        title="Test",
        slide_type=SlideType.COMPARISON,
        left_title="Before",
        right_title="After",
    )
    config = SlideConfig(
        title="Test",
        slide_type=SlideType.CONTENT,
        bullets=["Point A", "Point B", "Point C", "Point D"],
    )
    result = planner.apply_plan(config, plan)
    assert result.slide_type == SlideType.COMPARISON
    assert result.left_title == "Before"
    assert result.right_title == "After"


def test_apply_plan_respects_layout_locked():
    planner = SlidePlanner()
    from autoppt.data_types import SlidePlan
    plan = SlidePlan(
        title="Test",
        slide_type=SlideType.TWO_COLUMN,
        layout_locked=True,
    )
    config = SlideConfig(
        title="Test",
        slide_type=SlideType.CONTENT,
        bullets=["A", "B"],
        quote_text="Hello",
        quote_author="Author",
    )
    result = planner.apply_plan(config, plan)
    assert result.slide_type == SlideType.TWO_COLUMN


def test_slide_planner_handles_empty_title():
    planner = SlidePlanner()
    plan = planner.plan(
        slide_title="",
        section_title="Fallback Section",
        topic="Test",
    )
    assert plan.title == "Fallback Section"
    assert plan.slide_type == SlideType.CONTENT


def test_slide_planner_handles_none_title():
    planner = SlidePlanner()
    plan = planner.plan(
        slide_title=None,
        section_title="",
        topic="Test",
    )
    assert plan.title == "Untitled Slide"


def test_apply_plan_quote_with_empty_bullets_falls_back():
    planner = SlidePlanner()
    from autoppt.data_types import SlidePlan
    plan = SlidePlan(
        title="Vision",
        slide_type=SlideType.QUOTE,
        quote_author="Someone",
    )
    config = SlideConfig(
        title="Vision",
        bullets=[],
        slide_type=SlideType.CONTENT,
        quote_text=None,
    )
    result = planner.apply_plan(config, plan)
    # No quote_text and no bullets -> should fall back to CONTENT
    assert result.slide_type == SlideType.CONTENT


def test_slide_planner_preserves_current_slide_layout():
    planner = SlidePlanner()
    current = SlideSpec(
        layout=SlideLayout.COMPARISON,
        title="Existing",
        left_title="A",
        right_title="B",
    )
    plan = planner.plan(
        slide_title="General Topic",
        section_title="Section",
        topic="Topic",
        current_slide=current,
    )
    assert plan.slide_type == SlideType.COMPARISON


def test_split_bullets_single_item_empty_right():
    """Single bullet should stay in left column; right column should be empty."""
    planner = SlidePlanner()
    config = SlideConfig(
        title="Test",
        bullets=["Only item"],
        slide_type=SlideType.TWO_COLUMN,
        citations=[],
    )
    left, right = planner._split_bullets(config)
    assert left == ["Only item"]
    assert right == []


def test_split_bullets_empty_bullets_empty_columns():
    """Zero bullets should produce two empty columns."""
    planner = SlidePlanner()
    config = SlideConfig(
        title="Test",
        bullets=[],
        slide_type=SlideType.TWO_COLUMN,
        citations=[],
    )
    left, right = planner._split_bullets(config)
    assert left == []
    assert right == []


def test_split_bullets_with_explicit_columns():
    """Explicit left/right bullets should be used as-is."""
    planner = SlidePlanner()
    config = SlideConfig(
        title="Test",
        bullets=["Unused"],
        slide_type=SlideType.TWO_COLUMN,
        left_bullets=["L1", "L2"],
        right_bullets=["R1"],
        citations=[],
    )
    left, right = planner._split_bullets(config)
    assert left == ["L1", "L2"]
    assert right == ["R1"]


# --- _fill_layout_hints coverage (lines 274-288) ---


def test_fill_layout_hints_quote_defaults():
    """QUOTE type should get default quote_author and quote_context."""
    from autoppt.data_types import SlidePlan

    planner = SlidePlanner()
    plan = SlidePlan(
        title="Vision Statement",
        slide_type=SlideType.QUOTE,
        section_title="Culture",
        topic="Leadership",
    )
    planner._fill_layout_hints(plan, "Vision Statement", "Culture", "Leadership")
    assert plan.quote_author == "Industry Perspective"
    assert plan.quote_context == "Culture"


def test_fill_layout_hints_quote_defaults_fallback_to_topic():
    """QUOTE with empty section_title should fall back to topic for quote_context."""
    from autoppt.data_types import SlidePlan

    planner = SlidePlanner()
    plan = SlidePlan(
        title="Vision",
        slide_type=SlideType.QUOTE,
    )
    planner._fill_layout_hints(plan, "Vision", "", "AI Strategy")
    assert plan.quote_author == "Industry Perspective"
    assert plan.quote_context == "AI Strategy"


def test_fill_layout_hints_comparison_with_vs_title():
    """COMPARISON type with 'vs' in title should infer left/right titles."""
    from autoppt.data_types import SlidePlan

    planner = SlidePlanner()
    plan = SlidePlan(
        title="Cloud vs On-Premise",
        slide_type=SlideType.COMPARISON,
    )
    planner._fill_layout_hints(plan, "Cloud vs On-Premise", "Infra", "IT")
    assert plan.left_title == "Cloud"
    assert plan.right_title == "On-Premise"


def test_fill_layout_hints_two_column_with_framework():
    """TWO_COLUMN type with 'framework' in title should get framework defaults."""
    from autoppt.data_types import SlidePlan

    planner = SlidePlanner()
    plan = SlidePlan(
        title="Implementation Framework",
        slide_type=SlideType.TWO_COLUMN,
    )
    planner._fill_layout_hints(plan, "Implementation Framework", "Exec", "DevOps")
    assert plan.left_title == "Core Elements"
    assert plan.right_title == "Execution Moves"


# --- plan() with force_slide_type covering _fill_layout_hints branch (lines 55-60, 77-82) ---


def test_plan_force_two_column_with_framework_title():
    """force_slide_type=TWO_COLUMN with 'framework' title fills layout hints."""
    planner = SlidePlanner()
    plan = planner.plan(
        slide_title="Innovation Framework",
        section_title="Strategy",
        topic="Digital",
        force_slide_type=SlideType.TWO_COLUMN,
    )
    assert plan.slide_type == SlideType.TWO_COLUMN
    assert plan.layout_locked is True
    assert plan.left_title == "Core Elements"
    assert plan.right_title == "Execution Moves"


def test_plan_force_quote_fills_defaults():
    """force_slide_type=QUOTE fills quote_author and quote_context."""
    planner = SlidePlanner()
    plan = planner.plan(
        slide_title="Guiding Principle",
        section_title="Values",
        topic="Company Culture",
        force_slide_type=SlideType.QUOTE,
    )
    assert plan.slide_type == SlideType.QUOTE
    assert plan.layout_locked is True
    assert plan.quote_author == "Industry Perspective"
    assert plan.quote_context == "Values"


# --- _infer_from_content coverage (lines 247-259) ---


def test_infer_from_content_left_right_bullets_comparison_title():
    """left/right bullets with a comparison title should infer COMPARISON."""
    planner = SlidePlanner()
    config = SlideConfig(
        title="Cloud vs On-Premise",
        bullets=[],
        left_bullets=["Scalable", "Flexible"],
        right_bullets=["Secure", "Owned"],
    )
    result = planner._infer_from_content(config)
    assert result == SlideType.COMPARISON


def test_infer_from_content_left_right_bullets_no_comparison_title():
    """left/right bullets without a comparison title should infer TWO_COLUMN."""
    planner = SlidePlanner()
    config = SlideConfig(
        title="Key Takeaways",
        bullets=[],
        left_bullets=["Point A", "Point B"],
        right_bullets=["Point C", "Point D"],
    )
    result = planner._infer_from_content(config)
    assert result == SlideType.TWO_COLUMN


# --- _infer_two_column_titles coverage (lines 236-245) ---


def test_infer_two_column_titles_roadmap():
    """'roadmap' keyword should return Near Term / Next Phase."""
    planner = SlidePlanner()
    result = planner._infer_two_column_titles("Product Roadmap")
    assert result == ("Near Term", "Next Phase")


def test_infer_two_column_titles_no_match():
    """Title without any matching keyword should return None."""
    planner = SlidePlanner()
    result = planner._infer_two_column_titles("General Overview")
    assert result is None


# --- Evidence focus filtering (line 41) ---


def test_evidence_focus_excludes_empty_section_title():
    """Empty section_title should not produce empty strings in evidence_focus."""
    planner = SlidePlanner()
    plan = planner.plan(
        slide_title="Overview",
        section_title="",
        topic="AI",
    )
    assert "" not in plan.evidence_focus
    assert all(s for s in plan.evidence_focus)


# --- remix instruction two-column branch (lines 77-82) ---


def test_remix_instruction_two_column():
    """Remix instruction with 'framework' triggers TWO_COLUMN branch."""
    planner = SlidePlanner()
    plan = planner.plan(
        slide_title="Strategy Overview",
        section_title="Planning",
        topic="Growth",
        remix_instruction="Show this as a framework layout",
    )
    assert plan.slide_type == SlideType.TWO_COLUMN


# --- _infer_comparison_titles: pair-keyword match (line 230) ---


def test_infer_comparison_titles_pair_keyword():
    """Title containing both words of a _COMPARISON_PAIRS entry returns them title-cased."""
    planner = SlidePlanner()
    result = planner._infer_comparison_titles("Weighing Pros and Cons")
    assert result == ("Pros", "Cons")


def test_infer_comparison_titles_benefits_risks():
    """Another pair: benefits and risks."""
    planner = SlidePlanner()
    result = planner._infer_comparison_titles("Benefits and Risks of Cloud")
    assert result == ("Benefits", "Risks")


# --- _infer_comparison_titles: fallback for comparison tokens (line 234) ---


def test_infer_comparison_titles_compare_token_fallback():
    """Title with 'compare' but no specific pair returns generic fallback."""
    planner = SlidePlanner()
    result = planner._infer_comparison_titles("Compare Options")
    assert result == ("Current Approach", "Alternative Approach")


def test_infer_comparison_titles_tradeoff_token_fallback():
    """Title with 'tradeoff' but no specific pair returns generic fallback."""
    planner = SlidePlanner()
    result = planner._infer_comparison_titles("Key Tradeoff Analysis")
    assert result == ("Current Approach", "Alternative Approach")


# --- _infer_two_column_titles: pair-keyword match (line 241) ---


def test_infer_two_column_titles_pair_keyword():
    """Title containing both words of a _COMPARISON_PAIRS entry returns them title-cased."""
    planner = SlidePlanner()
    result = planner._infer_two_column_titles("Current State and Future Vision")
    assert result == ("Current", "Future")


# --- _infer_from_content: statistics, chart, image (lines 252, 254, 256) ---


def test_infer_from_content_statistics():
    """SlideConfig with statistics set should infer STATISTICS."""
    from autoppt.data_types import StatisticData

    planner = SlidePlanner()
    config = SlideConfig(
        title="Key Numbers",
        bullets=[],
        statistics=[
            StatisticData(value="85%", label="Adoption rate"),
            StatisticData(value="$4B", label="Revenue"),
        ],
    )
    result = planner._infer_from_content(config)
    assert result == SlideType.STATISTICS


def test_infer_from_content_chart():
    """SlideConfig with chart_data set should infer CHART."""
    from autoppt.data_types import ChartData, ChartType

    planner = SlidePlanner()
    config = SlideConfig(
        title="Revenue Growth",
        bullets=[],
        chart_data=ChartData(
            chart_type=ChartType.BAR,
            title="Revenue",
            categories=["Q1", "Q2", "Q3"],
            values=[10.0, 20.0, 30.0],
        ),
    )
    result = planner._infer_from_content(config)
    assert result == SlideType.CHART


def test_infer_from_content_image():
    """SlideConfig with image_query and no bullets should infer IMAGE."""
    planner = SlidePlanner()
    config = SlideConfig(
        title="Product Demo",
        bullets=[],
        image_query="product screenshot",
    )
    result = planner._infer_from_content(config)
    assert result == SlideType.IMAGE


def test_infer_from_content_image_query_with_bullets_stays_none():
    """SlideConfig with both image_query and bullets should NOT infer IMAGE."""
    planner = SlidePlanner()
    config = SlideConfig(
        title="Product Demo",
        bullets=["Feature 1", "Feature 2", "Feature 3"],
        image_query="product screenshot",
    )
    result = planner._infer_from_content(config)
    assert result is None


# --- _first_sentence (line 272) ---


def test_first_sentence_splits_at_period():
    """Multi-sentence text returns only the first sentence."""
    planner = SlidePlanner()
    result = planner._first_sentence("This is the first. This is the second.")
    assert result == "This is the first."


def test_first_sentence_single_sentence():
    """Single sentence returns unchanged."""
    planner = SlidePlanner()
    result = planner._first_sentence("Only one sentence here")
    assert result == "Only one sentence here"


def test_first_sentence_splits_at_exclamation():
    """Splitting at exclamation mark."""
    planner = SlidePlanner()
    result = planner._first_sentence("Great news! More details follow.")
    assert result == "Great news!"


# --- evidence_focus whitespace-only strings ---


def test_evidence_focus_excludes_whitespace_only():
    """Whitespace-only section_title should not appear in evidence_focus."""
    planner = SlidePlanner()
    plan = planner.plan(
        slide_title="Overview",
        section_title="   ",
        topic="AI",
    )
    assert "" not in plan.evidence_focus
    assert all(s.strip() for s in plan.evidence_focus)


def test_slide_planner_detects_quote_from_unicode_curly_quotes_in_context():
    """Unicode curly quotes with em-dash in context should trigger quote layout."""
    planner = SlidePlanner()
    plan = planner.plan(
        slide_title="Industry Insight",
        section_title="Market",
        topic="AI",
        context='\u201cInnovation distinguishes between a leader and a follower.\u201d \u2014 Steve Jobs',
    )
    assert plan.slide_type == SlideType.QUOTE


def test_quote_demotion_clears_quote_metadata():
    """When a QUOTE slide is demoted to CONTENT, quote fields should not be set."""
    planner = SlidePlanner()
    plan = SlidePlan(
        title="Test",
        topic="Topic",
        section_title="Section",
        slide_type=SlideType.QUOTE,
        evidence_focus=[],
        rationale="test",
        quote_author="",  # No author -> demotion
    )
    config = SlideConfig(
        title="Test",
        bullets=["Some text here."],
        slide_type=SlideType.CONTENT,
        # No quote_text, no quote_author -> should demote
    )
    result = planner.apply_plan(config, plan)
    assert result.slide_type == SlideType.CONTENT
    assert not result.quote_text
    assert not result.quote_author


def test_vs_word_boundary_match():
    """'vs' should match as word boundary, not as substring in 'canvas'."""
    from autoppt.data_types import SlideSpec, SlideLayout
    planner = SlidePlanner()
    # "canvas" contains "vs" but should NOT trigger comparison
    plan_canvas = planner.plan(
        slide_title="Canvas Design",
        section_title="Art",
        topic="Design",
        remix_instruction="redesign the canvas layout",
    )
    assert plan_canvas.slide_type != SlideType.COMPARISON

    # "A vs B" should trigger comparison
    plan_vs = planner.plan(
        slide_title="Option A",
        section_title="Analysis",
        topic="Comparison",
        remix_instruction="show this as A vs B",
    )
    assert plan_vs.slide_type == SlideType.COMPARISON


def test_comparison_pair_word_boundary_no_false_positive():
    """'today'/'tomorrow' should not match as substrings inside other words."""
    planner = SlidePlanner()
    result = planner._infer_comparison_titles("Today's Tomorrowland")
    assert result is None


def test_vs_dot_parsing_strips_leading_dot():
    """'Cloud vs. On-Premise' should produce clean titles without leading dots."""
    planner = SlidePlanner()
    result = planner._infer_comparison_titles("Cloud vs. On-Premise")
    assert result is not None
    left, right = result
    assert not left.startswith(".")
    assert not right.startswith(".")
    assert "Cloud" in left
    assert "On-Premise" in right


def test_vs_dot_only_right_side():
    """'A vs.' with nothing after the dot should return None or empty right."""
    planner = SlidePlanner()
    result = planner._infer_comparison_titles("Cloud vs.")
    # After stripping " :-.", the right side is empty, so result should be None
    assert result is None


def test_vs_dot_plan_produces_comparison():
    """Full plan() should detect 'vs.' title as comparison."""
    planner = SlidePlanner()
    plan = planner.plan(
        slide_title="React vs. Angular",
        section_title="Frontend",
        topic="Web Development",
    )
    assert plan.slide_type == SlideType.COMPARISON
    assert plan.left_title is not None
    assert plan.right_title is not None
    assert not plan.left_title.startswith(".")
    assert not plan.right_title.startswith(".")
