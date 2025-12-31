import os
import logging
from typing import Optional, List, Dict, Any

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE

from .data_types import UserPresentation, SlideConfig

logger = logging.getLogger(__name__)

class PPTRenderer:
    def __init__(self, template_path: str = None):
        if template_path:
            self.prs = Presentation(template_path)
        else:
            self.prs = Presentation()
            
    def add_title_slide(self, title: str, subtitle: str = ""):
        """Add a title slide with styled colors."""
        slide_layout = self.prs.slide_layouts[0]
        slide = self.prs.slides.add_slide(slide_layout)
        
        self._apply_background(slide)
        
        title_shape = slide.shapes.title
        subtitle_shape = slide.placeholders[1]
        
        title_shape.text = title
        self._style_text_shape(title_shape, is_title=True)
        
        subtitle_shape.text = subtitle
        self._style_text_shape(subtitle_shape, is_title=False)
        
    def add_section_header(self, title: str):
        """Add a section header slide."""
        slide_layout = self.prs.slide_layouts[2] # Usually Section Header
        slide = self.prs.slides.add_slide(slide_layout)
        
        self._apply_background(slide)
        
        if slide.shapes.title:
            slide.shapes.title.text = title
            self._style_text_shape(slide.shapes.title, is_title=True)
            
    def apply_style(self, style_name: str) -> None:
        """Setup global presentation style (colors, fonts)."""
        styles = {
            "technology": {
                "title_color": RGBColor(0, 102, 204),
                "text_color": RGBColor(200, 200, 255),
                "font_name": "Arial",
                "bg_color": RGBColor(10, 10, 40),
                "accent_color": RGBColor(0, 150, 255)
            },
            "nature": {
                "title_color": RGBColor(34, 139, 34),
                "text_color": RGBColor(50, 80, 50),
                "font_name": "Georgia",
                "bg_color": RGBColor(245, 255, 250),
                "accent_color": RGBColor(60, 179, 113)
            },
            "creative": {
                "title_color": RGBColor(200, 50, 150),
                "text_color": RGBColor(60, 40, 60),
                "font_name": "Verdana",
                "bg_color": RGBColor(255, 250, 240),
                "accent_color": RGBColor(255, 105, 180)
            },
            "minimalist": {
                "title_color": RGBColor(40, 40, 40),
                "text_color": RGBColor(80, 80, 80),
                "font_name": "Arial",
                "bg_color": RGBColor(255, 255, 255),
                "accent_color": RGBColor(100, 100, 100)
            },
            # New themes added in v0.2
            "corporate": {
                "title_color": RGBColor(0, 51, 102),
                "text_color": RGBColor(51, 51, 51),
                "font_name": "Calibri",
                "bg_color": RGBColor(240, 248, 255),
                "accent_color": RGBColor(0, 102, 153)
            },
            "academic": {
                "title_color": RGBColor(128, 0, 32),
                "text_color": RGBColor(64, 64, 64),
                "font_name": "Times New Roman",
                "bg_color": RGBColor(255, 253, 245),
                "accent_color": RGBColor(139, 69, 19)
            },
            "startup": {
                "title_color": RGBColor(255, 87, 51),
                "text_color": RGBColor(51, 51, 51),
                "font_name": "Helvetica",
                "bg_color": RGBColor(250, 250, 250),
                "accent_color": RGBColor(255, 140, 0)
            },
            "dark": {
                "title_color": RGBColor(0, 200, 150),
                "text_color": RGBColor(200, 200, 200),
                "font_name": "Consolas",
                "bg_color": RGBColor(20, 20, 30),
                "accent_color": RGBColor(138, 43, 226)
            }
        }
        self.current_style = styles.get(style_name.lower(), styles["minimalist"])
        logger.info(f"Applied theme: {style_name}")

    def _apply_background(self, slide):
        """Apply the current style's background color."""
        if hasattr(self, 'current_style'):
            slide.background.fill.solid()
            slide.background.fill.fore_color.rgb = self.current_style["bg_color"]

    def _style_text_shape(self, shape, is_title=False):
        """Apply colors and fonts to a shape's text."""
        if not hasattr(self, 'current_style') or not shape.has_text_frame:
            return
            
        color = self.current_style["title_color"] if is_title else self.current_style["text_color"]
        
        for paragraph in shape.text_frame.paragraphs:
            for run in paragraph.runs:
                run.font.name = self.current_style["font_name"]
                run.font.color.rgb = color

    def add_content_slide(self, title: str, bullets: list, notes: str = "", image_path: str = None):
        slide_layout = self.prs.slide_layouts[1] # 1 is usually Title and Content
        slide = self.prs.slides.add_slide(slide_layout)
        
        self._apply_background(slide)
        
        # Title
        title_shape = slide.shapes.title
        title_shape.text = title
        self._style_text_shape(title_shape, is_title=True)
        
        # Content (Bullets)
        body_shape = slide.placeholders[1]
        
        # If image, we resize the body shape to make room
        if image_path and os.path.exists(image_path):
            body_shape.width = Inches(5.5)
            try:
                slide.shapes.add_picture(image_path, Inches(6), Inches(1.5), height=Inches(5))
            except Exception as e:
                logger.warning(f"Failed to add image {image_path}: {e}")
        
        tf = body_shape.text_frame
        tf.word_wrap = True
        tf.clear() 
        
        for bullet in bullets:
            p = tf.add_paragraph()
            p.text = bullet
            p.level = 0
            
        self._style_text_shape(body_shape, is_title=False)
            
        # Add Notes
        if notes:
            notes_slide = slide.notes_slide
            text_frame = notes_slide.notes_text_frame
            text_frame.text = notes

    def add_chart_slide(self, title: str, chart_data: 'ChartData', notes: str = "") -> None:
        """
        Add a slide with a chart visualization.
        Supports bar, pie, line, and column charts.
        """
        from .data_types import ChartType
        
        slide_layout = self.prs.slide_layouts[5]  # Blank layout for more space
        slide = self.prs.slides.add_slide(slide_layout)
        
        self._apply_background(slide)
        
        # Add title manually
        from pptx.util import Inches, Pt
        title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(9), Inches(0.8))
        tf = title_box.text_frame
        tf.text = title
        for paragraph in tf.paragraphs:
            paragraph.font.size = Pt(28)
            paragraph.font.bold = True
            if hasattr(self, 'current_style'):
                paragraph.font.color.rgb = self.current_style["title_color"]
        
        # Prepare chart data
        chart_data_obj = CategoryChartData()
        chart_data_obj.categories = chart_data.categories
        chart_data_obj.add_series(chart_data.series_name, chart_data.values)
        
        # Map chart type to python-pptx enum
        chart_type_map = {
            ChartType.BAR: XL_CHART_TYPE.BAR_CLUSTERED,
            ChartType.COLUMN: XL_CHART_TYPE.COLUMN_CLUSTERED,
            ChartType.LINE: XL_CHART_TYPE.LINE,
            ChartType.PIE: XL_CHART_TYPE.PIE,
        }
        xl_chart_type = chart_type_map.get(chart_data.chart_type, XL_CHART_TYPE.COLUMN_CLUSTERED)
        
        # Add chart
        x, y, cx, cy = Inches(1), Inches(1.5), Inches(8), Inches(5)
        chart = slide.shapes.add_chart(xl_chart_type, x, y, cx, cy, chart_data_obj).chart
        
        # Style the chart title
        chart.has_title = True
        chart.chart_title.text_frame.text = chart_data.title
        
        logger.info(f"Added {chart_data.chart_type.value} chart: {chart_data.title}")
        
        # Add Notes
        if notes:
            notes_slide = slide.notes_slide
            text_frame = notes_slide.notes_text_frame
            text_frame.text = notes
            
    def add_citations_slide(self, citations: List[str]) -> None:
        """Add a references/citations slide."""
        if not citations:
            return
            
        slide_layout = self.prs.slide_layouts[1]
        slide = self.prs.slides.add_slide(slide_layout)
        
        self._apply_background(slide)
        
        title_shape = slide.shapes.title
        title_shape.text = "References"
        self._style_text_shape(title_shape, is_title=True)
        
        body_shape = slide.placeholders[1]
        tf = body_shape.text_frame
        tf.clear()
        
        for cit in citations:
            p = tf.add_paragraph()
            p.text = cit
            p.font.size = Pt(12)
        
        self._style_text_shape(body_shape, is_title=False)
        logger.info(f"Added citations slide with {len(citations)} references")
            
    def save(self, output_path: str) -> None:
        """Save the presentation to a file."""
        self.prs.save(output_path)
        logger.info(f"Saved presentation to {output_path}")

