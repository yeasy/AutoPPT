"""
Thumbnail generation utility for PowerPoint presentations.
"""
import os
import sys
import logging
import shutil
import tempfile
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# Constants
THUMBNAIL_WIDTH = 300  # Fixed thumbnail width in pixels
CONVERSION_DPI = 100  # DPI for PDF to image conversion
MAX_COLS = 6  # Maximum number of columns
DEFAULT_COLS = 5  # Default number of columns
JPEG_QUALITY = 95  # JPEG compression quality
GRID_PADDING = 20  # Padding between thumbnails
BORDER_WIDTH = 2  # Border width around thumbnails
FONT_SIZE_RATIO = 0.12  # Font size as fraction of thumbnail width
LABEL_PADDING_RATIO = 0.4  # Label padding as fraction of font size


def check_dependencies() -> Tuple[bool, List[str]]:
    """Check if required external tools are installed."""
    missing = []
    
    # Check for LibreOffice (soffice)
    if not shutil.which("soffice"):
        missing.append("libreoffice")
        
    # Check for pdftoppm (poppler)
    if not shutil.which("pdftoppm"):
        missing.append("poppler-utils")
        
    return len(missing) == 0, missing


def convert_to_pdf(pptx_path: Path, output_dir: Path) -> Optional[Path]:
    """Convert PPTX to PDF using LibreOffice."""
    logger.info("Converting %s to PDF...", pptx_path)

    cmd = [
        "soffice",
        "--headless",
        "--convert-to",
        "pdf",
        "--outdir",
        str(output_dir),
        str(pptx_path),
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)
        pdf_path = output_dir / f"{pptx_path.stem}.pdf"
        if pdf_path.exists():
            return pdf_path
        return None
    except subprocess.CalledProcessError as e:
        logger.error("Failed to convert PPTX to PDF: %s", e)
        return None
    except subprocess.TimeoutExpired:
        logger.error("LibreOffice conversion timed out for %s", pptx_path)
        return None


def convert_pdf_to_images(pdf_path: Path, output_dir: Path) -> List[Path]:
    """Convert PDF pages to images using pdftoppm."""
    logger.info("Converting PDF to images...")

    cmd = [
        "pdftoppm",
        "-jpeg",
        "-r",
        str(CONVERSION_DPI),
        str(pdf_path),
        str(output_dir / "slide"),
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)
        # pdftoppm generates files like slide-1.jpg, slide-01.jpg, etc.
        # sort them by number
        images = sorted(list(output_dir.glob("slide-*.jpg")), key=lambda p: int(p.stem.split("-")[-1]))
        return images
    except subprocess.CalledProcessError as e:
        logger.error("Failed to convert PDF to images: %s", e)
        return []
    except subprocess.TimeoutExpired:
        logger.error("PDF to image conversion timed out for %s", pdf_path)
        return []


def create_grid_image(
    images: List[Path],
    cols: int,
    thumb_width: int,
    start_index: int
) -> Image.Image | None:
    """Create a single grid image from a list of slide images."""
    if not images:
        return None
        
    # Calculate grid dimensions
    rows = (len(images) + cols - 1) // cols
    
    # helper to open first image to get aspect ratio
    with Image.open(images[0]) as first_img:
        aspect_ratio = first_img.height / first_img.width
        
    thumb_height = int(thumb_width * aspect_ratio)
    
    # Calculate layout
    font_size = int(thumb_width * FONT_SIZE_RATIO)
    label_height = int(font_size * (1 + LABEL_PADDING_RATIO * 2))
    
    cell_width = thumb_width + GRID_PADDING
    cell_height = thumb_height + label_height + GRID_PADDING
    
    grid_width = (cols * cell_width) + GRID_PADDING
    grid_height = (rows * cell_height) + GRID_PADDING
    
    # Create background
    grid_img = Image.new("RGB", (grid_width, grid_height), "white")
    draw = ImageDraw.Draw(grid_img)
    
    # Try to load a font, fallback to default
    try:
        font = ImageFont.truetype("Arial.ttf", font_size)
    except IOError:
        try:
            # Try generic Linux/Mac location
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
        except IOError:
            font = ImageFont.load_default()  # type: ignore[assignment]
    
    # Place images
    for idx, img_path in enumerate(images):
        row = idx // cols
        col = idx % cols
        
        x = GRID_PADDING + (col * cell_width)
        y = GRID_PADDING + (row * cell_height)
        
        # Open and resize image
        with Image.open(img_path) as img:
            img_resized = img.resize((thumb_width, thumb_height), Image.Resampling.LANCZOS)
            grid_img.paste(img_resized, (x, y + label_height))
            
            # Draw border
            draw.rectangle(
                [x, y + label_height, x + thumb_width, y + label_height + thumb_height],
                outline="#CCCCCC",
                width=BORDER_WIDTH
            )
            
            # Draw label
            label = f"Slide {start_index + idx}"
            text_bbox = draw.textbbox((0, 0), label, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            
            text_x = x + (thumb_width - text_width) // 2
            text_y = y + (label_height - font_size) // 2
            
            draw.text((text_x, text_y), label, fill="black", font=font)
            
    return grid_img


def generate_thumbnails(
    pptx_path: str,
    output_prefix: str = "thumbnails",
    cols: int = DEFAULT_COLS
) -> List[str]:
    """
    Generate thumbnail grids for a PowerPoint presentation.
    
    Args:
        pptx_path: Path to the .pptx file
        output_prefix: Prefix for output files (e.g. "output/thumbnails")
        cols: Number of columns in the grid
        
    Returns:
        List of paths to generated thumbnail grid images
    """
    pptx_file = Path(pptx_path).resolve()
    if not pptx_file.exists():
        raise FileNotFoundError(f"File not found: {pptx_path}")
        
    # Check dependencies
    is_ok, missing = check_dependencies()
    if not is_ok:
        logger.warning("Missing dependencies for thumbnail generation: %s", ", ".join(missing))
        logger.warning("Please install LibreOffice and poppler-utils.")
        return []

    generated_files = []
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # 1. Convert to PDF
            pdf_path = convert_to_pdf(pptx_file, temp_path)
            if not pdf_path:
                return []
                
            # 2. Convert to Images
            slide_images = convert_pdf_to_images(pdf_path, temp_path)
            if not slide_images:
                return []
                
            # 3. Create Grids
            # Calculate max slides per grid
            # For 5 columns, max 30 slides (5x6) to keep aspect ratio reasonable
            max_rows = cols + 1
            max_slides_per_grid = cols * max_rows
            
            total_slides = len(slide_images)
            num_grids = (total_slides + max_slides_per_grid - 1) // max_slides_per_grid
            
            output_dir = Path(output_prefix).parent
            output_dir.mkdir(parents=True, exist_ok=True)
            prefix_name = Path(output_prefix).name
            
            for i in range(num_grids):
                start_idx = i * max_slides_per_grid
                end_idx = min((i + 1) * max_slides_per_grid, total_slides)
                batch_images = slide_images[start_idx:end_idx]
                
                grid_img = create_grid_image(
                    batch_images, 
                    cols, 
                    THUMBNAIL_WIDTH, 
                    start_idx
                )
                
                if num_grids > 1:
                    filename = f"{prefix_name}-{i+1}.jpg"
                else:
                    filename = f"{prefix_name}.jpg"
                    
                output_path = output_dir / filename
                if grid_img is None:
                    continue
                grid_img.save(output_path, quality=JPEG_QUALITY)
                generated_files.append(str(output_path))
                
                logger.info("Created thumbnail grid: %s", output_path)

    except Exception as e:
        logger.error("Error generating thumbnails: %s", e, exc_info=True)
        return []
        
    return generated_files
