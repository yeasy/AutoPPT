import pytest

from autoppt.data_types import ChartData, ChartType, DeckSpec, SlideLayout, SlideSpec, StatisticData
from autoppt.deck_qa import DeckQA
from autoppt.layout_selector import LayoutSelector


def test_deck_qa_flags_duplicate_titles():
    deck = DeckSpec(
        title="Deck",
        topic="Topic",
        slides=[
            SlideSpec(layout=SlideLayout.CONTENT, title="Duplicate", bullets=["One"]),
            SlideSpec(layout=SlideLayout.CONTENT, title="Duplicate", bullets=["Two"]),
        ],
    )

    report = DeckQA().analyze(deck)

    assert any(issue.code == "duplicate_title" for issue in report.issues)


def test_deck_qa_flags_empty_content():
    deck = DeckSpec(
        title="Deck",
        topic="Topic",
        slides=[SlideSpec(layout=SlideLayout.CONTENT, title="Empty", bullets=[])],
    )

    report = DeckQA().analyze(deck)

    assert any(issue.code == "empty_content" for issue in report.issues)


def test_deck_qa_flags_incomplete_quote():
    deck = DeckSpec(
        title="Deck",
        topic="Topic",
        slides=[SlideSpec(layout=SlideLayout.QUOTE, title="Quote", quote_text="Quote only")],
    )

    report = DeckQA().analyze(deck)

    assert any(issue.code == "incomplete_quote" for issue in report.issues)


def test_deck_qa_flags_dense_content():
    deck = DeckSpec(
        title="Deck",
        topic="Topic",
        slides=[SlideSpec(layout=SlideLayout.CONTENT, title="Dense", bullets=[f"Point {i}" for i in range(10)])],
    )
    report = DeckQA().analyze(deck)
    assert any(issue.code == "dense_content" for issue in report.issues)


def test_deck_qa_flags_incomplete_columns():
    deck = DeckSpec(
        title="Deck",
        topic="Topic",
        slides=[SlideSpec(layout=SlideLayout.TWO_COLUMN, title="Half", left_bullets=["A"], right_bullets=[])],
    )
    report = DeckQA().analyze(deck)
    assert any(issue.code == "incomplete_columns" for issue in report.issues)


def test_deck_qa_flags_incomplete_comparison():
    deck = DeckSpec(
        title="Deck",
        topic="Topic",
        slides=[SlideSpec(layout=SlideLayout.COMPARISON, title="Half", left_bullets=["A"], right_bullets=[])],
    )
    report = DeckQA().analyze(deck)
    assert any(issue.code == "incomplete_comparison" for issue in report.issues)


def test_deck_qa_flags_thin_statistics():
    deck = DeckSpec(
        title="Deck",
        topic="Topic",
        slides=[SlideSpec(layout=SlideLayout.STATISTICS, title="Stats", statistics=[StatisticData(value="1", label="Only one")])],
    )
    report = DeckQA().analyze(deck)
    assert any(issue.code == "thin_statistics" for issue in report.issues)


def test_chart_data_rejects_mismatched_lengths():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        ChartData(chart_type=ChartType.BAR, title="T", categories=["A", "B"], values=[1.0])


def test_deck_qa_flags_missing_chart():
    deck = DeckSpec(
        title="Deck",
        topic="Topic",
        slides=[SlideSpec(layout=SlideLayout.CHART, title="No Chart")],
    )
    report = DeckQA().analyze(deck)
    assert any(issue.code == "missing_chart" for issue in report.issues)


def test_deck_qa_flags_missing_image():
    deck = DeckSpec(
        title="Deck",
        topic="Topic",
        slides=[SlideSpec(layout=SlideLayout.IMAGE, title="No Img")],
    )
    report = DeckQA().analyze(deck)
    assert any(issue.code == "missing_image" for issue in report.issues)


def test_deck_qa_clean_deck_has_no_issues():
    deck = DeckSpec(
        title="Deck",
        topic="Topic",
        slides=[SlideSpec(layout=SlideLayout.CONTENT, title="Good", bullets=["A", "B", "C"])],
    )
    report = DeckQA().analyze(deck)
    assert not report.has_issues


def test_deck_qa_flags_empty_title_slide():
    deck = DeckSpec(
        title="Deck",
        topic="Topic",
        slides=[SlideSpec(layout=SlideLayout.TITLE, title="")],
    )
    report = DeckQA().analyze(deck)
    assert report.has_issues
    assert report.issues[0].code == "empty_title"


def test_deck_qa_flags_empty_section_slide():
    deck = DeckSpec(
        title="Deck",
        topic="Topic",
        slides=[SlideSpec(layout=SlideLayout.SECTION, title="   ")],
    )
    report = DeckQA().analyze(deck)
    assert report.has_issues
    assert report.issues[0].code == "empty_title"


def test_deck_qa_title_slide_with_valid_title_is_clean():
    deck = DeckSpec(
        title="Deck",
        topic="Topic",
        slides=[SlideSpec(layout=SlideLayout.TITLE, title="Welcome")],
    )
    report = DeckQA().analyze(deck)
    assert not report.has_issues


def test_deck_qa_flags_empty_citations():
    deck = DeckSpec(
        title="Deck",
        topic="Topic",
        slides=[SlideSpec(layout=SlideLayout.CITATIONS, title="References", citations=[])],
    )

    report = DeckQA().analyze(deck)

    assert any(issue.code == "empty_citations" for issue in report.issues)


def test_layout_selector_builds_quote_slide():
    slide = LayoutSelector().quote_slide(
        title="Founder's Principle",
        quote_text="Stay hungry, stay foolish.",
        quote_author="Steve Jobs",
        quote_context="Stanford, 2005",
    )

    assert slide.layout == SlideLayout.QUOTE
    assert slide.title == "Founder's Principle"
    assert slide.quote_author == "Steve Jobs"


def test_deck_qa_flags_empty_string_bullets():
    """Content slide with only empty-string bullets should be flagged."""
    deck = DeckSpec(
        title="Deck",
        topic="Topic",
        slides=[SlideSpec(layout=SlideLayout.CONTENT, title="Blank Bullets", bullets=["", "  ", ""])],
    )

    report = DeckQA().analyze(deck)
    assert any(issue.code == "empty_content" for issue in report.issues)


def test_deck_qa_passes_non_empty_bullets():
    """Content slide with real bullets should not be flagged as empty."""
    deck = DeckSpec(
        title="Deck",
        topic="Topic",
        slides=[SlideSpec(layout=SlideLayout.CONTENT, title="Valid", bullets=["Real point"])],
    )

    report = DeckQA().analyze(deck)
    assert not any(issue.code == "empty_content" for issue in report.issues)


def test_deck_qa_empty_deck_reports_issue():
    """An empty deck should be flagged as an issue."""
    deck = DeckSpec(title="Deck", topic="Topic", slides=[])
    report = DeckQA().analyze(deck)
    assert report.has_issues
    assert any(issue.code == "empty_deck" for issue in report.issues)


def test_deck_qa_flags_whitespace_only_left_column():
    """Two-column slide with whitespace-only left bullets should be flagged."""
    deck = DeckSpec(
        title="Deck",
        topic="Topic",
        slides=[
            SlideSpec(
                layout=SlideLayout.TWO_COLUMN,
                title="Bad Columns",
                left_bullets=["", "  "],
                right_bullets=["Real content"],
                left_title="Left",
                right_title="Right",
            )
        ],
    )
    report = DeckQA().analyze(deck)
    assert any(issue.code == "incomplete_columns" for issue in report.issues)


def test_deck_qa_flags_whitespace_only_comparison_right():
    """Comparison slide with whitespace-only right bullets should be flagged."""
    deck = DeckSpec(
        title="Deck",
        topic="Topic",
        slides=[
            SlideSpec(
                layout=SlideLayout.COMPARISON,
                title="Bad Comparison",
                left_bullets=["Real point"],
                right_bullets=["", " ", "\t"],
                left_title="A",
                right_title="B",
            )
        ],
    )
    report = DeckQA().analyze(deck)
    assert any(issue.code == "incomplete_comparison" for issue in report.issues)


def test_deck_qa_ignores_whitespace_bullets_for_dense_content():
    """A slide with 10 bullets where 8 are whitespace should NOT trigger dense_content."""
    deck = DeckSpec(
        title="Deck",
        topic="Topic",
        slides=[
            SlideSpec(
                layout=SlideLayout.CONTENT,
                title="Sparse",
                bullets=["Real one", "Real two", "", " ", "  ", "\t", "", " ", "", "  "],
            )
        ],
    )
    report = DeckQA().analyze(deck)
    assert not any(issue.code == "dense_content" for issue in report.issues)


def test_deck_qa_passes_real_column_bullets():
    """Two-column slide with real bullets should not be flagged."""
    deck = DeckSpec(
        title="Deck",
        topic="Topic",
        slides=[
            SlideSpec(
                layout=SlideLayout.TWO_COLUMN,
                title="Good Columns",
                left_bullets=["Point A"],
                right_bullets=["Point B"],
                left_title="Left",
                right_title="Right",
            )
        ],
    )
    report = DeckQA().analyze(deck)
    assert not any(issue.code == "incomplete_columns" for issue in report.issues)


def test_deck_qa_duplicate_empty_titles_flagged_as_empty():
    """Two slides with empty titles should each be flagged with empty_title,
    but NOT as duplicate_title (empty strings are skipped by the dedup logic)."""
    deck = DeckSpec(
        title="Deck",
        topic="Topic",
        slides=[
            SlideSpec(layout=SlideLayout.TITLE, title=""),
            SlideSpec(layout=SlideLayout.TITLE, title=""),
        ],
    )
    report = DeckQA().analyze(deck)
    assert report.has_issues
    empty_title_issues = [i for i in report.issues if i.code == "empty_title"]
    assert len(empty_title_issues) == 2
    # Empty titles are not tracked as duplicates
    assert not any(i.code == "duplicate_title" for i in report.issues)


def test_deck_qa_flags_dense_two_column():
    deck = DeckSpec(
        title="Deck",
        topic="Topic",
        slides=[
            SlideSpec(
                layout=SlideLayout.TWO_COLUMN,
                title="Dense Columns",
                left_bullets=[f"Left point {i}" for i in range(7)],
                right_bullets=["Right point 1", "Right point 2"],
                left_title="Left",
                right_title="Right",
            )
        ],
    )
    report = DeckQA().analyze(deck)
    assert any(issue.code == "dense_columns" for issue in report.issues)


def test_deck_qa_passes_normal_two_column():
    deck = DeckSpec(
        title="Deck",
        topic="Topic",
        slides=[
            SlideSpec(
                layout=SlideLayout.TWO_COLUMN,
                title="Normal Columns",
                left_bullets=["L1", "L2", "L3"],
                right_bullets=["R1", "R2", "R3"],
                left_title="Left",
                right_title="Right",
            )
        ],
    )
    report = DeckQA().analyze(deck)
    assert not any(issue.code == "dense_columns" for issue in report.issues)


def test_deck_qa_flags_dense_comparison():
    deck = DeckSpec(
        title="Deck",
        topic="Topic",
        slides=[
            SlideSpec(
                layout=SlideLayout.COMPARISON,
                title="Dense Compare",
                left_bullets=["L1", "L2"],
                right_bullets=[f"Right point {i}" for i in range(8)],
                left_title="Option A",
                right_title="Option B",
            )
        ],
    )
    report = DeckQA().analyze(deck)
    assert any(issue.code == "dense_comparison" for issue in report.issues)


def test_deck_qa_passes_normal_comparison():
    deck = DeckSpec(
        title="Deck",
        topic="Topic",
        slides=[
            SlideSpec(
                layout=SlideLayout.COMPARISON,
                title="Normal Compare",
                left_bullets=["L1", "L2", "L3"],
                right_bullets=["R1", "R2", "R3"],
                left_title="Option A",
                right_title="Option B",
            )
        ],
    )
    report = DeckQA().analyze(deck)
    assert not any(issue.code == "dense_comparison" for issue in report.issues)
