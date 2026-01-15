"""
Unit tests for thumbnail generation.
"""
import pytest
import sys
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from autoppt.thumbnail import generate_thumbnails, check_dependencies, convert_to_pdf

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
