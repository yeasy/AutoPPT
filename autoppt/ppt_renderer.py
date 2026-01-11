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
        
        # Add decoration line for themes that support it
        self._add_decoration_line(slide, y_position=3.5)

        
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
                "accent_color": RGBColor(0, 150, 255),
                "gradient": True,
                "gradient_end": RGBColor(30, 30, 80)
            },
            "nature": {
                "title_color": RGBColor(34, 139, 34),
                "text_color": RGBColor(50, 80, 50),
                "font_name": "Georgia",
                "bg_color": RGBColor(245, 255, 250),
                "accent_color": RGBColor(60, 179, 113),
                "gradient": False
            },
            "creative": {
                "title_color": RGBColor(200, 50, 150),
                "text_color": RGBColor(60, 40, 60),
                "font_name": "Verdana",
                "bg_color": RGBColor(255, 250, 240),
                "accent_color": RGBColor(255, 105, 180),
                "gradient": False
            },
            "minimalist": {
                "title_color": RGBColor(40, 40, 40),
                "text_color": RGBColor(80, 80, 80),
                "font_name": "Arial",
                "bg_color": RGBColor(255, 255, 255),
                "accent_color": RGBColor(100, 100, 100),
                "gradient": False
            },
            "corporate": {
                "title_color": RGBColor(0, 51, 102),
                "text_color": RGBColor(51, 51, 51),
                "font_name": "Calibri",
                "bg_color": RGBColor(240, 248, 255),
                "accent_color": RGBColor(0, 102, 153),
                "gradient": False
            },
            "academic": {
                "title_color": RGBColor(128, 0, 32),
                "text_color": RGBColor(64, 64, 64),
                "font_name": "Times New Roman",
                "bg_color": RGBColor(255, 253, 245),
                "accent_color": RGBColor(139, 69, 19),
                "gradient": False
            },
            "startup": {
                "title_color": RGBColor(255, 87, 51),
                "text_color": RGBColor(51, 51, 51),
                "font_name": "Helvetica",
                "bg_color": RGBColor(250, 250, 250),
                "accent_color": RGBColor(255, 140, 0),
                "gradient": False
            },
            "dark": {
                "title_color": RGBColor(0, 200, 150),
                "text_color": RGBColor(200, 200, 200),
                "font_name": "Consolas",
                "bg_color": RGBColor(20, 20, 30),
                "accent_color": RGBColor(138, 43, 226),
                "gradient": True,
                "gradient_end": RGBColor(40, 20, 60)
            },
            # ========== NEW MODERN THEMES (v0.4) ==========
            "luxury": {
                "title_color": RGBColor(212, 175, 55),  # Gold
                "text_color": RGBColor(240, 240, 240),
                "font_name": "Georgia",
                "bg_color": RGBColor(25, 25, 35),
                "accent_color": RGBColor(180, 140, 40),
                "gradient": True,
                "gradient_end": RGBColor(45, 35, 55),
                "decoration_line": True
            },
            "magazine": {
                "title_color": RGBColor(220, 20, 60),  # Crimson
                "text_color": RGBColor(30, 30, 30),
                "font_name": "Helvetica",
                "bg_color": RGBColor(255, 255, 255),
                "accent_color": RGBColor(220, 20, 60),
                "gradient": False,
                "decoration_line": True
            },
            "tech_gradient": {
                "title_color": RGBColor(255, 255, 255),
                "text_color": RGBColor(230, 230, 250),
                "font_name": "Arial",
                "bg_color": RGBColor(63, 81, 181),  # Indigo
                "accent_color": RGBColor(0, 188, 212),  # Cyan
                "gradient": True,
                "gradient_end": RGBColor(156, 39, 176),  # Purple
                "decoration_line": True
            },
            "ocean": {
                "title_color": RGBColor(255, 255, 255),
                "text_color": RGBColor(220, 240, 255),
                "font_name": "Arial",
                "bg_color": RGBColor(0, 105, 148),
                "accent_color": RGBColor(0, 200, 200),
                "gradient": True,
                "gradient_end": RGBColor(0, 50, 100),
                "decoration_line": False
            },
            "sunset": {
                "title_color": RGBColor(255, 255, 255),
                "text_color": RGBColor(255, 240, 220),
                "font_name": "Georgia",
                "bg_color": RGBColor(255, 100, 80),
                "accent_color": RGBColor(255, 200, 100),
                "gradient": True,
                "gradient_end": RGBColor(180, 50, 100),
                "decoration_line": True
            }
        }
        self.current_style = styles.get(style_name.lower(), styles["minimalist"])
        logger.info(f"Applied theme: {style_name}")

    def _apply_background(self, slide):
        """Apply the current style's background color or gradient."""
        if not hasattr(self, 'current_style'):
            return
            
        # Check if gradient is enabled for this theme
        if self.current_style.get("gradient") and "gradient_end" in self.current_style:
            try:
                from pptx.enum.dml import MSO_THEME_COLOR
                from pptx.oxml.ns import qn
                from pptx.oxml import parse_xml
                
                # Apply gradient background using XML manipulation
                bg = slide.background
                bg.fill.gradient()
                bg.fill.gradient_angle = 270  # Top to bottom
                bg.fill.gradient_stops[0].color.rgb = self.current_style["bg_color"]
                bg.fill.gradient_stops[1].color.rgb = self.current_style["gradient_end"]
            except Exception as e:
                # Fallback to solid color if gradient fails
                logger.debug(f"Gradient fallback: {e}")
                slide.background.fill.solid()
                slide.background.fill.fore_color.rgb = self.current_style["bg_color"]
        else:
            slide.background.fill.solid()
            slide.background.fill.fore_color.rgb = self.current_style["bg_color"]
    
    def _add_decoration_line(self, slide, y_position: float = 1.2):
        """Add a decorative accent line below the title."""
        if not hasattr(self, 'current_style'):
            return
        if not self.current_style.get("decoration_line", False):
            return
            
        from pptx.enum.shapes import MSO_SHAPE
        
        # Add a thin accent line
        line = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(0.5),          # Left
            Inches(y_position),   # Top (below title)
            Inches(2),            # Width
            Inches(0.05)          # Height (thin line)
        )
        line.fill.solid()
        line.fill.fore_color.rgb = self.current_style["accent_color"]
        line.line.fill.background()  # No border

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
    
    def add_fullscreen_image_slide(self, image_path: str, caption: str = "", overlay_title: str = "") -> None:
        """
        Add a fullscreen image slide for visual impact (great for section openers).
        
        Args:
            image_path: Path to the image file
            caption: Optional small caption at the bottom
            overlay_title: Optional large title overlaid on the image
        """
        if not image_path or not os.path.exists(image_path):
            logger.warning(f"Image not found: {image_path}")
            return
            
        slide_layout = self.prs.slide_layouts[6]  # Blank layout
        slide = self.prs.slides.add_slide(slide_layout)
        
        # Add fullscreen image
        try:
            slide.shapes.add_picture(
                image_path,
                Inches(0), Inches(0),
                width=self.prs.slide_width,
                height=self.prs.slide_height
            )
        except Exception as e:
            logger.error(f"Failed to add fullscreen image: {e}")
            return
        
        # Add overlay title if provided
        if overlay_title:
            title_box = slide.shapes.add_textbox(
                Inches(0.5), Inches(3),
                Inches(9), Inches(1.5)
            )
            tf = title_box.text_frame
            tf.text = overlay_title
            for paragraph in tf.paragraphs:
                paragraph.font.size = Pt(48)
                paragraph.font.bold = True
                paragraph.font.color.rgb = RGBColor(255, 255, 255)
                # Add shadow effect via font name styling
                if hasattr(self, 'current_style'):
                    paragraph.font.name = self.current_style["font_name"]
        
        # Add caption if provided
        if caption:
            caption_box = slide.shapes.add_textbox(
                Inches(0.5), Inches(6.5),
                Inches(9), Inches(0.5)
            )
            tf = caption_box.text_frame
            tf.text = caption
            for paragraph in tf.paragraphs:
                paragraph.font.size = Pt(14)
                paragraph.font.color.rgb = RGBColor(220, 220, 220)
        
        logger.info(f"Added fullscreen image slide: {overlay_title or 'No title'}")
    
    def add_statistics_slide(self, title: str, stats: List[Dict[str, str]], notes: str = "") -> None:
        """
        Add a slide highlighting key statistics with large numbers.
        
        Args:
            title: Slide title
            stats: List of dicts with 'value' (e.g., "85%") and 'label' (e.g., "Market Share")
            notes: Optional speaker notes
        """
        slide_layout = self.prs.slide_layouts[6]  # Blank layout
        slide = self.prs.slides.add_slide(slide_layout)
        
        self._apply_background(slide)
        
        # Add title at top
        title_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(0.3),
            Inches(9), Inches(0.8)
        )
        tf = title_box.text_frame
        tf.text = title
        for paragraph in tf.paragraphs:
            paragraph.font.size = Pt(32)
            paragraph.font.bold = True
            if hasattr(self, 'current_style'):
                paragraph.font.color.rgb = self.current_style["title_color"]
                paragraph.font.name = self.current_style["font_name"]
        
        # Calculate positions for stats (distribute evenly)
        num_stats = min(len(stats), 4)  # Max 4 stats
        if num_stats == 0:
            return
            
        spacing = 9 / num_stats
        start_x = 0.5 + (spacing - 2) / 2  # Center each stat box
        
        for i, stat in enumerate(stats[:4]):
            x_pos = start_x + (i * spacing)
            
            # Large number
            value_box = slide.shapes.add_textbox(
                Inches(x_pos), Inches(2.5),
                Inches(2), Inches(1.5)
            )
            tf = value_box.text_frame
            tf.text = stat.get("value", "N/A")
            for paragraph in tf.paragraphs:
                paragraph.font.size = Pt(54)
                paragraph.font.bold = True
                if hasattr(self, 'current_style'):
                    paragraph.font.color.rgb = self.current_style["accent_color"]
                    paragraph.font.name = self.current_style["font_name"]
            
            # Label below
            label_box = slide.shapes.add_textbox(
                Inches(x_pos), Inches(4.2),
                Inches(2), Inches(0.8)
            )
            tf = label_box.text_frame
            tf.text = stat.get("label", "")
            tf.word_wrap = True
            for paragraph in tf.paragraphs:
                paragraph.font.size = Pt(16)
                if hasattr(self, 'current_style'):
                    paragraph.font.color.rgb = self.current_style["text_color"]
                    paragraph.font.name = self.current_style["font_name"]
        
        # Add notes
        if notes:
            notes_slide = slide.notes_slide
            text_frame = notes_slide.notes_text_frame
            text_frame.text = notes
        
        logger.info(f"Added statistics slide: {title} with {num_stats} stats")
            
    def save(self, output_path: str) -> None:
        """Save the presentation to a file."""
        self.prs.save(output_path)
        logger.info(f"Saved presentation to {output_path}")

