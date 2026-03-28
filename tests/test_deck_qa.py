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
    with pytest.raises(Exception):
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
