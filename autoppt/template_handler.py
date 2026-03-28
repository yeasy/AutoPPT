"""
Template handler for working with existing PowerPoint presentations.
"""
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

from pptx import Presentation
try:
    from markitdown import MarkItDown
    HAS_MARKITDOWN = True
except ImportError:
    HAS_MARKITDOWN = False

logger = logging.getLogger(__name__)

class TemplateHandler:
    """Handles loading and analysis of PowerPoint templates."""
    
    def __init__(self, template_path: str):
        """
        Initialize with a path to a PPTX template.
        """
        self.template_path = Path(template_path).resolve()
        if not self.template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")
            
        self.prs = Presentation(str(self.template_path))
        self.layouts = self._analyze_layouts()
        
    def _analyze_layouts(self) -> Dict[int, Dict[str, Any]]:
        """Analyze available slide layouts."""
        layouts: Dict[int, Dict[str, Any]] = {}
        flat_index = 0

        for i, slide_master in enumerate(self.prs.slide_masters):
            for j, layout in enumerate(slide_master.slide_layouts):
                layout_info = {
                    "index": j,
                    "master_index": i,
                    "name": layout.name,
                    "placeholders": [
                        {
                            "idx": ph.placeholder_format.idx,
                            "type": str(ph.placeholder_format.type),
                            "name": ph.name
                        }
                        for ph in layout.placeholders
                    ]
                }
                layouts[flat_index] = layout_info
                flat_index += 1
                
        return layouts
    
    def extract_text_content(self) -> str:
        """Extract text content from the template using MarkItDown."""
        if not HAS_MARKITDOWN:
            logger.warning("markitdown not installed, cannot extract text content")
            return ""
            
        try:
            md = MarkItDown()
            result = md.convert(str(self.template_path))
            return str(result.text_content)
        except Exception as e:
            logger.error("Failed to extract text from template: %s", e)
            return ""

    def get_layout_by_name(self, name_pattern: str) -> int | None:
        """Find a layout index by name matching."""
        name_pattern = name_pattern.lower()
        for idx, info in self.layouts.items():
            if name_pattern in info["name"].lower():
                return idx
        return None
        
    def get_best_layout_for_type(self, slide_type: str) -> int:
        """
        Get the best layout index for a given slide type.
        """
        # Common PowerPoint layout names
        mappings = {
            "title": ["title slide", "intro"],
            "section": ["section header", "segue"],
            "content": ["title and content", "content"],
            "two_column": ["two content", "comparison"],
            "blank": ["blank"],
            "picture": ["picture", "image"]
        }
        
        patterns = mappings.get(slide_type, [])
        for pattern in patterns:
            idx = self.get_layout_by_name(pattern)
            if idx is not None:
                return idx
                
        # Fallback to first non-title layout for content
        if slide_type == "content":
            return 1 if 1 in self.layouts else 0
            
        return 0
