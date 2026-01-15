from autoppt.themes import get_theme, get_theme_names


def test_get_theme_names_includes_minimalist():
    assert "minimalist" in get_theme_names()


def test_get_theme_unknown_falls_back_to_minimalist():
    fallback = get_theme("missing-theme")
    minimalist = get_theme("minimalist")
    assert fallback["font_name"] == minimalist["font_name"]
    assert fallback["bg_color"] == minimalist["bg_color"]
