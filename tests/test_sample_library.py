import tempfile

from pptx import Presentation
from PIL import Image

from autoppt.sample_library import (
    build_sample_deck,
    get_sample_definitions,
    render_readme_showcase_previews,
    render_sample,
)


def test_sample_library_builds_all_defined_decks():
    definitions = get_sample_definitions()

    assert len(definitions) >= 11
    for definition in definitions:
        with tempfile.TemporaryDirectory(prefix="test-sample-") as asset_dir:
            deck = build_sample_deck(definition.sample_id, asset_dir=asset_dir)
            assert deck.title
            assert deck.style == definition.style
            assert deck.language == definition.language
            assert len(deck.slides) >= 6


def test_sample_library_renders_sample_pptx(tmp_path):
    output_path = render_sample("en_visual_showcase", tmp_path)

    assert output_path.exists()
    presentation = Presentation(str(output_path))
    assert len(presentation.slides) >= 6


def test_sample_library_renders_readme_previews(tmp_path):
    outputs = render_readme_showcase_previews(tmp_path)

    assert len(outputs) == 2
    for output in outputs:
        assert output.exists()
        assert output.stat().st_size > 0


def test_sample_library_renders_readme_previews_with_real_preview_path(tmp_path, monkeypatch):
    preview_source = tmp_path / "slide-1.jpg"
    Image.new("RGB", (1200, 675), color=(24, 42, 88)).save(preview_source)

    def fake_check_dependencies():
        return True, []

    def fake_render_sample(sample_id, output_dir):
        output = output_dir / f"{sample_id}.pptx"
        output.write_text("fake")
        return output

    def fake_convert_to_pdf(pptx_path, output_dir):
        pdf_path = output_dir / f"{pptx_path.stem}.pdf"
        pdf_path.write_text("fake")
        return pdf_path

    def fake_convert_pdf_to_images(pdf_path, output_dir):
        return [preview_source]

    monkeypatch.setattr("autoppt.sample_library.check_dependencies", fake_check_dependencies)
    monkeypatch.setattr("autoppt.sample_library.render_sample", fake_render_sample)
    monkeypatch.setattr("autoppt.sample_library.convert_to_pdf", fake_convert_to_pdf)
    monkeypatch.setattr("autoppt.sample_library.convert_pdf_to_images", fake_convert_pdf_to_images)

    outputs = render_readme_showcase_previews(tmp_path)
    assert len(outputs) == 2
    assert all(path.exists() for path in outputs)
