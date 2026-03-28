from unittest.mock import patch

import pytest
from pptx import Presentation

from autoppt.data_types import DeckSpec, PresentationOutline, PresentationSection, SlideConfig, SlideLayout, SlidePlan, SlideSpec, SlideType
from autoppt.generator import Generator
from autoppt.llm_provider import MockProvider


@pytest.fixture
def mock_generator():
    with patch("autoppt.generator.Researcher"), patch("autoppt.generator.PPTRenderer"):
        yield Generator(provider_name="mock")


def test_generator_init():
    gen = Generator(provider_name="mock")
    assert isinstance(gen.llm, MockProvider)
    assert gen.provider_name == "mock"


def test_create_outline(mock_generator):
    outline = mock_generator._create_outline("AI Future", 5, "English")
    assert isinstance(outline, PresentationOutline)
    assert len(outline.sections) > 0


@patch("autoppt.generator.PPTRenderer")
@patch("autoppt.generator.Researcher")
def test_generate_flow(mock_researcher_cls, mock_renderer_cls, tmp_path):
    output_file = str(tmp_path / "test_gen.pptx")
    mock_researcher = mock_researcher_cls.return_value
    mock_researcher.gather_context.return_value = "Mock context"
    mock_researcher.search_images.return_value = []
    mock_renderer_cls.return_value.save.side_effect = lambda path: tmp_path.joinpath("test_gen.pptx").write_bytes(b"ppt")

    gen = Generator(provider_name="mock")
    result = gen.generate(topic="Test Topic", slides_count=3, output_file=output_file)

    assert result == output_file
    assert mock_researcher.gather_context.call_count > 0
    mock_renderer_cls.return_value.render_deck.assert_called_once()
    mock_renderer_cls.return_value.apply_style.assert_called()


def test_create_slide_content(mock_generator):
    plan = SlidePlan(
        title="Slide Title",
        section_title="Overview",
        topic="Test Topic",
        language="English",
        slide_type=SlideType.CONTENT,
    )
    config = mock_generator._create_slide_content("Slide Title", "Context context", "minimalist", "English", "Test Topic", plan)
    assert isinstance(config, SlideConfig)
    assert config.title
    assert len(config.bullets) > 0


@patch("autoppt.generator.generate_thumbnails")
@patch("autoppt.generator.PPTRenderer")
@patch("autoppt.generator.Researcher")
def test_generate_with_thumbnails(mock_research, mock_renderer, mock_thumb, tmp_path):
    output_file = str(tmp_path / "thumb_test.pptx")
    mock_renderer.return_value.save.side_effect = lambda path: tmp_path.joinpath("thumb_test.pptx").write_bytes(b"ppt")

    gen = Generator(provider_name="mock")

    with patch.object(gen, "_create_outline") as mock_outline:
        mock_outline.return_value = PresentationOutline(
            title="Test",
            sections=[PresentationSection(title="S1", slides=["Slide 1"])],
        )

        with patch.object(gen, "_create_slide_content") as mock_content:
            mock_content.return_value = SlideConfig(
                title="Slide 1",
                bullets=["Point 1"],
                slide_type=SlideType.CONTENT,
                citations=[],
            )

            gen.generate(
                topic="Thumbnails",
                output_file=output_file,
                slides_count=3,
                create_thumbnails=True,
            )

    mock_thumb.assert_called_once()


@patch("autoppt.generator.PPTRenderer")
@patch("autoppt.generator.Researcher")
def test_generate_from_outline_shares_pipeline(mock_researcher_cls, mock_renderer_cls, tmp_path):
    output_file = str(tmp_path / "outline_gen.pptx")
    mock_researcher = mock_researcher_cls.return_value
    mock_researcher.gather_context.return_value = "Mock context"
    mock_researcher.search_images.return_value = []
    mock_renderer_cls.return_value.save.side_effect = lambda path: tmp_path.joinpath("outline_gen.pptx").write_bytes(b"ppt")

    gen = Generator(provider_name="mock")
    outline = PresentationOutline(
        title="Outline",
        sections=[PresentationSection(title="Section", slides=["Slide 1"])],
    )

    result = gen.generate_from_outline(outline, "Outline Topic", output_file=output_file)

    assert result == output_file
    mock_researcher.gather_context.assert_called_once()


def test_generate_smoke_creates_openable_ppt(tmp_path):
    output_file = tmp_path / "smoke.pptx"
    gen = Generator(provider_name="mock")

    with patch.object(gen, "_create_outline") as mock_outline, patch.object(gen, "_create_slide_content") as mock_content:
        mock_outline.return_value = PresentationOutline(
            title="Smoke Deck",
            sections=[PresentationSection(title="Overview", slides=["Key Slide"])],
        )
        mock_content.return_value = SlideConfig(
            title="Key Slide",
            bullets=["First point", "Second point", "Third point"],
            slide_type=SlideType.CONTENT,
            citations=[],
        )
        with patch.object(gen.researcher, "gather_context", return_value="Mock context"), patch.object(
            gen.researcher, "search_images", return_value=[]
        ):
            result = gen.generate(topic="Smoke Topic", slides_count=1, output_file=str(output_file))

    assert result == str(output_file)
    assert output_file.exists()
    assert output_file.stat().st_size > 0

    presentation = Presentation(str(output_file))
    assert len(presentation.slides) >= 3


def test_generate_collects_quality_report(tmp_path):
    output_file = tmp_path / "qa_smoke.pptx"
    gen = Generator(provider_name="mock")

    with patch.object(gen, "_create_outline") as mock_outline, patch.object(gen, "_create_slide_content") as mock_content:
        mock_outline.return_value = PresentationOutline(
            title="QA Deck",
            sections=[PresentationSection(title="Overview", slides=["Problem Slide"])],
        )
        mock_content.return_value = SlideConfig(
            title="Problem Slide",
            bullets=[],
            slide_type=SlideType.CONTENT,
            citations=[],
        )
        with patch.object(gen.researcher, "gather_context", return_value="Mock context"), patch.object(
            gen.researcher, "search_images", return_value=[]
        ):
            gen.generate(topic="QA Topic", slides_count=1, output_file=str(output_file))

    assert gen.last_quality_report.has_issues


def test_generate_quote_slide_from_config(tmp_path):
    output_file = tmp_path / "quote.pptx"
    gen = Generator(provider_name="mock")

    with patch.object(gen, "_create_outline") as mock_outline, patch.object(gen, "_create_slide_content") as mock_content:
        mock_outline.return_value = PresentationOutline(
            title="Quote Deck",
            sections=[PresentationSection(title="Overview", slides=["Quote Slide"])],
        )
        mock_content.return_value = SlideConfig(
            title="Quote Slide",
            bullets=[],
            slide_type=SlideType.QUOTE,
            quote_text="Execution beats intention.",
            quote_author="AutoPPT",
            quote_context="Mock source",
            citations=[],
        )
        with patch.object(gen.researcher, "gather_context", return_value="Mock context"), patch.object(
            gen.researcher, "search_images", return_value=[]
        ):
            gen.generate(topic="Quote Topic", slides_count=1, output_file=str(output_file))

    assert output_file.exists()


def test_build_deck_spec_tracks_metadata_and_rich_layouts(tmp_path):
    gen = Generator(provider_name="mock")
    outline = PresentationOutline(
        title="Deck",
        sections=[PresentationSection(title="Strategy", slides=["Current vs Future"])],
    )

    with patch.object(gen, "_plan_slide") as mock_plan, patch.object(gen, "_build_slide") as mock_build:
        mock_plan.return_value = SlidePlan(
            title="Current vs Future",
            section_title="Strategy",
            topic="Transformation",
            language="English",
            slide_type=SlideType.COMPARISON,
            left_title="Current",
            right_title="Future",
        )
        mock_build.return_value = SlideConfig(
            title="Current vs Future",
            bullets=[],
            slide_type=SlideType.COMPARISON,
            left_title="Current",
            right_title="Future",
            left_bullets=["Legacy process"],
            right_bullets=["Automated workflow"],
            citations=["https://example.com/compare"],
        )
        deck_spec = gen.build_deck_spec(outline, topic="Transformation", style="technology", language="English")

    assert deck_spec.style == "technology"
    assert deck_spec.language == "English"
    comparison_slide = next(slide for slide in deck_spec.slides if slide.title == "Current vs Future")
    assert comparison_slide.layout.value == "comparison"
    assert comparison_slide.plan is not None
    assert comparison_slide.source_config is not None


def test_remix_slide_updates_selected_slide():
    gen = Generator(provider_name="mock")
    outline = PresentationOutline(
        title="Deck",
        sections=[PresentationSection(title="Strategy", slides=["Execution Priorities"])],
    )

    with patch.object(gen, "_plan_slide") as mock_plan, patch.object(gen, "_build_slide") as mock_build:
        mock_plan.return_value = SlidePlan(
            title="Execution Priorities",
            section_title="Strategy",
            topic="Transformation",
            language="English",
            slide_type=SlideType.CONTENT,
        )
        mock_build.return_value = SlideConfig(
            title="Execution Priorities",
            bullets=["Initial point", "Next point"],
            slide_type=SlideType.CONTENT,
            citations=[],
        )
        deck_spec = gen.build_deck_spec(outline, topic="Transformation", style="minimalist", language="English")

    target_index = next(index for index, slide in enumerate(deck_spec.slides) if slide.title == "Execution Priorities")

    with patch.object(gen, "_plan_slide") as remix_plan, patch.object(gen, "_build_slide") as remix_build:
        remix_plan.return_value = SlidePlan(
            title="Execution Priorities",
            section_title="Strategy",
            topic="Transformation",
            language="English",
            slide_type=SlideType.TWO_COLUMN,
            left_title="Now",
            right_title="Next",
        )
        remix_build.return_value = SlideConfig(
            title="Execution Priorities",
            bullets=["Current process", "Manual QA", "Automation", "Release velocity"],
            slide_type=SlideType.TWO_COLUMN,
            left_title="Now",
            right_title="Next",
            left_bullets=["Current process", "Manual QA"],
            right_bullets=["Automation", "Release velocity"],
            citations=["https://example.com/remix"],
        )
        remixed_deck = gen.remix_slide(deck_spec, target_index, instruction="Turn this into a clearer two-column slide.")

    remixed_slide = remixed_deck.slides[target_index]
    assert remixed_slide.layout.value == "two_column"
    assert remixed_slide.left_title == "Now"
    assert remixed_slide.citations == ["https://example.com/remix"]


@patch("autoppt.generator.PPTRenderer")
@patch("autoppt.generator.Researcher")
def test_save_deck_materializes_citations_for_render(mock_researcher_cls, mock_renderer_cls, tmp_path):
    output_file = str(tmp_path / "rendered.pptx")
    mock_renderer_cls.return_value.save.side_effect = lambda path: tmp_path.joinpath("rendered.pptx").write_bytes(b"ppt")

    gen = Generator(provider_name="mock")
    outline = PresentationOutline(
        title="Deck",
        sections=[PresentationSection(title="Strategy", slides=["Execution Priorities"])],
    )
    with patch.object(gen, "_plan_slide") as mock_plan, patch.object(gen, "_build_slide") as mock_build:
        mock_plan.return_value = SlidePlan(
            title="Execution Priorities",
            section_title="Strategy",
            topic="Transformation",
            language="English",
            slide_type=SlideType.CONTENT,
        )
        mock_build.return_value = SlideConfig(
            title="Execution Priorities",
            bullets=["Initial point", "Next point"],
            slide_type=SlideType.CONTENT,
            citations=["https://example.com/source"],
        )
        deck_spec = gen.build_deck_spec(outline, topic="Transformation", style="minimalist", language="English")

    gen.save_deck(deck_spec, output_file)

    render_deck = mock_renderer_cls.return_value.render_deck.call_args.args[0]
    assert any(slide.layout.value == "citations" for slide in render_deck.slides)


def test_regenerate_slide_preserves_editable_metadata():
    gen = Generator(provider_name="mock")
    outline = PresentationOutline(
        title="Deck",
        sections=[PresentationSection(title="Strategy", slides=["Execution Priorities"])],
    )

    with patch.object(gen, "_plan_slide") as mock_plan, patch.object(gen, "_build_slide") as mock_build:
        mock_plan.return_value = SlidePlan(
            title="Execution Priorities",
            section_title="Strategy",
            topic="Transformation",
            language="English",
            slide_type=SlideType.CONTENT,
        )
        mock_build.return_value = SlideConfig(
            title="Execution Priorities",
            bullets=["Initial point", "Next point"],
            slide_type=SlideType.CONTENT,
            citations=[],
        )
        deck_spec = gen.build_deck_spec(outline, topic="Transformation", style="minimalist", language="English")

    target_index = next(index for index, slide in enumerate(deck_spec.slides) if slide.title == "Execution Priorities")

    with patch.object(gen, "_plan_slide") as regen_plan, patch.object(gen, "_build_slide") as regen_build:
        regen_plan.return_value = SlidePlan(
            title="Execution Priorities",
            section_title="Strategy",
            topic="Transformation",
            language="English",
            slide_type=SlideType.COMPARISON,
            left_title="Now",
            right_title="Next",
        )
        regen_build.return_value = SlideConfig(
            title="Execution Priorities",
            bullets=[],
            slide_type=SlideType.COMPARISON,
            left_title="Now",
            right_title="Next",
            left_bullets=["Current process", "Manual QA"],
            right_bullets=["Automation", "Release velocity"],
            citations=["https://example.com/regenerated"],
        )
        regenerated_deck = gen.regenerate_slide(deck_spec, target_index, target_layout=SlideType.COMPARISON)

    regenerated_slide = regenerated_deck.slides[target_index]
    assert regenerated_slide.editable is True
    assert regenerated_slide.layout.value == "comparison"
    assert regenerated_slide.source_title == "Execution Priorities"
    assert regenerated_slide.citations == ["https://example.com/regenerated"]


def test_generator_double_close_is_safe():
    gen = Generator(provider_name="mock")
    gen.close()
    gen.close()  # second close must not raise
    assert gen.assets_dir == ""
    assert gen._assets_tmpdir is None


def test_generator_context_manager_double_close_is_safe():
    with Generator(provider_name="mock") as gen:
        gen.close()
    # __exit__ calls close() again - must not raise
    assert gen.assets_dir == ""


def test_update_slide_out_of_range_raises():
    gen = Generator(provider_name="mock")
    deck_spec = DeckSpec(title="D", topic="T", slides=[])
    with pytest.raises(IndexError, match="out of range"):
        gen.regenerate_slide(deck_spec, 0)


def test_update_slide_non_editable_raises():
    gen = Generator(provider_name="mock")
    deck_spec = DeckSpec(
        title="D", topic="T",
        slides=[SlideSpec(layout=SlideLayout.TITLE, title="Title", editable=False)],
    )
    with pytest.raises(ValueError, match="content slides"):
        gen.regenerate_slide(deck_spec, 0)


def test_coerce_slide_type_rejects_structural_layouts():
    gen = Generator(provider_name="mock")
    with pytest.raises(ValueError, match="cannot be used"):
        gen._coerce_slide_type(SlideLayout.TITLE)


def test_save_and_load_deck_spec_round_trip(tmp_path):
    gen = Generator(provider_name="mock")
    deck_spec = DeckSpec(title="Round Trip", topic="AI", style="corporate", language="English", slides=[])
    output_path = tmp_path / "deck_spec.json"

    gen.save_deck_spec(deck_spec, str(output_path))
    loaded = gen.load_deck_spec(str(output_path))

    assert output_path.exists()
    assert loaded.title == "Round Trip"
    assert loaded.style == "corporate"


def test_sanitize_prompt_field_truncates_long_input():
    from autoppt.generator import _sanitize_prompt_field, _MAX_PROMPT_FIELD_LEN

    long_input = "A" * 1000
    result = _sanitize_prompt_field(long_input)
    assert len(result) == _MAX_PROMPT_FIELD_LEN


def test_sanitize_prompt_field_strips_null_bytes():
    from autoppt.generator import _sanitize_prompt_field

    result = _sanitize_prompt_field("hello\x00world")
    assert "\x00" not in result
    assert result == "helloworld"


def test_sanitize_prompt_field_strips_control_characters():
    from autoppt.generator import _sanitize_prompt_field

    result = _sanitize_prompt_field("hello\x01\x08\x0b\x7fworld")
    assert result == "helloworld"


def test_sanitize_prompt_field_preserves_newlines_and_tabs():
    from autoppt.generator import _sanitize_prompt_field

    result = _sanitize_prompt_field("hello\n\tworld")
    assert result == "hello\n\tworld"
