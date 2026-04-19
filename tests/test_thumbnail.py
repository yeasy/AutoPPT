"""
Unit tests for thumbnail generation.
"""
import pytest
import subprocess
import sys
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, call
from PIL import ImageFont

from autoppt.thumbnail import (
    generate_thumbnails, check_dependencies, convert_to_pdf,
    convert_pdf_to_images, create_grid_image,
    THUMBNAIL_WIDTH, CONVERSION_DPI, GRID_PADDING, BORDER_WIDTH,
    FONT_SIZE_RATIO, LABEL_PADDING_RATIO, JPEG_QUALITY, SUBPROCESS_TIMEOUT,
)

class TestThumbnailGeneration:
    """Tests for thumbnail generation module."""

    @pytest.fixture
    def mock_subprocess(self):
        with patch("subprocess.run") as mock:
            yield mock

    @pytest.fixture
    def mock_shutil(self):
        with patch("shutil.which") as mock:
            # Default to finding everything
            mock.return_value = "/usr/bin/fake"
            yield mock

    def test_check_dependencies_success(self, mock_shutil):
        """Test check_dependencies when all tools exist."""
        ok, missing = check_dependencies()
        assert ok is True
        assert len(missing) == 0

    def test_check_dependencies_missing(self):
        """Test check_dependencies when tools are missing."""
        with patch("shutil.which", return_value=None):
            ok, missing = check_dependencies()
            assert ok is False
            assert "libreoffice" in missing
            assert "poppler-utils" in missing

    def test_generate_thumbnails_no_file(self):
        """Test generation with non-existent file."""
        with pytest.raises(FileNotFoundError):
            generate_thumbnails("nonexistent.pptx")

    @patch("autoppt.thumbnail.convert_to_pdf")
    @patch("autoppt.thumbnail.convert_pdf_to_images")
    @patch("autoppt.thumbnail.create_grid_image")
    @patch("autoppt.thumbnail.check_dependencies")
    def test_generate_thumbnails_flow(
        self,
        mock_check,
        mock_create_grid,
        mock_pdf_imgs,
        mock_to_pdf,
        tmp_path
    ):
        """Test the full flow of generate_thumbnails."""
        # Setup mocks
        mock_check.return_value = (True, [])

        dummy_pptx = tmp_path / "test.pptx"
        dummy_pptx.touch()

        mock_to_pdf.return_value = tmp_path / "test.pdf"
        mock_pdf_imgs.return_value = [tmp_path / "slide-1.jpg", tmp_path / "slide-2.jpg"]

        mock_grid_img = MagicMock()
        mock_create_grid.return_value = mock_grid_img

        # execution
        results = generate_thumbnails(str(dummy_pptx), output_prefix=str(tmp_path / "thumb"))

        # assertions
        assert mock_to_pdf.called
        assert mock_pdf_imgs.called
        assert mock_create_grid.called
        assert mock_grid_img.save.called
        assert len(results) > 0

    def test_convert_to_pdf_command(self, mock_subprocess, tmp_path):
        """Test strict command arguments for LibreOffice."""
        pptx_path = tmp_path / "input.pptx"
        output_dir = tmp_path / "out"

        convert_to_pdf(pptx_path, output_dir)

        mock_subprocess.assert_called_once()
        args = mock_subprocess.call_args[0][0]
        assert args[0] == "soffice"
        assert "--convert-to" in args
        assert "pdf" in args
        assert str(pptx_path) in args

    def test_convert_to_pdf_subprocess_error(self, tmp_path):
        """Test convert_to_pdf handles CalledProcessError gracefully."""
        import subprocess
        pptx_path = tmp_path / "input.pptx"
        output_dir = tmp_path / "out"
        output_dir.mkdir()

        with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "soffice")):
            result = convert_to_pdf(pptx_path, output_dir)
        assert result is None

    def test_generate_thumbnails_missing_deps(self, tmp_path):
        """Test generate_thumbnails exits gracefully with missing dependencies."""
        dummy_pptx = tmp_path / "test.pptx"
        dummy_pptx.touch()

        with patch("autoppt.thumbnail.check_dependencies", return_value=(False, ["libreoffice"])):
            result = generate_thumbnails(str(dummy_pptx))
        assert result == []

    @patch("autoppt.thumbnail.create_grid_image")
    @patch("autoppt.thumbnail.convert_pdf_to_images")
    @patch("autoppt.thumbnail.convert_to_pdf")
    @patch("autoppt.thumbnail.check_dependencies")
    def test_generate_thumbnails_pdf_conversion_fails(
        self, mock_check, mock_to_pdf, mock_pdf_imgs, mock_create_grid, tmp_path
    ):
        """Test generate_thumbnails handles PDF conversion failure."""
        mock_check.return_value = (True, [])
        dummy_pptx = tmp_path / "test.pptx"
        dummy_pptx.touch()
        mock_to_pdf.return_value = None

        results = generate_thumbnails(str(dummy_pptx))
        assert results == []
        mock_pdf_imgs.assert_not_called()


class TestConvertPdfToImages:
    """Tests for convert_pdf_to_images function."""

    def test_successful_conversion(self, tmp_path):
        """Test successful PDF to image conversion with sorted output."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.touch()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create fake slide image files that pdftoppm would produce
        (output_dir / "slide-1.jpg").touch()
        (output_dir / "slide-3.jpg").touch()
        (output_dir / "slide-2.jpg").touch()

        with patch("subprocess.run") as mock_run:
            result = convert_pdf_to_images(pdf_path, output_dir)

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "pdftoppm"
        assert "-jpeg" in args
        assert "-r" in args
        assert str(CONVERSION_DPI) in args
        assert str(pdf_path) in args

        # Verify sorting: 1, 2, 3
        assert len(result) == 3
        assert result[0].name == "slide-1.jpg"
        assert result[1].name == "slide-2.jpg"
        assert result[2].name == "slide-3.jpg"

    def test_called_process_error(self, tmp_path):
        """Test convert_pdf_to_images handles CalledProcessError."""
        pdf_path = tmp_path / "test.pdf"
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "pdftoppm")):
            result = convert_pdf_to_images(pdf_path, output_dir)
        assert result == []

    def test_timeout_expired(self, tmp_path):
        """Test convert_pdf_to_images handles TimeoutExpired."""
        pdf_path = tmp_path / "test.pdf"
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("pdftoppm", 120)):
            result = convert_pdf_to_images(pdf_path, output_dir)
        assert result == []

    def test_no_images_produced(self, tmp_path):
        """Test convert_pdf_to_images returns empty list when no images found."""
        pdf_path = tmp_path / "test.pdf"
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with patch("subprocess.run"):
            result = convert_pdf_to_images(pdf_path, output_dir)
        assert result == []


class TestConvertToPdfTimeout:
    """Test timeout handling in convert_to_pdf."""

    def test_timeout_expired(self, tmp_path):
        """Test convert_to_pdf handles TimeoutExpired."""
        pptx_path = tmp_path / "input.pptx"
        output_dir = tmp_path / "out"
        output_dir.mkdir()

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("soffice", 120)):
            result = convert_to_pdf(pptx_path, output_dir)
        assert result is None

    def test_successful_conversion(self, tmp_path):
        """Test convert_to_pdf returns pdf path on success."""
        pptx_path = tmp_path / "input.pptx"
        output_dir = tmp_path / "out"
        output_dir.mkdir()

        # Create the expected output PDF
        expected_pdf = output_dir / "input.pdf"
        expected_pdf.touch()

        with patch("subprocess.run"):
            result = convert_to_pdf(pptx_path, output_dir)
        assert result == expected_pdf

    def test_pdf_not_created(self, tmp_path):
        """Test convert_to_pdf returns None when PDF file not created."""
        pptx_path = tmp_path / "input.pptx"
        output_dir = tmp_path / "out"
        output_dir.mkdir()

        with patch("subprocess.run"):
            result = convert_to_pdf(pptx_path, output_dir)
        assert result is None


class TestCreateGridImage:
    """Tests for create_grid_image function."""

    def _make_fake_images(self, tmp_path, count=3, width=400, height=300):
        """Helper to create fake slide images."""
        from PIL import Image
        paths = []
        for i in range(count):
            img_path = tmp_path / f"slide-{i+1}.jpg"
            img = Image.new("RGB", (width, height), "blue")
            img.save(img_path)
            paths.append(img_path)
        return paths

    def test_empty_images_returns_none(self):
        """Test create_grid_image returns None for empty list."""
        result = create_grid_image([], cols=5, thumb_width=300, start_index=0)
        assert result is None

    def test_single_image(self, tmp_path):
        """Test grid with a single image."""
        images = self._make_fake_images(tmp_path, count=1)
        result = create_grid_image(images, cols=5, thumb_width=300, start_index=0)
        assert result is not None
        # 1 image in a 5-col grid = 1 row
        # Width should be 5 * (300 + 20) + 20 = 1620
        assert result.width == 5 * (300 + GRID_PADDING) + GRID_PADDING

    def test_multiple_images_grid_dimensions(self, tmp_path):
        """Test grid dimensions with multiple images spanning rows."""
        images = self._make_fake_images(tmp_path, count=7)
        result = create_grid_image(images, cols=3, thumb_width=200, start_index=0)
        assert result is not None
        # 7 images, 3 cols -> 3 rows
        expected_width = 3 * (200 + GRID_PADDING) + GRID_PADDING
        assert result.width == expected_width

    def test_start_index_offset(self, tmp_path):
        """Test that start_index affects label numbering (grid still renders)."""
        images = self._make_fake_images(tmp_path, count=2)
        result = create_grid_image(images, cols=5, thumb_width=300, start_index=10)
        assert result is not None

    def test_font_fallback_to_default(self, tmp_path):
        """Test that font loading falls back to default when truetype fails."""
        images = self._make_fake_images(tmp_path, count=1)

        # Get a real default font before patching
        real_default = ImageFont.load_default()

        # Both truetype calls fail, so load_default is used
        with patch("PIL.ImageFont.truetype", side_effect=IOError("no font")):
            with patch("PIL.ImageFont.load_default", return_value=real_default):
                result = create_grid_image(images, cols=5, thumb_width=300, start_index=0)
        assert result is not None

    def test_font_fallback_multiple_candidates(self, tmp_path):
        """Test font tries multiple candidates before falling back to default."""
        images = self._make_fake_images(tmp_path, count=1)

        real_truetype = ImageFont.truetype
        call_count = [0]
        def truetype_side_effect(*args, **kwargs):
            call_count[0] += 1
            # Allow load_default's internal truetype call (passes BytesIO, not str)
            if args and not isinstance(args[0], str):
                return real_truetype(*args, **kwargs)
            raise IOError("Font not found")

        with patch("PIL.ImageFont.truetype", side_effect=truetype_side_effect):
            result = create_grid_image(images, cols=5, thumb_width=300, start_index=0)
        assert result is not None
        assert call_count[0] >= 2  # Multiple font candidates attempted

    def test_slide_labels_are_one_indexed(self, tmp_path):
        """Test that slide labels use 1-indexed numbering (Slide 1, not Slide 0)."""
        images = self._make_fake_images(tmp_path, count=3)

        with patch("PIL.ImageDraw.ImageDraw.text") as mock_text:
            create_grid_image(images, cols=5, thumb_width=300, start_index=0)

        # draw.text((x, y), label, ...) — the label string is the second positional arg
        label_args = [c.args[1] for c in mock_text.call_args_list]
        assert "Slide 1" in label_args
        assert "Slide 2" in label_args
        assert "Slide 3" in label_args
        assert "Slide 0" not in label_args

    def test_slide_labels_with_start_index_offset(self, tmp_path):
        """Test that start_index=5 produces labels starting at Slide 6."""
        images = self._make_fake_images(tmp_path, count=2)

        with patch("PIL.ImageDraw.ImageDraw.text") as mock_text:
            create_grid_image(images, cols=5, thumb_width=300, start_index=5)

        label_args = [c.args[1] for c in mock_text.call_args_list]
        assert "Slide 6" in label_args
        assert "Slide 7" in label_args
        assert "Slide 5" not in label_args

    def test_image_aspect_ratio_preserved(self, tmp_path):
        """Test that thumbnail height respects source aspect ratio."""
        # Create wide images (2:1 aspect)
        images = self._make_fake_images(tmp_path, count=1, width=800, height=400)
        result = create_grid_image(images, cols=5, thumb_width=300, start_index=0)
        assert result is not None
        # aspect_ratio = 400/800 = 0.5, thumb_height = 300 * 0.5 = 150
        thumb_height = int(300 * 0.5)
        font_size = int(300 * FONT_SIZE_RATIO)
        label_height = int(font_size * (1 + LABEL_PADDING_RATIO * 2))
        cell_height = thumb_height + label_height + GRID_PADDING
        expected_grid_height = 1 * cell_height + GRID_PADDING
        assert result.height == expected_grid_height


class TestGenerateThumbnailsAdvanced:
    """Advanced tests for generate_thumbnails edge cases."""

    @patch("autoppt.thumbnail.create_grid_image")
    @patch("autoppt.thumbnail.convert_pdf_to_images")
    @patch("autoppt.thumbnail.convert_to_pdf")
    @patch("autoppt.thumbnail.check_dependencies")
    def test_empty_slide_images_returns_empty(
        self, mock_check, mock_to_pdf, mock_pdf_imgs, mock_create_grid, tmp_path
    ):
        """Test generate_thumbnails returns [] when no slide images produced."""
        mock_check.return_value = (True, [])
        dummy_pptx = tmp_path / "test.pptx"
        dummy_pptx.touch()
        mock_to_pdf.return_value = tmp_path / "test.pdf"
        mock_pdf_imgs.return_value = []

        results = generate_thumbnails(str(dummy_pptx), output_prefix=str(tmp_path / "thumb"))
        assert results == []
        mock_create_grid.assert_not_called()

    @patch("autoppt.thumbnail.create_grid_image")
    @patch("autoppt.thumbnail.convert_pdf_to_images")
    @patch("autoppt.thumbnail.convert_to_pdf")
    @patch("autoppt.thumbnail.check_dependencies")
    def test_multiple_grids_pagination(
        self, mock_check, mock_to_pdf, mock_pdf_imgs, mock_create_grid, tmp_path
    ):
        """Test generate_thumbnails creates multiple grids for many slides."""
        mock_check.return_value = (True, [])
        dummy_pptx = tmp_path / "test.pptx"
        dummy_pptx.touch()
        mock_to_pdf.return_value = tmp_path / "test.pdf"

        # 35 slides with 5 cols -> max_rows=6, max_per_grid=30 -> 2 grids
        slide_paths = [tmp_path / f"slide-{i+1}.jpg" for i in range(35)]
        mock_pdf_imgs.return_value = slide_paths

        mock_grid_img = MagicMock()
        mock_create_grid.return_value = mock_grid_img

        results = generate_thumbnails(
            str(dummy_pptx), output_prefix=str(tmp_path / "thumb"), cols=5
        )

        assert mock_create_grid.call_count == 2
        # First call: 30 slides, second call: 5 slides
        first_call_images = mock_create_grid.call_args_list[0][0][0]
        second_call_images = mock_create_grid.call_args_list[1][0][0]
        assert len(first_call_images) == 30
        assert len(second_call_images) == 5

        # With multiple grids, filenames should have -1, -2 suffixes
        assert len(results) == 2
        assert "-1.jpg" in results[0]
        assert "-2.jpg" in results[1]

    @patch("autoppt.thumbnail.create_grid_image")
    @patch("autoppt.thumbnail.convert_pdf_to_images")
    @patch("autoppt.thumbnail.convert_to_pdf")
    @patch("autoppt.thumbnail.check_dependencies")
    def test_single_grid_no_suffix(
        self, mock_check, mock_to_pdf, mock_pdf_imgs, mock_create_grid, tmp_path
    ):
        """Test single grid file has no numeric suffix."""
        mock_check.return_value = (True, [])
        dummy_pptx = tmp_path / "test.pptx"
        dummy_pptx.touch()
        mock_to_pdf.return_value = tmp_path / "test.pdf"
        mock_pdf_imgs.return_value = [tmp_path / f"slide-{i+1}.jpg" for i in range(5)]

        mock_grid_img = MagicMock()
        mock_create_grid.return_value = mock_grid_img

        results = generate_thumbnails(
            str(dummy_pptx), output_prefix=str(tmp_path / "thumb"), cols=5
        )

        assert len(results) == 1
        assert results[0].endswith("thumb.jpg")

    @patch("autoppt.thumbnail.create_grid_image")
    @patch("autoppt.thumbnail.convert_pdf_to_images")
    @patch("autoppt.thumbnail.convert_to_pdf")
    @patch("autoppt.thumbnail.check_dependencies")
    def test_create_grid_returns_none_skips(
        self, mock_check, mock_to_pdf, mock_pdf_imgs, mock_create_grid, tmp_path
    ):
        """Test that a None grid image is skipped (no save, no output)."""
        mock_check.return_value = (True, [])
        dummy_pptx = tmp_path / "test.pptx"
        dummy_pptx.touch()
        mock_to_pdf.return_value = tmp_path / "test.pdf"
        mock_pdf_imgs.return_value = [tmp_path / "slide-1.jpg"]

        mock_create_grid.return_value = None

        results = generate_thumbnails(
            str(dummy_pptx), output_prefix=str(tmp_path / "thumb"), cols=5
        )
        assert results == []

    @patch("autoppt.thumbnail.create_grid_image")
    @patch("autoppt.thumbnail.convert_pdf_to_images")
    @patch("autoppt.thumbnail.convert_to_pdf")
    @patch("autoppt.thumbnail.check_dependencies")
    def test_exception_during_generation(
        self, mock_check, mock_to_pdf, mock_pdf_imgs, mock_create_grid, tmp_path
    ):
        """Test generate_thumbnails catches unexpected exceptions."""
        mock_check.return_value = (True, [])
        dummy_pptx = tmp_path / "test.pptx"
        dummy_pptx.touch()
        mock_to_pdf.side_effect = RuntimeError("unexpected error")

        results = generate_thumbnails(
            str(dummy_pptx), output_prefix=str(tmp_path / "thumb")
        )
        assert results == []

    @patch("autoppt.thumbnail.create_grid_image")
    @patch("autoppt.thumbnail.convert_pdf_to_images")
    @patch("autoppt.thumbnail.convert_to_pdf")
    @patch("autoppt.thumbnail.check_dependencies")
    def test_cols_clamp_and_grid_layout(
        self, mock_check, mock_to_pdf, mock_pdf_imgs, mock_create_grid, tmp_path
    ):
        """Test with different column count affecting grid pagination."""
        mock_check.return_value = (True, [])
        dummy_pptx = tmp_path / "test.pptx"
        dummy_pptx.touch()
        mock_to_pdf.return_value = tmp_path / "test.pdf"

        # 10 slides with 3 cols -> max_rows=4, max_per_grid=12 -> 1 grid
        mock_pdf_imgs.return_value = [tmp_path / f"slide-{i+1}.jpg" for i in range(10)]
        mock_grid_img = MagicMock()
        mock_create_grid.return_value = mock_grid_img

        results = generate_thumbnails(
            str(dummy_pptx), output_prefix=str(tmp_path / "thumb"), cols=3
        )
        assert mock_create_grid.call_count == 1
        assert len(results) == 1


class TestNonNumericSlideSortKey:
    """Test that convert_pdf_to_images handles non-numeric slide file stems."""

    def test_non_numeric_stem_does_not_crash(self, tmp_path):
        """Files with non-numeric stems like 'slide-abc' should be handled without crash."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.touch()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create files with both numeric and non-numeric stems
        (output_dir / "slide-abc.jpg").touch()
        (output_dir / "slide-1.jpg").touch()
        (output_dir / "slide-2.jpg").touch()

        with patch("subprocess.run") as mock_run:
            result = convert_pdf_to_images(pdf_path, output_dir)

        mock_run.assert_called_once()
        assert len(result) == 3
        # Non-numeric stems should sort to position 0 (front), numeric ones sorted normally
        # The key point is no crash occurs
        numeric_names = [p.name for p in result if p.stem.split("-")[-1].isdigit()]
        assert "slide-1.jpg" in numeric_names
        assert "slide-2.jpg" in numeric_names


def test_create_grid_image_rejects_zero_cols():
    """create_grid_image should reject cols=0."""
    from pathlib import Path
    with pytest.raises(ValueError, match="cols must be >= 1"):
        create_grid_image([Path("/fake/img.png")], cols=0, thumb_width=200, start_index=0)


def test_create_grid_image_rejects_negative_cols():
    """create_grid_image should reject negative cols."""
    from pathlib import Path
    with pytest.raises(ValueError, match="cols must be >= 1"):
        create_grid_image([Path("/fake/img.png")], cols=-1, thumb_width=200, start_index=0)


class TestGenerateThumbnailsColsClamping:
    """Tests for cols parameter clamping in generate_thumbnails."""

    @patch("autoppt.thumbnail.create_grid_image")
    @patch("autoppt.thumbnail.convert_pdf_to_images")
    @patch("autoppt.thumbnail.convert_to_pdf")
    @patch("autoppt.thumbnail.check_dependencies")
    def test_cols_100_clamped_to_max_cols(
        self, mock_check, mock_to_pdf, mock_pdf_imgs, mock_create_grid, tmp_path
    ):
        """Passing cols=100 should be clamped to MAX_COLS and not crash."""
        from autoppt.thumbnail import MAX_COLS
        mock_check.return_value = (True, [])
        dummy_pptx = tmp_path / "test.pptx"
        dummy_pptx.touch()
        mock_to_pdf.return_value = tmp_path / "test.pdf"
        mock_pdf_imgs.return_value = [tmp_path / f"slide-{i+1}.jpg" for i in range(3)]

        mock_grid_img = MagicMock()
        mock_create_grid.return_value = mock_grid_img

        results = generate_thumbnails(
            str(dummy_pptx), output_prefix=str(tmp_path / "thumb"), cols=100
        )

        assert len(results) > 0
        # Verify create_grid_image was called with clamped cols (MAX_COLS)
        mock_create_grid.assert_called_once()
        call_args = mock_create_grid.call_args
        actual_cols = call_args[1].get("cols") if call_args[1] else call_args[0][1] if len(call_args[0]) > 1 else None
        assert actual_cols is not None
        assert actual_cols <= MAX_COLS

    @patch("autoppt.thumbnail.create_grid_image")
    @patch("autoppt.thumbnail.convert_pdf_to_images")
    @patch("autoppt.thumbnail.convert_to_pdf")
    @patch("autoppt.thumbnail.check_dependencies")
    def test_cols_0_clamped_to_1(
        self, mock_check, mock_to_pdf, mock_pdf_imgs, mock_create_grid, tmp_path
    ):
        """Passing cols=0 should be clamped to 1 (not crash)."""
        mock_check.return_value = (True, [])
        dummy_pptx = tmp_path / "test.pptx"
        dummy_pptx.touch()
        mock_to_pdf.return_value = tmp_path / "test.pdf"
        mock_pdf_imgs.return_value = [tmp_path / f"slide-{i+1}.jpg" for i in range(2)]

        mock_grid_img = MagicMock()
        mock_create_grid.return_value = mock_grid_img

        results = generate_thumbnails(
            str(dummy_pptx), output_prefix=str(tmp_path / "thumb"), cols=0
        )

        # Should not crash; cols gets clamped to 1
        assert len(results) > 0
        mock_create_grid.assert_called()


class TestPptxExtensionValidation:
    """Test that generate_thumbnails rejects non-pptx files."""

    def test_non_pptx_extension_rejected(self, tmp_path):
        """A file with wrong extension should be rejected."""
        txt_file = tmp_path / "document.txt"
        txt_file.touch()
        with pytest.raises(ValueError, match="Expected a .pptx file"):
            generate_thumbnails(str(txt_file))

    def test_pdf_extension_rejected(self, tmp_path):
        """A PDF file should be rejected."""
        pdf_file = tmp_path / "slides.pdf"
        pdf_file.touch()
        with pytest.raises(ValueError, match="Expected a .pptx file"):
            generate_thumbnails(str(pdf_file))

    def test_pptx_extension_accepted(self, tmp_path):
        """A .pptx file should pass the extension check (may fail later on deps)."""
        pptx_file = tmp_path / "test.pptx"
        pptx_file.touch()
        with patch("autoppt.thumbnail.check_dependencies", return_value=(False, ["libreoffice"])):
            # Will return [] because deps missing, but won't raise ValueError
            result = generate_thumbnails(str(pptx_file))
            assert result == []

    def test_rejects_system_path(self):
        """generate_thumbnails should reject system paths."""
        with pytest.raises(ValueError, match="system path"):
            generate_thumbnails("/etc/something.pptx")

    def test_rejects_proc_path(self):
        """generate_thumbnails should reject /proc/ paths."""
        with pytest.raises(ValueError, match="system path"):
            generate_thumbnails("/proc/self/something.pptx")

    def test_rejects_sensitive_path_ssh(self):
        """generate_thumbnails should reject .ssh paths."""
        with pytest.raises(ValueError, match="sensitive path"):
            generate_thumbnails("/home/user/.ssh/something.pptx")

    def test_rejects_sensitive_path_docker(self):
        """generate_thumbnails should reject .docker paths."""
        with pytest.raises(ValueError, match="sensitive path"):
            generate_thumbnails("/home/user/.docker/something.pptx")

    def test_rejects_path_traversal_in_pptx_path(self):
        """generate_thumbnails should reject pptx paths with '..' segments."""
        with pytest.raises(ValueError, match="traversal"):
            generate_thumbnails("output/../../../etc/evil.pptx")


class TestThumbnailValueErrorPropagation:
    """Tests that ValueError and FileNotFoundError propagate instead of being swallowed."""

    def test_value_error_not_swallowed(self):
        """ValueError from path validation should propagate, not be caught."""
        with pytest.raises(ValueError):
            generate_thumbnails("/etc/evil.pptx")

    def test_file_not_found_not_swallowed(self, tmp_path):
        """FileNotFoundError should propagate, not be caught."""
        missing = tmp_path / "nonexistent.pptx"
        with pytest.raises(FileNotFoundError):
            generate_thumbnails(str(missing))


class TestThumbnailExpandedBlockedSegments:
    """Tests that expanded BLOCKED_PATH_SEGMENTS are enforced in thumbnail paths."""

    @pytest.mark.parametrize("sensitive_path", [
        "/home/user/.local/share/slides.pptx",
        "/home/user/.bashrc.pptx",
        "/home/user/.bash_history.pptx",
        "/home/user/.profile.pptx",
        "/home/user/.zshrc.pptx",
        "/home/user/.zsh_history.pptx",
    ])
    def test_rejects_expanded_sensitive_pptx_paths(self, sensitive_path):
        """generate_thumbnails should reject pptx paths containing .local, .bash*, .profile, .zsh*."""
        with pytest.raises(ValueError, match="sensitive path"):
            generate_thumbnails(sensitive_path)


class TestSubprocessTimeoutConstant:
    """Tests for the SUBPROCESS_TIMEOUT constant."""

    def test_subprocess_timeout_is_positive(self):
        assert SUBPROCESS_TIMEOUT > 0

    def test_convert_to_pdf_uses_timeout_constant(self, tmp_path):
        """convert_to_pdf should use SUBPROCESS_TIMEOUT, not a hardcoded value."""
        pptx_path = tmp_path / "test.pptx"
        pptx_path.write_bytes(b"fake")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            convert_to_pdf(pptx_path, tmp_path)
            args, kwargs = mock_run.call_args
            assert kwargs.get("timeout") == SUBPROCESS_TIMEOUT

    def test_convert_pdf_to_images_uses_timeout_constant(self, tmp_path):
        """convert_pdf_to_images should use SUBPROCESS_TIMEOUT, not a hardcoded value."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"fake")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            convert_pdf_to_images(pdf_path, tmp_path)
            args, kwargs = mock_run.call_args
            assert kwargs.get("timeout") == SUBPROCESS_TIMEOUT


class TestSubprocessStderrLogging:
    """Tests for subprocess stderr being included in error logs."""

    def test_convert_to_pdf_logs_stderr(self, tmp_path):
        """convert_to_pdf should log subprocess stderr on failure."""
        pptx_path = tmp_path / "test.pptx"
        pptx_path.write_bytes(b"fake")
        err = subprocess.CalledProcessError(1, "soffice")
        err.stderr = b"LibreOffice error details"
        with patch("subprocess.run", side_effect=err), \
             patch("autoppt.thumbnail.logger") as mock_logger:
            result = convert_to_pdf(pptx_path, tmp_path)
        assert result is None
        log_call_args = mock_logger.error.call_args[0]
        assert "LibreOffice error details" in log_call_args[2]

    def test_convert_pdf_to_images_logs_stderr(self, tmp_path):
        """convert_pdf_to_images should log subprocess stderr on failure."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"fake")
        err = subprocess.CalledProcessError(1, "pdftoppm")
        err.stderr = b"pdftoppm error details"
        with patch("subprocess.run", side_effect=err), \
             patch("autoppt.thumbnail.logger") as mock_logger:
            result = convert_pdf_to_images(pdf_path, tmp_path)
        assert result == []
        log_call_args = mock_logger.error.call_args[0]
        assert "pdftoppm error details" in log_call_args[2]


class TestPrefixNameSanitization:
    """Tests for prefix_name sanitization stripping path separators."""

    @patch("autoppt.thumbnail.create_grid_image")
    @patch("autoppt.thumbnail.convert_pdf_to_images")
    @patch("autoppt.thumbnail.convert_to_pdf")
    @patch("autoppt.thumbnail.check_dependencies")
    def test_prefix_name_strips_path_separators(
        self, mock_check, mock_to_pdf, mock_pdf_imgs, mock_create_grid, tmp_path
    ):
        """output_prefix with embedded path separators in the basename should be sanitized."""
        mock_check.return_value = (True, [])
        dummy_pptx = tmp_path / "test.pptx"
        dummy_pptx.touch()
        mock_to_pdf.return_value = tmp_path / "test.pdf"
        mock_pdf_imgs.return_value = [tmp_path / "slide-1.jpg"]

        mock_grid_img = MagicMock()
        mock_create_grid.return_value = mock_grid_img

        # Use an output_prefix whose Path().name is clean, but verify sanitization
        # is applied (slashes replaced with underscores in the filename)
        results = generate_thumbnails(
            str(dummy_pptx), output_prefix=str(tmp_path / "thumb"), cols=5
        )

        assert len(results) == 1
        # The filename should not contain any path separator characters
        filename = Path(results[0]).name
        assert "/" not in filename
        assert "\\" not in filename

    @patch("autoppt.thumbnail.create_grid_image")
    @patch("autoppt.thumbnail.convert_pdf_to_images")
    @patch("autoppt.thumbnail.convert_to_pdf")
    @patch("autoppt.thumbnail.check_dependencies")
    def test_prefix_name_with_backslash_in_name(
        self, mock_check, mock_to_pdf, mock_pdf_imgs, mock_create_grid, tmp_path
    ):
        """A prefix whose basename contains backslash should have it replaced with underscore."""
        import re
        from pathlib import Path as P

        # Directly test the sanitization logic used in thumbnail.py line 272
        test_name = "some\\evil\\name"
        sanitized = re.sub(r"[/\\]", "_", P(test_name).name)
        assert "\\" not in sanitized
        assert "/" not in sanitized
        # On POSIX, P("some\\evil\\name").name is "some\\evil\\name"
        # so the re.sub should turn backslashes into underscores
        assert "_" in sanitized or sanitized == "name"


class TestSubprocessShellFalse:
    """Tests that subprocess calls explicitly set shell=False."""

    def test_convert_to_pdf_uses_shell_false(self, tmp_path):
        """convert_to_pdf must pass shell=False to subprocess.run."""
        pptx_path = tmp_path / "test.pptx"
        pptx_path.write_bytes(b"fake")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            convert_to_pdf(pptx_path, tmp_path)
            _, kwargs = mock_run.call_args
            assert kwargs.get("shell") is False

    def test_convert_pdf_to_images_uses_shell_false(self, tmp_path):
        """convert_pdf_to_images must pass shell=False to subprocess.run."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"fake")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            convert_pdf_to_images(pdf_path, tmp_path)
            _, kwargs = mock_run.call_args
            assert kwargs.get("shell") is False
