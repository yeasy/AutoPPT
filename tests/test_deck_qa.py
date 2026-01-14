from autoppt.data_types import DeckSpec, SlideLayout, SlideSpec
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
