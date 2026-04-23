from __future__ import annotations

import logging
import re

from .themes import get_theme_names

logger = logging.getLogger(__name__)

DEFAULT_STYLE = "minimalist"
ALL_STYLES = get_theme_names()

STYLE_DESCRIPTIONS = {
    "minimalist": "Clean grayscale, professional",
    "technology": "Dark blue with gradient, tech-focused",
    "nature": "Earthy greens, organic feel",
    "creative": "Vibrant colors, artistic",
    "corporate": "Professional blue, business-ready",
    "academic": "Traditional maroon, scholarly",
    "startup": "Modern orange, energetic",
    "dark": "Cyan on dark with gradient, modern",
    "luxury": "Gold on dark, elegant premium",
    "magazine": "Crimson accents, editorial style",
    "tech_gradient": "Indigo to purple gradient",
    "ocean": "Deep blue gradient, calming",
    "sunset": "Warm orange to pink gradient",
    "chalkboard": "Black chalkboard, chalk texture, educational",
    "blueprint": "Technical schematics, grid texture, architectural",
    "sketch": "Hand-drawn style, warm and friendly",
    "retro": "Vintage colors, nostalgic feel",
    "neon": "Glowing accents, vibrant nightlife feel",
}

STYLE_KEYWORDS = {
    "chalkboard": [
        "classroom", "teaching", "school", "chalkboard", "blackboard",
        "lecture", "lesson", "课堂", "教学", "学校", "黑板",
    ],
    "sketch": [
        "tutorial", "learn", "education", "guide", "intro", "beginner",
        "howto", "how-to", "step by step", "教程", "学习", "入门", "指南",
    ],
    "blueprint": [
        "architecture", "system", "infrastructure", "schema", "design pattern",
        "database", "network", "devops", "架构", "系统设计", "基础设施",
    ],
    "technology": [
        "ai", "artificial intelligence", "machine learning", "software",
        "programming", "coding", "data", "cloud", "api", "algorithm",
        "人工智能", "机器学习", "软件", "编程", "数据", "云计算",
    ],
    "corporate": [
        "investor", "quarterly", "business", "proposal", "finance",
        "revenue", "market", "strategy", "投资", "商业", "财务", "战略",
    ],
    "startup": [
        "startup", "launch", "mvp", "growth", "funding", "pitch",
        "venture", "entrepreneur", "创业", "融资", "增长",
    ],
    "academic": [
        "research", "study", "paper", "thesis", "university", "science",
        "experiment", "hypothesis", "研究", "论文", "大学", "科学",
    ],
    "creative": [
        "art", "design", "creative", "illustration", "animation",
        "artistic", "visual", "艺术", "设计", "创意", "插画",
    ],
    "neon": [
        "entertainment", "music", "gaming", "game", "esports", "party",
        "nightlife", "娱乐", "音乐", "游戏", "电竞",
    ],
    "retro": [
        "history", "heritage", "vintage", "historical", "past", "era",
        "tradition", "classic", "历史", "传统", "经典", "复古",
    ],
    "nature": [
        "environment", "green", "eco", "climate", "sustainability",
        "nature", "wildlife", "plant", "环境", "绿色", "气候", "自然",
    ],
    "dark": [
        "dark mode", "night", "atmospheric", "cinematic",
        "深色", "夜间", "电影级",
    ],
    "luxury": [
        "luxury", "premium", "exclusive", "high-end", "elegant",
        "奢华", "高端", "尊贵",
    ],
    "magazine": [
        "magazine", "editorial", "journalism", "media", "press",
        "杂志", "编辑", "媒体",
    ],
    "tech_gradient": [
        "saas", "platform", "devtools", "developer tools", "api platform",
        "saas平台", "开发者工具",
    ],
    "ocean": [
        "ocean", "marine", "maritime", "shipping", "sea", "aquatic",
        "海洋", "航海", "水产",
    ],
    "sunset": [
        "wellness", "mindfulness", "yoga", "meditation", "lifestyle",
        "健康", "冥想", "瑜伽", "生活方式",
    ],
}


if __debug__:
    _theme_names = set(get_theme_names())
    _desc_names = set(STYLE_DESCRIPTIONS.keys())
    _kw_names = set(STYLE_KEYWORDS.keys()) | {DEFAULT_STYLE}
    assert _desc_names == _theme_names, f"STYLE_DESCRIPTIONS out of sync with THEME_DEFINITIONS: {_desc_names ^ _theme_names}"
    assert _kw_names == _theme_names, f"STYLE_KEYWORDS out of sync with THEME_DEFINITIONS: {_kw_names ^ _theme_names}"
    del _theme_names, _desc_names, _kw_names


def auto_select_style(topic: str, language: str = "English") -> str:
    if not topic:
        return DEFAULT_STYLE

    topic_lower = topic.lower()
    style_scores: dict[str, int] = {}

    for style, keywords in STYLE_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if any(ord(char) > 127 for char in keyword):
                if keyword_lower in topic_lower:
                    score += 1
            else:
                pattern = r"\b" + re.escape(keyword_lower) + r"\b"
                if re.search(pattern, topic_lower):
                    score += 1
        if score > 0:
            style_scores[style] = score

    if not style_scores:
        logger.info("No keyword match for topic '%s', using default style: %s", topic, DEFAULT_STYLE)
        return DEFAULT_STYLE

    best_style = max(style_scores, key=lambda candidate: style_scores[candidate])
    logger.info("Auto-selected style '%s' for topic '%s' (score: %s)", best_style, topic, style_scores[best_style])
    return best_style


def get_style_description(style: str) -> str:
    return STYLE_DESCRIPTIONS.get(style, "Custom style")


def get_all_styles() -> list[str]:
    return list(ALL_STYLES)
