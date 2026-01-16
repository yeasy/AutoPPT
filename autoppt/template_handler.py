"""
Template handler for working with existing PowerPoint presentations.
"""
import logging
import json
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
        
    def _analyze_layouts(self) -> Dict[str, Any]:
        """Analyze available slide layouts."""
        layouts = {}
        
        # Analyze slide masters
        for i, slide_master in enumerate(self.prs.slide_masters):
            # Analyze layouts within master
            for j, layout in enumerate(slide_master.slide_layouts):
                # Try to determine layout type based on placeholders
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
                
                # key by index but also keep map logic
                layouts[j] = layout_info
                
        return layouts
    
    def extract_text_content(self) -> str:
        """Extract text content from the template using MarkItDown."""
        if not HAS_MARKITDOWN:
            logger.warning("markitdown not installed, cannot extract text content")
            return ""
            
        try:
            md = MarkItDown()
            result = md.convert(str(self.template_path))
            return result.text_content
        except Exception as e:
            logger.error(f"Failed to extract text from template: {e}")
            return ""

    def get_layout_by_name(self, name_pattern: str) -> Optional[int]:
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
            "section": ["section header", "segway"],
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
