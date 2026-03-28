from dataclasses import dataclass
import logging
import math
from pathlib import Path
import tempfile
import textwrap
from typing import Any

logger = logging.getLogger(__name__)

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from .data_types import ChartData, ChartType, DeckSpec, SlideLayout, SlideSpec, StatisticData
from .generator import Generator
from .thumbnail import check_dependencies, convert_pdf_to_images, convert_to_pdf


@dataclass(frozen=True)
class SampleDefinition:
    sample_id: str
    filename: str
    category: str
    title: str
    topic: str
    language: str
    style: str
    description: str


def _title(title: str, subtitle: str) -> SlideSpec:
    return SlideSpec(layout=SlideLayout.TITLE, title=title, subtitle=subtitle)


def _section(title: str) -> SlideSpec:
    return SlideSpec(layout=SlideLayout.SECTION, title=title)


def _content(title: str, bullets: list[str], notes: str = "", citations: list[str] | None = None) -> SlideSpec:
    return SlideSpec(
        layout=SlideLayout.CONTENT,
        title=title,
        bullets=bullets,
        speaker_notes=notes,
        citations=citations or [],
    )


def _two_column(
    title: str,
    left_title: str,
    right_title: str,
    left_bullets: list[str],
    right_bullets: list[str],
    notes: str = "",
    citations: list[str] | None = None,
) -> SlideSpec:
    return SlideSpec(
        layout=SlideLayout.TWO_COLUMN,
        title=title,
        left_title=left_title,
        right_title=right_title,
        left_bullets=left_bullets,
        right_bullets=right_bullets,
        speaker_notes=notes,
        citations=citations or [],
    )


def _comparison(
    title: str,
    left_title: str,
    right_title: str,
    left_bullets: list[str],
    right_bullets: list[str],
    notes: str = "",
    citations: list[str] | None = None,
) -> SlideSpec:
    return SlideSpec(
        layout=SlideLayout.COMPARISON,
        title=title,
        left_title=left_title,
        right_title=right_title,
        left_bullets=left_bullets,
        right_bullets=right_bullets,
        speaker_notes=notes,
        citations=citations or [],
    )


def _quote(
    title: str,
    quote_text: str,
    quote_author: str,
    quote_context: str,
    notes: str = "",
    citations: list[str] | None = None,
) -> SlideSpec:
    return SlideSpec(
        layout=SlideLayout.QUOTE,
        title=title,
        quote_text=quote_text,
        quote_author=quote_author,
        quote_context=quote_context,
        speaker_notes=notes,
        citations=citations or [],
    )


def _statistics(title: str, stats: list[tuple[str, str]], notes: str = "", citations: list[str] | None = None) -> SlideSpec:
    return SlideSpec(
        layout=SlideLayout.STATISTICS,
        title=title,
        statistics=[StatisticData(value=value, label=label) for value, label in stats],
        speaker_notes=notes,
        citations=citations or [],
    )


def _chart(
    title: str,
    chart_title: str,
    categories: list[str],
    values: list[float],
    chart_type: ChartType = ChartType.COLUMN,
    notes: str = "",
    citations: list[str] | None = None,
) -> SlideSpec:
    return SlideSpec(
        layout=SlideLayout.CHART,
        title=title,
        chart_data=ChartData(
            chart_type=chart_type,
            title=chart_title,
            categories=categories,
            values=values,
            series_name=chart_title,
        ),
        speaker_notes=notes,
        citations=citations or [],
    )


def _image(title: str, image_path: str, caption: str = "", citations: list[str] | None = None) -> SlideSpec:
    return SlideSpec(
        layout=SlideLayout.IMAGE,
        title=title,
        image_path=image_path,
        image_caption=caption,
        citations=citations or [],
    )


def _content_with_image(
    title: str,
    bullets: list[str],
    image_path: str,
    notes: str = "",
    citations: list[str] | None = None,
) -> SlideSpec:
    return SlideSpec(
        layout=SlideLayout.CONTENT,
        title=title,
        bullets=bullets,
        image_path=image_path,
        speaker_notes=notes,
        citations=citations or [],
    )


def _gradient_image(size: tuple[int, int], start: tuple[int, int, int], end: tuple[int, int, int]) -> Image.Image:
    width, height = size
    image = Image.new("RGB", size, start)
    draw = ImageDraw.Draw(image)
    for y in range(height):
        blend = y / max(height - 1, 1)
        color = tuple(int(start[index] * (1 - blend) + end[index] * blend) for index in range(3))
        draw.line((0, y, width, y), fill=color)
    return image


def _build_visual_asset(asset_dir: Path, name: str, palette: dict[str, Any], motif: str) -> str:
    asset_dir.mkdir(parents=True, exist_ok=True)
    output_path = asset_dir / f"{name}.png"
    image = _gradient_image((1600, 900), palette["start"], palette["end"]).convert("RGBA")

    glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    for ellipse in palette["ellipses"]:
        x0, y0, x1, y1, alpha = ellipse
        glow_draw.ellipse((x0, y0, x1, y1), fill=palette["accent"] + (alpha,))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=35))
    image = Image.alpha_composite(image, glow)

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    if motif == "grid":
        for x in range(0, image.size[0], 120):
            overlay_draw.line((x, 0, x, image.size[1]), fill=palette["line"] + (60,), width=2)
        for y in range(0, image.size[1], 120):
            overlay_draw.line((0, y, image.size[0], y), fill=palette["line"] + (40,), width=2)
    elif motif == "waves":
        for offset in range(0, 6):
            points = []
            for x in range(0, image.size[0] + 40, 40):
                y = 560 + int(55 * math.sin((x / 180) + offset))
                points.append((x, y + offset * 26))
            overlay_draw.line(points, fill=palette["line"] + (110,), width=6)
    elif motif == "frames":
        for inset in (80, 150, 220):
            overlay_draw.rounded_rectangle(
                (inset, inset, image.size[0] - inset, image.size[1] - inset),
                radius=28,
                outline=palette["line"] + (120,),
                width=5,
            )
    image = Image.alpha_composite(image, overlay).convert("RGB")
    image.save(output_path, format="PNG")
    return str(output_path)


def _load_font(candidates: list[str], size: int):
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _cover_image(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    target_w, target_h = size
    src_w, src_h = image.size
    scale = max(target_w / src_w, target_h / src_h)
    resized = image.resize((int(src_w * scale), int(src_h * scale)), Image.Resampling.LANCZOS)
    left = max((resized.width - target_w) // 2, 0)
    top = max((resized.height - target_h) // 2, 0)
    return resized.crop((left, top, left + target_w, top + target_h))


def _theme_palette(style: str) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]:
    palettes = {
        "technology": ((16, 26, 62), (20, 92, 168), (118, 220, 255)),
        "nature": ((19, 61, 42), (68, 138, 84), (201, 255, 210)),
        "creative": ((88, 26, 46), (201, 90, 94), (255, 224, 184)),
        "dark": ((12, 18, 42), (28, 60, 122), (120, 224, 255)),
        "corporate": ((24, 52, 98), (69, 119, 202), (208, 232, 255)),
        "startup": ((108, 56, 12), (244, 138, 35), (255, 233, 187)),
    }
    start, end, accent = palettes.get(style, ((40, 46, 60), (98, 112, 140), (225, 232, 244)))
    return start, end, accent


def _build_card_background(deck: DeckSpec, size: tuple[int, int]) -> Image.Image:
    for slide in deck.slides:
        if slide.image_path and Path(slide.image_path).exists():
            with Image.open(slide.image_path) as image:
                return _cover_image(image.convert("RGB"), size)

    start, end, accent = _theme_palette(deck.style)
    background = _gradient_image(size, start, end).convert("RGBA")

    glow = Image.new("RGBA", size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse((60, 40, 380, 360), fill=accent + (110,))
    glow_draw.ellipse((size[0] - 320, size[1] - 280, size[0] + 40, size[1] + 20), fill=accent + (70,))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=30))
    background = Image.alpha_composite(background, glow)
    return background.convert("RGB")


def _get_card_lines(deck: DeckSpec) -> list[str]:
    for slide in deck.slides:
        if slide.bullets:
            return slide.bullets[:3]
        if slide.left_bullets or slide.right_bullets:
            return (slide.left_bullets or [])[:2] + (slide.right_bullets or [])[:1]
        if slide.quote_text:
            return [slide.quote_text]
    return [deck.topic]


def _draw_showcase_card(
    definition: SampleDefinition,
    deck: DeckSpec,
    card_size: tuple[int, int],
    locale: str,
) -> Image.Image:
    width, height = card_size
    card = Image.new("RGBA", card_size, (0, 0, 0, 0))
    background = _build_card_background(deck, card_size).convert("RGBA")

    mask = Image.new("L", card_size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, width, height), radius=34, fill=255)
    card.paste(background, (0, 0), mask)

    overlay = Image.new("RGBA", card_size, (8, 12, 18, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rounded_rectangle((0, 0, width, height), radius=34, fill=(8, 12, 18, 120))
    overlay_draw.rounded_rectangle((24, 24, 190, 66), radius=18, fill=(255, 255, 255, 42))
    overlay_draw.rounded_rectangle((24, 86, width - 24, height - 24), radius=24, fill=(6, 10, 18, 132))
    card = Image.alpha_composite(card, overlay)
    draw = ImageDraw.Draw(card)

    title_font = _load_font(
        ["/System/Library/Fonts/Supplemental/Avenir Next Demi Bold.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"],
        34,
    )
    body_font = _load_font(
        ["/System/Library/Fonts/Supplemental/Avenir Next.ttc", "/System/Library/Fonts/Supplemental/Arial.ttf"],
        20,
    )
    caption_font = _load_font(
        ["/System/Library/Fonts/Supplemental/Avenir Next.ttc", "/System/Library/Fonts/Supplemental/Arial.ttf"],
        17,
    )
    if locale == "zh":
        title_font = _load_font(
            ["/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/Supplemental/STHeiti Light.ttc"],
            34,
        )
        body_font = _load_font(
            ["/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/Supplemental/STHeiti Light.ttc"],
            20,
        )
        caption_font = _load_font(
            ["/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/Supplemental/STHeiti Light.ttc"],
            17,
        )

    accent = _theme_palette(deck.style)[2]
    label = f"{len(deck.slides)} slides" if locale == "en" else f"{len(deck.slides)} 页"
    draw.text((42, 36), label, fill=(245, 249, 255), font=caption_font)
    draw.text((42, 108), definition.title, fill=(255, 255, 255), font=title_font)

    subtitle = (deck.slides[0].subtitle if deck.slides else None) or definition.description
    subtitle_lines = textwrap.wrap(subtitle, width=30 if locale == "en" else 16)[:2]
    y = 156
    for line in subtitle_lines:
        draw.text((42, y), line, fill=(215, 225, 238), font=body_font)
        y += 28

    draw.rounded_rectangle((42, y + 8, 174, y + 42), radius=15, fill=accent + (255,))
    draw.text((58, y + 14), deck.style, fill=(12, 18, 28), font=caption_font)
    y += 68

    for bullet in _get_card_lines(deck):
        wrapped = textwrap.wrap(bullet, width=34 if locale == "en" else 18)[:2]
        draw.ellipse((42, y + 8, 54, y + 20), fill=accent + (255,))
        line_y = y
        for index, line in enumerate(wrapped):
            x = 68
            draw.text((x, line_y), line, fill=(241, 245, 250), font=body_font)
            line_y += 25
        y = line_y + 12
        if y > height - 90:
            break

    border = Image.new("RGBA", card_size, (0, 0, 0, 0))
    border_draw = ImageDraw.Draw(border)
    border_draw.rounded_rectangle((1, 1, width - 2, height - 2), radius=34, outline=(255, 255, 255, 90), width=2)
    card = Image.alpha_composite(card, border)
    return card


def _draw_real_preview_card(
    definition: SampleDefinition,
    deck: DeckSpec,
    preview_path: Path,
    card_size: tuple[int, int],
    locale: str,
) -> Image.Image:
    with Image.open(preview_path) as image:
        preview = _cover_image(image.convert("RGB"), card_size).convert("RGBA")

    mask = Image.new("L", card_size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, card_size[0], card_size[1]), radius=34, fill=255)

    card = Image.new("RGBA", card_size, (0, 0, 0, 0))
    card.paste(preview, (0, 0), mask)

    overlay = Image.new("RGBA", card_size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rounded_rectangle((0, 0, card_size[0], card_size[1]), radius=34, fill=(8, 12, 18, 54))
    overlay_draw.rounded_rectangle((24, card_size[1] - 170, card_size[0] - 24, card_size[1] - 24), radius=22, fill=(8, 12, 18, 172))
    overlay_draw.rounded_rectangle((24, 24, 172, 64), radius=18, fill=(255, 255, 255, 42))
    card = Image.alpha_composite(card, overlay)

    draw = ImageDraw.Draw(card)
    title_font = _load_font(
        ["/System/Library/Fonts/Supplemental/Avenir Next Demi Bold.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"],
        27,
    )
    body_font = _load_font(
        ["/System/Library/Fonts/Supplemental/Avenir Next.ttc", "/System/Library/Fonts/Supplemental/Arial.ttf"],
        16,
    )
    if locale == "zh":
        title_font = _load_font(
            ["/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/Supplemental/STHeiti Light.ttc"],
            27,
        )
        body_font = _load_font(
            ["/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/Supplemental/STHeiti Light.ttc"],
            16,
        )

    label = f"{len(deck.slides)} slides" if locale == "en" else f"{len(deck.slides)} 页"
    draw.text((42, 34), label, fill=(245, 249, 255), font=body_font)
    draw.text((42, card_size[1] - 144), definition.title, fill=(255, 255, 255), font=title_font)
    subtitle = (deck.slides[0].subtitle if deck.slides else None) or definition.description
    subtitle_lines = textwrap.wrap(subtitle, width=28 if locale == "en" else 14)[:2]
    y = card_size[1] - 102
    for line in subtitle_lines:
        draw.text((42, y), line, fill=(218, 228, 239), font=body_font)
        y += 22

    border = Image.new("RGBA", card_size, (0, 0, 0, 0))
    border_draw = ImageDraw.Draw(border)
    border_draw.rounded_rectangle((1, 1, card_size[0] - 2, card_size[1] - 2), radius=34, outline=(255, 255, 255, 90), width=2)
    card = Image.alpha_composite(card, border)
    return card


def _real_preview_image_for_sample(sample_id: str, deck: DeckSpec) -> Path | None:
    deps_ok, _missing = check_dependencies()
    if not deps_ok:
        return None

    with tempfile.TemporaryDirectory(prefix=f"autoppt-real-preview-{sample_id}-") as temp_dir:
        temp_root = Path(temp_dir)
        pptx_path = render_sample(sample_id, temp_root)
        pdf_path = convert_to_pdf(pptx_path, temp_root)
        if not pdf_path:
            return None
        images = convert_pdf_to_images(pdf_path, temp_root)
        if not images:
            return None
        preview_path = temp_root / f"{sample_id}-preview.jpg"
        with Image.open(images[0]) as image:
            image.convert("RGB").save(preview_path, format="JPEG", quality=92)
        final_path = Path(tempfile.mkdtemp(prefix=f"autoppt-real-preview-cache-{sample_id}-")) / preview_path.name
        final_path.parent.mkdir(parents=True, exist_ok=True)
        preview_path.replace(final_path)
        return final_path


def render_readme_showcase_previews(output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    manifests = {
        "showcase-preview-en.png": {
            "locale": "en",
            "title": "Showcase Samples",
            "subtitle": "Native PPTX decks for tech, art, lifestyle, and image-led storytelling",
            "sample_ids": ["en_visual_showcase", "en_tech", "en_art"],
        },
        "showcase-preview-zh-CN.png": {
            "locale": "zh",
            "title": "Showcase 样例",
            "subtitle": "原生 PPTX 输出，覆盖高保真视觉页、科技主题和艺术主题",
            "sample_ids": ["cn_visual_showcase", "cn_tech", "cn_art"],
        },
    }

    created: list[Path] = []
    for filename, config in manifests.items():
        canvas = Image.new("RGB", (1800, 980), color=(8, 12, 22))
        canvas = _gradient_image(canvas.size, (10, 16, 28), (24, 40, 70))
        canvas = canvas.convert("RGBA")

        glow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow)
        glow_draw.ellipse((60, 80, 520, 480), fill=(60, 160, 255, 92))
        glow_draw.ellipse((1240, 40, 1770, 560), fill=(255, 120, 180, 76))
        glow_draw.ellipse((1120, 560, 1760, 1020), fill=(92, 255, 206, 62))
        glow = glow.filter(ImageFilter.GaussianBlur(radius=50))
        canvas = Image.alpha_composite(canvas, glow)
        draw = ImageDraw.Draw(canvas)

        locale: str = config["locale"]  # type: ignore[assignment]
        title_font = _load_font(
            ["/System/Library/Fonts/Supplemental/Avenir Next Demi Bold.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"],
            54,
        )
        subtitle_font = _load_font(
            ["/System/Library/Fonts/Supplemental/Avenir Next.ttc", "/System/Library/Fonts/Supplemental/Arial.ttf"],
            24,
        )
        if locale == "zh":
            title_font = _load_font(
                ["/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/Supplemental/STHeiti Light.ttc"],
                54,
            )
            subtitle_font = _load_font(
                ["/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/Supplemental/STHeiti Light.ttc"],
                24,
            )

        title_text: str = config["title"]  # type: ignore[assignment]
        subtitle_text: str = config["subtitle"]  # type: ignore[assignment]
        draw.text((96, 72), title_text, fill=(255, 255, 255), font=title_font)
        for index, line in enumerate(textwrap.wrap(subtitle_text, width=68 if locale == "en" else 28)):
            draw.text((96, 144 + index * 30), line, fill=(216, 226, 238), font=subtitle_font)

        preview_cache: list[Path] = []
        with tempfile.TemporaryDirectory(prefix="autoppt-readme-preview-") as asset_dir:
            cards = []
            for sample_id in config["sample_ids"]:
                definition = get_sample_definition(sample_id)
                deck = build_sample_deck(sample_id, asset_dir=asset_dir)
                preview_path = _real_preview_image_for_sample(sample_id, deck)
                if preview_path:
                    preview_cache.append(preview_path)
                    cards.append(_draw_real_preview_card(definition, deck, preview_path, (500, 650), locale))
                else:
                    cards.append(_draw_showcase_card(definition, deck, (500, 650), locale))

            x_positions = [96, 648, 1200]
            for x, card in zip(x_positions, cards):
                canvas.paste(card, (x, 264), card)

        for preview in preview_cache:
            try:
                preview.unlink()
                preview.parent.rmdir()
            except OSError:
                pass

        output_path = output_root / filename
        canvas.convert("RGB").save(output_path, format="PNG")
        created.append(output_path)

    return created


SAMPLE_DEFINITIONS: tuple[SampleDefinition, ...] = (
    SampleDefinition("cn_tech", "cn_tech.pptx", "showcase", "人工智能与未来科技", "人工智能与未来科技", "Chinese", "tech_gradient", "中文科技展示样例"),
    SampleDefinition("cn_life", "cn_life.pptx", "showcase", "健康生活方式", "健康生活方式", "Chinese", "ocean", "中文生活方式展示样例"),
    SampleDefinition("cn_art", "cn_art.pptx", "showcase", "文艺复兴艺术", "文艺复兴艺术", "Chinese", "luxury", "中文艺术展示样例"),
    SampleDefinition("cn_visual_showcase", "cn_visual_showcase.pptx", "showcase", "视觉型展示样例", "视觉型展示样例", "Chinese", "dark", "中文高保真图片型展示样例"),
    SampleDefinition("en_tech", "en_tech.pptx", "showcase", "Artificial Intelligence and Future Technology", "Artificial Intelligence and Future Technology", "English", "tech_gradient", "English technology showcase"),
    SampleDefinition("en_life", "en_life.pptx", "showcase", "Healthy Living Lifestyle", "Healthy Living Lifestyle", "English", "sunset", "English healthy living showcase"),
    SampleDefinition("en_art", "en_art.pptx", "showcase", "Renaissance Art", "Renaissance Art", "English", "magazine", "English art showcase"),
    SampleDefinition("en_visual_showcase", "en_visual_showcase.pptx", "showcase", "Visual Showcase Sample", "Visual Showcase Sample", "English", "dark", "High-fidelity image-heavy showcase sample"),
    SampleDefinition("feature_layouts_en", "feature_layouts_en.pptx", "feature", "Layout Gallery", "Layout Gallery", "English", "corporate", "Feature sample for richer layouts"),
    SampleDefinition("feature_layouts_cn", "feature_layouts_cn.pptx", "feature", "版式画廊", "版式画廊", "Chinese", "startup", "功能样例，展示 richer layouts"),
    SampleDefinition("feature_workbench", "feature_workbench.pptx", "feature", "Slide Workbench Flow", "Slide Workbench Flow", "English", "minimalist", "Feature sample for regenerate and remix workflow"),
)


def get_sample_definitions(category: str = "all") -> list[SampleDefinition]:
    if category == "all":
        return list(SAMPLE_DEFINITIONS)
    return [sample for sample in SAMPLE_DEFINITIONS if sample.category == category]


def get_sample_definition(sample_id: str) -> SampleDefinition:
    for sample in SAMPLE_DEFINITIONS:
        if sample.sample_id == sample_id:
            return sample
    raise KeyError(f"Unknown sample id: {sample_id}")


def build_sample_deck(sample_id: str, asset_dir: str | Path | None = None) -> DeckSpec:
    """Build a sample deck spec.

    When *asset_dir* is ``None`` a temporary directory is created and the caller
    is responsible for cleaning it up after the returned ``DeckSpec`` is no
    longer needed.  Prefer passing an explicit directory managed via
    ``tempfile.TemporaryDirectory`` to avoid leaks.
    """
    definition = get_sample_definition(sample_id)
    builder = _SAMPLE_BUILDERS[sample_id]
    if asset_dir is None:
        asset_dir = Path(tempfile.mkdtemp(prefix=f"autoppt-sample-assets-{sample_id}-"))
        logger.warning("build_sample_deck created temp asset dir %s; caller must clean up", asset_dir)
    return builder(definition, Path(asset_dir))


def render_sample(sample_id: str, output_dir: str | Path) -> Path:
    definition = get_sample_definition(sample_id)
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    output_path = output_root / definition.filename
    with tempfile.TemporaryDirectory(prefix=f"autoppt-sample-assets-{sample_id}-") as asset_dir:
        deck = build_sample_deck(sample_id, asset_dir=asset_dir)
        generator = Generator(provider_name="mock")
        try:
            generator.save_deck(deck, str(output_path))
        finally:
            generator.close()
    return output_path


def _base_deck(definition: SampleDefinition, slides: list[SlideSpec]) -> DeckSpec:
    return DeckSpec(
        title=definition.title,
        topic=definition.topic,
        style=definition.style,
        language=definition.language,
        slides=slides,
    )


def _build_cn_tech(definition: SampleDefinition, asset_dir: Path) -> DeckSpec:
    citations = ["https://www.mckinsey.com/capabilities/quantumblack/our-insights/the-state-of-ai", "https://www.nature.com/subjects/artificial-intelligence"]
    hero = _build_visual_asset(
        asset_dir,
        "cn_tech_hero",
        {
            "start": (10, 18, 58),
            "end": (56, 44, 142),
            "accent": (98, 232, 255),
            "line": (170, 220, 255),
            "ellipses": ((120, 80, 640, 560, 112), (900, 90, 1490, 710, 88), (480, 470, 1090, 930, 70)),
        },
        "grid",
    )
    detail = _build_visual_asset(
        asset_dir,
        "cn_tech_detail",
        {
            "start": (14, 26, 76),
            "end": (38, 102, 184),
            "accent": (100, 255, 228),
            "line": (188, 242, 255),
            "ellipses": ((80, 140, 560, 700, 96), (960, 110, 1440, 670, 82), (580, 540, 1220, 920, 66)),
        },
        "frames",
    )
    return _base_deck(
        definition,
        [
            _title("人工智能与未来科技", "从模型能力到可运营系统"),
            _image("平台化时代的 AI 界面", hero, "高保真视觉页，强调未来感与系统规模", citations=citations),
            _statistics("平台化速度", [("78%", "团队已试点"), ("3x", "成熟团队交付速度"), ("24 个月", "重构窗口")], citations=citations),
            _content_with_image(
                "真正变化的不是模型，而是工作流",
                [
                    "模型正在变成默认界面。",
                    "评测与路由进入主链路。",
                    "治理比参数更先决定 ROI。",
                ],
                image_path=detail,
                citations=citations,
            ),
            _comparison(
                "局部工具 vs 平台能力",
                "局部工具",
                "平台能力",
                ["单点提效", "接口重复", "质量波动大"],
                ["统一路由", "共享知识层", "上线成本更低"],
                citations=citations,
            ),
            _chart("模型能力曲线", "Capability Index", ["2023", "2024", "2025", "2026"], [42, 58, 71, 83], chart_type=ChartType.LINE, citations=citations),
            _two_column(
                "企业 AI 操作模型",
                "建设层",
                "控制层",
                ["模型与编排", "检索与工具", "反馈与评测"],
                ["风险分级", "预算护栏", "业务负责人"],
                citations=citations,
            ),
            _quote("战略提示", "真正的优势来自工作方式重构，而不只是把模型接进流程。", "AutoPPT Sample Desk", "AI Operating Model Notes", citations=citations),
        ],
    )


def _build_cn_life(definition: SampleDefinition, asset_dir: Path) -> DeckSpec:
    citations = ["https://www.who.int/news-room/fact-sheets/detail/physical-activity", "https://www.hsph.harvard.edu/nutritionsource/"]
    hero = _build_visual_asset(
        asset_dir,
        "cn_life_hero",
        {
            "start": (8, 84, 110),
            "end": (38, 146, 188),
            "accent": (192, 255, 232),
            "line": (215, 255, 247),
            "ellipses": ((90, 120, 570, 700, 98), (980, 100, 1460, 680, 82), (540, 520, 1120, 930, 62)),
        },
        "waves",
    )
    detail = _build_visual_asset(
        asset_dir,
        "cn_life_detail",
        {
            "start": (18, 96, 108),
            "end": (60, 160, 170),
            "accent": (255, 244, 188),
            "line": (255, 255, 232),
            "ellipses": ((120, 150, 620, 720, 92), (820, 130, 1450, 760, 76), (480, 520, 920, 920, 58)),
        },
        "frames",
    )
    return _base_deck(
        definition,
        [
            _title("健康生活方式", "稳定节律，比短期冲刺更有力量"),
            _image("清晨节律页", hero, "图片主导型 lifestyle 开场页", citations=citations),
            _content_with_image(
                "真正有效的是稳定的一天",
                [
                    "先让节律可重复。",
                    "再谈强度与目标。",
                    "环境设计比意志力更可靠。",
                ],
                image_path=detail,
                citations=citations,
            ),
            _statistics("基础目标", [("150 分钟", "每周运动"), ("7-9 小时", "推荐睡眠"), ("5 份", "每日蔬果")], citations=citations),
            _two_column(
                "一个可持续的日常系统",
                "晨间",
                "晚间",
                ["固定起床", "喝水再喝咖啡", "先活动再看消息"],
                ["晚饭提前", "降低强光", "固定收尾流程"],
                citations=citations,
            ),
            _image("恢复同样重要", detail, "留白、恢复和低刺激环境，决定这套系统能否持续", citations=citations),
            _quote("习惯原则", "小而稳的日常胜过偶尔完美的一天。", "AutoPPT Sample Desk", "Healthy Habits Brief", citations=citations),
        ],
    )


def _build_cn_art(definition: SampleDefinition, asset_dir: Path) -> DeckSpec:
    citations = ["https://www.uffizi.it/en/the-uffizi", "https://www.metmuseum.org/toah/hd/itar/hd_itar.htm"]
    hero = _build_visual_asset(
        asset_dir,
        "cn_art_hero",
        {
            "start": (36, 24, 22),
            "end": (118, 76, 40),
            "accent": (255, 216, 156),
            "line": (255, 242, 210),
            "ellipses": ((100, 120, 590, 640, 100), (920, 120, 1470, 760, 82), (440, 530, 940, 930, 60)),
        },
        "frames",
    )
    gallery = _build_visual_asset(
        asset_dir,
        "cn_art_gallery",
        {
            "start": (20, 18, 24),
            "end": (78, 44, 60),
            "accent": (212, 175, 55),
            "line": (255, 232, 188),
            "ellipses": ((120, 180, 540, 620, 90), (860, 120, 1480, 760, 76), (540, 560, 1040, 930, 54)),
        },
        "grid",
    )
    return _base_deck(
        definition,
        [
            _title("文艺复兴艺术", "一场关于空间、身体与权力的视觉重写"),
            _image("展陈式开场页", hero, "更适合艺术与文化主题的海报感开场", citations=citations),
            _quote("艺术评论", "透视法不只是绘画技巧，而是一种组织世界的新方式。", "AutoPPT Sample Desk", "Art History Notes", citations=citations),
            _content_with_image(
                "为什么它今天仍然现代",
                [
                    "空间开始有逻辑。",
                    "人物开始有重量。",
                    "观看开始带有立场。",
                ],
                image_path=gallery,
                citations=citations,
            ),
            _image("作品墙式图片页", gallery, "用整页图片维持观看节奏，而不是把每页都塞满说明", citations=citations),
            _comparison(
                "早期 vs 盛期文艺复兴",
                "早期",
                "盛期",
                ["结构实验", "透视成形", "情绪克制"],
                ["构图平衡", "身体成熟", "理想美成型"],
                citations=citations,
            ),
            _two_column(
                "如何读一幅作品",
                "形式线索",
                "文化线索",
                ["空间组织", "光影处理", "姿态比例"],
                ["赞助人", "宗教背景", "古典引用"],
                citations=citations,
            ),
        ],
    )


def _build_en_tech(definition: SampleDefinition, asset_dir: Path) -> DeckSpec:
    citations = ["https://www.mckinsey.com/capabilities/quantumblack/our-insights/the-state-of-ai", "https://openai.com/index/"]
    hero = _build_visual_asset(
        asset_dir,
        "en_tech_hero",
        {
            "start": (14, 18, 62),
            "end": (62, 40, 152),
            "accent": (92, 232, 255),
            "line": (182, 224, 255),
            "ellipses": ((110, 100, 620, 580, 110), (940, 90, 1490, 700, 88), (520, 500, 1120, 940, 70)),
        },
        "grid",
    )
    detail = _build_visual_asset(
        asset_dir,
        "en_tech_detail",
        {
            "start": (22, 32, 84),
            "end": (52, 118, 198),
            "accent": (110, 255, 222),
            "line": (208, 248, 255),
            "ellipses": ((90, 160, 590, 720, 96), (940, 120, 1460, 690, 82), (580, 520, 1200, 930, 66)),
        },
        "frames",
    )
    return _base_deck(
        definition,
        [
            _title("Artificial Intelligence and Future Technology", "From model capability to operating model"),
            _image("Platform-scale AI systems", hero, "High-fidelity hero slide for a launch-style technology deck", citations=citations),
            _statistics("Platform shift", [("72%", "Teams standardizing"), ("2.7x", "Faster delivery"), ("90 days", "Pilot to platform")], citations=citations),
            _content_with_image(
                "What changed in one year",
                [
                    "Models became the default UI.",
                    "Evaluation moved into the product loop.",
                    "Governance moved upstream.",
                ],
                image_path=detail,
                citations=citations,
            ),
            _comparison(
                "Point tools vs AI platform",
                "Point tools",
                "AI platform",
                ["Quick wins", "Repeated integration", "No shared QA"],
                ["Shared routing", "Reusable knowledge", "Lower rollout cost"],
                citations=citations,
            ),
            _chart("Capability index", "Capability Index", ["2023", "2024", "2025", "2026"], [40, 55, 70, 82], chart_type=ChartType.LINE, citations=citations),
            _two_column(
                "Execution stack",
                "Ship",
                "Control",
                ["Models and routing", "Retrieval and tools", "Feedback and evals"],
                ["Risk tiers", "Budget guardrails", "Workflow owners"],
                citations=citations,
            ),
            _quote("Operating principle", "The durable advantage comes from redesigning work, not merely adding models.", "AutoPPT Sample Desk", "Future Technology Brief", citations=citations),
        ],
    )


def _build_en_life(definition: SampleDefinition, asset_dir: Path) -> DeckSpec:
    citations = ["https://www.who.int/news-room/fact-sheets/detail/physical-activity", "https://www.cdc.gov/sleep/about/index.html"]
    hero = _build_visual_asset(
        asset_dir,
        "en_life_hero",
        {
            "start": (255, 124, 78),
            "end": (228, 76, 128),
            "accent": (255, 226, 160),
            "line": (255, 244, 214),
            "ellipses": ((90, 120, 560, 690, 96), (910, 80, 1480, 720, 84), (500, 520, 1120, 930, 62)),
        },
        "waves",
    )
    detail = _build_visual_asset(
        asset_dir,
        "en_life_detail",
        {
            "start": (255, 142, 96),
            "end": (242, 98, 156),
            "accent": (255, 241, 196),
            "line": (255, 246, 228),
            "ellipses": ((120, 150, 600, 740, 88), (830, 120, 1460, 760, 70), (520, 540, 960, 920, 56)),
        },
        "frames",
    )
    return _base_deck(
        definition,
        [
            _title("Healthy Living Lifestyle", "A calmer system for energy and resilience"),
            _image("Lifestyle cover slide", hero, "A softer, image-led opening for wellness storytelling", citations=citations),
            _content_with_image(
                "The steady-day rule",
                [
                    "Design for repeatability first.",
                    "Make recovery visible.",
                    "Let the environment do the work.",
                ],
                image_path=detail,
                citations=citations,
            ),
            _statistics("Baseline targets", [("150 min", "Weekly activity"), ("7-9 hrs", "Adult sleep"), ("2 L", "Hydration target")], citations=citations),
            _two_column(
                "Simple daily system",
                "Morning",
                "Evening",
                ["Wake at one time", "Hydrate before caffeine", "Move before messages"],
                ["End meals earlier", "Reduce bright light", "Use one fixed wind-down ritual"],
                citations=citations,
            ),
            _image("Recovery matters too", detail, "A lower-density slide keeps the deck from feeling like a wellness checklist", citations=citations),
            _quote("Habit rule", "Consistency compounds faster than intensity.", "AutoPPT Sample Desk", "Healthy Living Notes", citations=citations),
        ],
    )


def _build_en_art(definition: SampleDefinition, asset_dir: Path) -> DeckSpec:
    citations = ["https://www.metmuseum.org/toah/hd/itar/hd_itar.htm", "https://www.uffizi.it/en/artworks/birth-of-venus"]
    hero = _build_visual_asset(
        asset_dir,
        "en_art_hero",
        {
            "start": (86, 18, 40),
            "end": (196, 42, 66),
            "accent": (255, 218, 184),
            "line": (255, 236, 210),
            "ellipses": ((110, 110, 620, 620, 98), (900, 120, 1490, 760, 82), (500, 520, 1020, 930, 60)),
        },
        "frames",
    )
    gallery = _build_visual_asset(
        asset_dir,
        "en_art_gallery",
        {
            "start": (64, 20, 34),
            "end": (126, 30, 58),
            "accent": (255, 214, 174),
            "line": (255, 238, 214),
            "ellipses": ((90, 180, 560, 640, 90), (860, 120, 1480, 760, 74), (560, 560, 1040, 930, 54)),
        },
        "grid",
    )
    return _base_deck(
        definition,
        [
            _title("Renaissance Art", "How technique, patronage, and humanism reshaped visual culture"),
            _image("Editorial opening slide", hero, "A poster-like opening works better than a dense survey slide", citations=citations),
            _quote("Art history lens", "Perspective became a way of thinking, not just a way of drawing.", "AutoPPT Sample Desk", "Renaissance Art Notes", citations=citations),
            _content_with_image(
                "Why it still feels modern",
                [
                    "Space became persuasive.",
                    "Bodies gained gravity.",
                    "Viewers were given a position.",
                ],
                image_path=gallery,
                citations=citations,
            ),
            _image("Gallery wall slide", gallery, "A full-image page keeps pacing and atmosphere intact", citations=citations),
            _comparison(
                "Early vs High Renaissance",
                "Early Renaissance",
                "High Renaissance",
                ["Spatial experiments", "Measured emotion", "Technique consolidating"],
                ["Balanced compositions", "Integrated anatomy", "Ideal beauty and authority"],
                citations=citations,
            ),
            _two_column(
                "How to read a painting",
                "Formal clues",
                "Context clues",
                ["Perspective and composition", "Light and texture", "Gesture and proportion"],
                ["Patron identity", "Religious or civic use", "Classical references"],
                citations=citations,
            ),
        ],
    )


def _build_cn_visual_showcase(definition: SampleDefinition, asset_dir: Path) -> DeckSpec:
    citations = ["https://github.com/yeasy/autoppt", "https://platform.openai.com/docs/overview"]
    hero = _build_visual_asset(
        asset_dir,
        "cn_visual_hero",
        {
            "start": (8, 14, 36),
            "end": (18, 58, 116),
            "accent": (70, 220, 255),
            "line": (120, 190, 255),
            "ellipses": ((90, 120, 520, 520, 120), (920, 140, 1430, 650, 95), (540, 520, 1080, 980, 80)),
        },
        "grid",
    )
    detail = _build_visual_asset(
        asset_dir,
        "cn_visual_detail",
        {
            "start": (14, 32, 42),
            "end": (20, 104, 92),
            "accent": (120, 255, 200),
            "line": (185, 255, 220),
            "ellipses": ((110, 180, 650, 760, 105), (860, 70, 1460, 640, 90), (1050, 540, 1520, 920, 70)),
        },
        "waves",
    )
    gallery = _build_visual_asset(
        asset_dir,
        "cn_visual_gallery",
        {
            "start": (46, 20, 20),
            "end": (132, 70, 42),
            "accent": (255, 205, 130),
            "line": (255, 235, 180),
            "ellipses": ((140, 120, 530, 480, 100), (820, 120, 1470, 760, 80), (420, 520, 930, 900, 65)),
        },
        "frames",
    )
    return _base_deck(
        definition,
        [
            _title("视觉型展示样例", "面向图片主导型 deck 的高保真示例"),
            _image("智能城市氛围页", hero, "程序化生成的高保真视觉素材", citations=citations),
            _section("先建立气氛"),
            _image("展陈海报风格页", gallery, "让整页视觉先占据舞台，再压缩说明文字", citations=citations),
            _content_with_image(
                "视觉页真正有用的地方",
                [
                    "它先定义节奏。",
                    "它再决定记忆点。",
                    "它最后才承载说明。",
                ],
                image_path=detail,
                citations=citations,
            ),
            _image("横向叙事页", detail, "适合章节过渡、场景叙述和品牌语气铺垫", citations=citations),
            _quote("视觉原则", "先建立气氛，再压缩信息密度，图片型页面才会真正成立。", "AutoPPT Sample Desk", "Visual Showcase Notes", citations=citations),
        ],
    )


def _build_en_visual_showcase(definition: SampleDefinition, asset_dir: Path) -> DeckSpec:
    citations = ["https://github.com/yeasy/autoppt", "https://docs.streamlit.io/"]
    hero = _build_visual_asset(
        asset_dir,
        "en_visual_hero",
        {
            "start": (12, 18, 40),
            "end": (24, 72, 132),
            "accent": (84, 220, 255),
            "line": (140, 200, 255),
            "ellipses": ((110, 90, 590, 540, 120), (920, 120, 1480, 700, 95), (520, 480, 1120, 930, 75)),
        },
        "grid",
    )
    detail = _build_visual_asset(
        asset_dir,
        "en_visual_detail",
        {
            "start": (20, 22, 30),
            "end": (72, 36, 88),
            "accent": (255, 120, 190),
            "line": (255, 185, 220),
            "ellipses": ((120, 160, 620, 720, 105), (860, 120, 1450, 720, 85), (420, 520, 1020, 960, 70)),
        },
        "frames",
    )
    horizon = _build_visual_asset(
        asset_dir,
        "en_visual_horizon",
        {
            "start": (18, 34, 30),
            "end": (20, 112, 94),
            "accent": (135, 255, 220),
            "line": (200, 255, 230),
            "ellipses": ((90, 210, 580, 780, 100), (930, 60, 1500, 660, 85), (1180, 530, 1540, 900, 65)),
        },
        "waves",
    )
    return _base_deck(
        definition,
        [
            _title("Visual Showcase Sample", "A deterministic, image-forward deck"),
            _image("Hero visual slide", hero, "Programmatically generated high-fidelity hero image", citations=citations),
            _section("Atmosphere first"),
            _image("Poster-style visual page", detail, "A nearly empty visual page can carry tone better than a crowded explainer", citations=citations),
            _content_with_image(
                "Why image-heavy decks work",
                [
                    "They set mood instantly.",
                    "They slow the reading load.",
                    "They make structure feel intentional.",
                ],
                image_path=horizon,
                citations=citations,
            ),
            _image("Panoramic atmosphere slide", horizon, "Best used for transitions, chapter openers, and storytelling beats", citations=citations),
            _quote("Visual rule", "A strong image slide should lower cognitive load while raising emotional clarity.", "AutoPPT Sample Desk", "Visual Showcase Notes", citations=citations),
        ],
    )


def _build_feature_layouts_en(definition: SampleDefinition, asset_dir: Path) -> DeckSpec:
    citations = ["https://github.com/yeasy/autoppt", "https://platform.openai.com/docs/overview"]
    return _base_deck(
        definition,
        [
            _title("Layout Gallery", "Deterministic feature sample for richer layouts"),
            _section("Core layouts"),
            _content("Content layout", [
                "Use content slides when the message depends on a sequence of evidence-backed points.",
                "This layout is the baseline and should remain readable without visual gimmicks.",
                "It is still the best option for explanatory or narrative-heavy material.",
            ], citations=citations),
            _comparison("Comparison layout", "Current", "Target", ["Manual review process", "Fragmented tooling", "Slow feedback loops"], ["Unified workflow", "Shared tooling layer", "Faster quality checks"], citations=citations),
            _two_column("Two-column layout", "Build", "Operate", ["Model and tool integration", "Knowledge retrieval", "Evaluation setup"], ["Monitoring and review", "Cost controls", "Policy enforcement"], citations=citations),
            _quote("Quote layout", "Structure gives the model a better chance to be useful.", "AutoPPT Sample Desk", "Layout Gallery", citations=citations),
            _statistics("Statistics layout", [("5", "Primary content layouts"), ("1", "Deck QA pass before export"), ("0 keys", "Needed for deterministic refresh")], citations=citations),
            _chart("Chart layout", "Coverage score", ["Content", "Comparison", "Two-column", "Quote", "Statistics"], [95, 91, 89, 84, 92], chart_type=ChartType.BAR, citations=citations),
        ],
    )


def _build_feature_layouts_cn(definition: SampleDefinition, asset_dir: Path) -> DeckSpec:
    citations = ["https://github.com/yeasy/autoppt", "https://platform.openai.com/docs/overview"]
    return _base_deck(
        definition,
        [
            _title("版式画廊", "用于验证 richer layouts 的确定性样例"),
            _section("核心版式"),
            _content("内容页版式", [
                "当表达依赖连续论点和证据时，内容页依然是最稳妥的默认选择。",
                "即便存在更丰富的视觉版式，也不应牺牲可读性与结构清晰度。",
                "内容页应优先承载需要讲述逻辑链的主题。",
            ], citations=citations),
            _comparison("对比版式", "当前状态", "目标状态", ["流程依赖人工", "工具碎片化", "反馈周期慢"], ["统一工作流", "共享工具层", "质量回路更快"], citations=citations),
            _two_column("双栏版式", "建设", "运营", ["模型与工具接入", "知识检索", "评估体系"], ["监控与复盘", "成本控制", "策略治理"], citations=citations),
            _quote("引用版式", "结构清晰，模型才更可能真正有用。", "AutoPPT Sample Desk", "版式画廊", citations=citations),
            _statistics("统计版式", [("5", "主要内容版式"), ("1", "导出前 Deck QA"), ("0", "刷新样例所需 API Key")], citations=citations),
            _chart("图表版式", "Coverage Score", ["内容页", "对比", "双栏", "引用", "统计"], [95, 91, 89, 84, 92], chart_type=ChartType.BAR, citations=citations),
        ],
    )


def _build_feature_workbench(definition: SampleDefinition, asset_dir: Path) -> DeckSpec:
    citations = ["https://github.com/yeasy/autoppt", "https://docs.streamlit.io/"]
    return _base_deck(
        definition,
        [
            _title("Slide Workbench Flow", "Before and after single-slide operations"),
            _section("Original"),
            _content("Original content slide", [
                "The first editable version starts as a plain content slide with sequential points.",
                "This is useful when the user wants to inspect structure before forcing a richer layout.",
                "The workbench can then regenerate or remix the same slot without rebuilding the full deck.",
            ], citations=citations),
            _section("Regenerated as comparison"),
            _comparison("Regenerated comparison slide", "Current workflow", "Target workflow", ["Manual review gate", "Local prompt tweaks", "Inconsistent export quality"], ["Layout-aware planning", "Explicit target layout", "Repeatable export path"], citations=citations),
            _section("Remixed into two-column"),
            _two_column("Remixed two-column slide", "What stayed", "What changed", ["Same deck and topic context", "Same slide slot", "Same export pipeline"], ["Sharper grouping", "Cleaner visual rhythm", "More obvious speaking structure"], citations=citations),
            _quote("Why this matters", "Single-slide iteration keeps momentum without forcing a full rerun.", "AutoPPT Sample Desk", "Workbench Demo", citations=citations),
        ],
    )


_SAMPLE_BUILDERS = {
    "cn_tech": _build_cn_tech,
    "cn_life": _build_cn_life,
    "cn_art": _build_cn_art,
    "cn_visual_showcase": _build_cn_visual_showcase,
    "en_tech": _build_en_tech,
    "en_life": _build_en_life,
    "en_art": _build_en_art,
    "en_visual_showcase": _build_en_visual_showcase,
    "feature_layouts_en": _build_feature_layouts_en,
    "feature_layouts_cn": _build_feature_layouts_cn,
    "feature_workbench": _build_feature_workbench,
}
