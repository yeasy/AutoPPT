from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from .data_types import UserPresentation, SlideConfig

class PPTRenderer:
    def __init__(self, template_path: str = None):
        if template_path:
            self.prs = Presentation(template_path)
        else:
            self.prs = Presentation()
            
    def add_title_slide(self, title: str, subtitle: str = ""):
        slide_layout = self.prs.slide_layouts[0] # 0 is usually Title Slide
        slide = self.prs.slides.add_slide(slide_layout)
        
        title_shape = slide.shapes.title
        subtitle_shape = slide.placeholders[1]
        
        title_shape.text = title
        subtitle_shape.text = subtitle
        
    def add_content_slide(self, title: str, bullets: list, notes: str = ""):
        slide_layout = self.prs.slide_layouts[1] # 1 is usually Title and Content
        slide = self.prs.slides.add_slide(slide_layout)
        
        # Title
        title_shape = slide.shapes.title
        title_shape.text = title
        
        # Content (Bullets)
        body_shape = slide.placeholders[1]
        tf = body_shape.text_frame
        tf.word_wrap = True
        
        # Clear existing paragraphs
        tf.clear() 
        
        for bullet in bullets:
            p = tf.add_paragraph()
            p.text = bullet
            p.level = 0
            
        # Add Notes
        if notes:
            notes_slide = slide.notes_slide
            text_frame = notes_slide.notes_text_frame
            text_frame.text = notes
            
    def add_citations_slide(self, citations: list):
        if not citations:
            return
            
        slide_layout = self.prs.slide_layouts[1]
        slide = self.prs.slides.add_slide(slide_layout)
        
        title_shape = slide.shapes.title
        title_shape.text = "References"
        
        body_shape = slide.placeholders[1]
        tf = body_shape.text_frame
        tf.clear()
        
        for cit in citations:
            p = tf.add_paragraph()
            p.text = cit
            p.font.size = Pt(12)
            
    def save(self, output_path: str):
        self.prs.save(output_path)
