import pytest
from autoppt.themes import DEFAULT_THEME, get_theme, get_theme_names


def test_get_theme_names_includes_minimalist():
    assert "minimalist" in get_theme_names()


def test_get_theme_unknown_falls_back_to_minimalist():
    fallback = get_theme("missing-theme")
    minimalist = get_theme("minimalist")
    assert fallback["font_name"] == minimalist["font_name"]
    assert fallback["bg_color"] == minimalist["bg_color"]


@pytest.mark.parametrize("theme_name", get_theme_names())
def test_every_theme_has_all_default_keys(theme_name):
    """Each theme must contain every key from DEFAULT_THEME."""
    theme = get_theme(theme_name)
    for key in DEFAULT_THEME:
        assert key in theme, f"Theme '{theme_name}' missing key '{key}'"


def test_get_theme_none_falls_back():
    theme = get_theme(None)
    assert "font_name" in theme


def test_get_theme_empty_falls_back():
    theme = get_theme("")
    assert "font_name" in theme
