from pydantic import BaseModel, Field
from typing import List, Optional

class SlideConfig(BaseModel):
    title: str = Field(description="The main title of the slide")
    bullets: List[str] = Field(description="List of 3-5 bullet points")
    image_query: Optional[str] = Field(None, description="A search query to find an image for this slide")
    speaker_notes: Optional[str] = Field(None, description="Speaker notes for this slide")
    citations: List[str] = Field(default_factory=list, description="List of source URLs used for this slide")

class PresentationSection(BaseModel):
    title: str = Field(description="Title of the section or chapter")
    slides: List[str] = Field(description="List of slide topics within this section")

class PresentationOutline(BaseModel):
    title: str = Field(description="Main title of the presentation")
    sections: List[PresentationSection] = Field(description="List of hierarchical sections/chapters")

class UserPresentation(BaseModel):
    title: str
    sections: List[PresentationSection]
