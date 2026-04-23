"""
Unit tests for autoppt.main module.

Covers all major code paths including argument parsing, auto-style selection,
outline-only flow, confirm-outline interactive mode, and all exception handlers.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from autoppt.config import Config
from autoppt.exceptions import APIKeyError, AutoPPTError, RateLimitError
from autoppt.main import main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _default_args(**overrides):
    """Return a MagicMock with default argument values, applying overrides."""
    defaults = dict(
        topic="Test Topic",
        style="minimalist",
        provider="mock",
        slides=5,
        language="English",
        model=None,
        output=None,
        template=None,
        thumbnails=False,
        auto_style=False,
        outline_only=False,
        confirm_outline=False,
        verbose=False,
    )
    defaults.update(overrides)
    return MagicMock(**defaults)


def _mock_generator_context(mock_generator):
    """Wire up a mock Generator class so it works as a context manager."""
    instance = mock_generator.return_value
    instance.__enter__ = MagicMock(return_value=instance)
    instance.__exit__ = MagicMock(return_value=False)
    return instance


@pytest.fixture
def mock_args():
    with patch("argparse.ArgumentParser.parse_args") as mock:
        yield mock


# ---------------------------------------------------------------------------
# Basic success / output path tests
# ---------------------------------------------------------------------------

@patch("autoppt.main.Config.initialize")
@patch("autoppt.main.Config.validate")
@patch("autoppt.generator.Generator")
def test_main_success_mock(mock_generator, mock_validate, mock_initialize, mock_args):
    mock_args.return_value = _default_args()

    gen = _mock_generator_context(mock_generator)
    gen.generate.return_value = "output/Test_Topic.pptx"

    main()

    mock_initialize.assert_called_once()
    mock_generator.assert_called_once()
    gen.generate.assert_called_once()
    assert gen.generate.call_args.kwargs["create_thumbnails"] is False


@patch("autoppt.main.Config.initialize")
@patch("autoppt.main.Config.validate")
@patch("autoppt.generator.Generator")
def test_main_custom_output(mock_generator, mock_validate, mock_initialize, mock_args):
    mock_args.return_value = _default_args(output="custom/path.pptx", verbose=True, style="dark")

    gen = _mock_generator_context(mock_generator)

    main()

    _, kwargs = gen.generate.call_args
    assert kwargs["output_file"] == "custom/path.pptx"


# ---------------------------------------------------------------------------
# Auto-style selection (lines 87-89)
# ---------------------------------------------------------------------------

@patch("autoppt.main.Config.initialize")
@patch("autoppt.main.Config.validate")
@patch("autoppt.main.get_style_description", return_value="tech visuals")
@patch("autoppt.main.auto_select_style", return_value="technology")
@patch("autoppt.generator.Generator")
def test_main_auto_style(mock_generator, mock_auto_style, mock_desc, mock_validate, mock_init, mock_args):
    mock_args.return_value = _default_args(auto_style=True)

    gen = _mock_generator_context(mock_generator)
    gen.generate.return_value = "output/Test_Topic.pptx"

    main()

    mock_auto_style.assert_called_once_with("Test Topic", "English")
    kwargs = gen.generate.call_args.kwargs
    assert kwargs["style"] == "technology"


# ---------------------------------------------------------------------------
# Slide count validation (line 91-92)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Topic validation
# ---------------------------------------------------------------------------

@patch("autoppt.main.Config.initialize")
def test_main_topic_empty(mock_init, mock_args):
    mock_args.return_value = _default_args(topic="")

    with pytest.raises(SystemExit):
        main()


@patch("autoppt.main.Config.initialize")
def test_main_topic_whitespace_only(mock_init, mock_args):
    mock_args.return_value = _default_args(topic="   ")

    with pytest.raises(SystemExit):
        main()


@patch("autoppt.main.Config.initialize")
def test_main_topic_too_long(mock_init, mock_args):
    mock_args.return_value = _default_args(topic="A" * 1001)

    with pytest.raises(SystemExit):
        main()


@patch("autoppt.main.Config.initialize")
@patch("autoppt.main.Config.validate")
@patch("autoppt.generator.Generator")
def test_main_topic_at_max_length(mock_generator, mock_validate, mock_init, mock_args):
    """A topic of exactly 1000 characters should be accepted."""
    mock_args.return_value = _default_args(topic="A" * 1000)

    gen = _mock_generator_context(mock_generator)
    gen.generate.return_value = "output/test.pptx"

    main()

    gen.generate.assert_called_once()


# ---------------------------------------------------------------------------
# Template path validation
# ---------------------------------------------------------------------------

@patch("autoppt.main.Config.initialize")
def test_main_template_not_found(mock_init, mock_args):
    mock_args.return_value = _default_args(template="/nonexistent/template.pptx")

    with pytest.raises(SystemExit):
        main()


@patch("autoppt.main.Config.initialize")
@patch("autoppt.main.Config.validate")
@patch("autoppt.generator.Generator")
def test_main_template_valid(mock_generator, mock_validate, mock_init, mock_args, tmp_path):
    """A template that exists on disk should be accepted."""
    tpl = tmp_path / "template.pptx"
    tpl.write_text("fake")
    mock_args.return_value = _default_args(template=str(tpl))

    gen = _mock_generator_context(mock_generator)
    gen.generate.return_value = "output/Test_Topic.pptx"

    main()

    kwargs = gen.generate.call_args.kwargs
    assert kwargs["template_path"] == str(tpl)


# ---------------------------------------------------------------------------
# Slide count validation (line 91-92)
# ---------------------------------------------------------------------------

@patch("autoppt.main.Config.initialize")
def test_main_slides_too_few(mock_init, mock_args):
    mock_args.return_value = _default_args(slides=2)

    with pytest.raises(SystemExit):
        main()


@patch("autoppt.main.Config.initialize")
def test_main_slides_too_many(mock_init, mock_args):
    mock_args.return_value = _default_args(slides=51)

    with pytest.raises(SystemExit):
        main()


@patch("autoppt.main.Config.initialize")
@patch("autoppt.main.Config.validate")
@patch("autoppt.generator.Generator")
def test_main_slides_boundary_min(mock_generator, mock_validate, mock_init, mock_args):
    """slides=3 is the lower boundary and should be accepted."""
    mock_args.return_value = _default_args(slides=3)

    gen = _mock_generator_context(mock_generator)
    gen.generate.return_value = "output/Test_Topic.pptx"

    main()

    gen.generate.assert_called_once()


@patch("autoppt.main.Config.initialize")
@patch("autoppt.main.Config.validate")
@patch("autoppt.generator.Generator")
def test_main_slides_boundary_max(mock_generator, mock_validate, mock_init, mock_args):
    """slides=50 is the upper boundary and should be accepted."""
    mock_args.return_value = _default_args(slides=50)

    gen = _mock_generator_context(mock_generator)
    gen.generate.return_value = "output/Test_Topic.pptx"

    main()

    gen.generate.assert_called_once()


# ---------------------------------------------------------------------------
# Model logging (line 102-103)
# ---------------------------------------------------------------------------

@patch("autoppt.main.Config.initialize")
@patch("autoppt.main.Config.validate")
@patch("autoppt.generator.Generator")
def test_main_with_model_specified(mock_generator, mock_validate, mock_init, mock_args):
    mock_args.return_value = _default_args(model="gpt-4o")

    gen = _mock_generator_context(mock_generator)
    gen.generate.return_value = "output/Test_Topic.pptx"

    main()

    mock_generator.assert_called_once_with(provider_name="mock", model="gpt-4o")


# ---------------------------------------------------------------------------
# --outline-only flow (lines 117-124)
# ---------------------------------------------------------------------------

@patch("autoppt.main.Config.initialize")
@patch("autoppt.main.Config.validate")
@patch("autoppt.generator.Generator")
def test_main_outline_only(mock_generator, mock_validate, mock_init, mock_args):
    mock_args.return_value = _default_args(outline_only=True)

    gen = _mock_generator_context(mock_generator)
    gen.generate_outline.return_value = MagicMock()
    gen.outline_to_markdown.return_value = "# Test Outline\n## Section 1"

    main()

    gen.generate_outline.assert_called_once_with("Test Topic", 5, "English")
    gen.save_outline.assert_called_once()
    gen.outline_to_markdown.assert_called_once()
    # generate should NOT be called in outline-only mode
    gen.generate.assert_not_called()


# ---------------------------------------------------------------------------
# --confirm-outline flow (lines 126-153)
# ---------------------------------------------------------------------------

@patch("autoppt.main.Config.initialize")
@patch("autoppt.main.Config.validate")
@patch("builtins.input", return_value="y")
@patch("autoppt.generator.Generator")
def test_main_confirm_outline_accept(mock_generator, mock_input, mock_validate, mock_init, mock_args):
    mock_args.return_value = _default_args(confirm_outline=True)

    gen = _mock_generator_context(mock_generator)
    gen.generate_outline.return_value = MagicMock()
    gen.outline_to_markdown.return_value = "# Outline"
    gen.generate_from_outline.return_value = "output/Test_Topic.pptx"

    main()

    gen.generate_outline.assert_called_once()
    gen.generate_from_outline.assert_called_once()


@patch("autoppt.main.Config.initialize")
@patch("autoppt.main.Config.validate")
@patch("builtins.input", return_value="n")
@patch("autoppt.generator.Generator")
def test_main_confirm_outline_reject(mock_generator, mock_input, mock_validate, mock_init, mock_args):
    mock_args.return_value = _default_args(confirm_outline=True)

    gen = _mock_generator_context(mock_generator)
    gen.generate_outline.return_value = MagicMock()
    gen.outline_to_markdown.return_value = "# Outline"

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    gen.generate_from_outline.assert_not_called()


@patch("autoppt.main.Config.initialize")
@patch("autoppt.main.Config.validate")
@patch("builtins.input", return_value="q")
@patch("autoppt.generator.Generator")
def test_main_confirm_outline_quit(mock_generator, mock_input, mock_validate, mock_init, mock_args):
    mock_args.return_value = _default_args(confirm_outline=True)

    gen = _mock_generator_context(mock_generator)
    gen.generate_outline.return_value = MagicMock()
    gen.outline_to_markdown.return_value = "# Outline"

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    gen.generate_from_outline.assert_not_called()


@patch("autoppt.main.Config.initialize")
@patch("autoppt.main.Config.validate")
@patch("builtins.input", side_effect=EOFError)
@patch("autoppt.generator.Generator")
def test_main_confirm_outline_eof(mock_generator, mock_input, mock_validate, mock_init, mock_args):
    """When stdin is not interactive (EOFError), generation proceeds."""
    mock_args.return_value = _default_args(confirm_outline=True)

    gen = _mock_generator_context(mock_generator)
    gen.generate_outline.return_value = MagicMock()
    gen.outline_to_markdown.return_value = "# Outline"
    gen.generate_from_outline.return_value = "output/Test_Topic.pptx"

    main()

    gen.generate_from_outline.assert_called_once()


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

@patch("autoppt.main.Config.initialize")
@patch("autoppt.main.Config.validate")
def test_main_api_key_error(mock_validate, mock_initialize, mock_args):
    mock_args.return_value = _default_args(provider="openai")
    mock_validate.side_effect = APIKeyError("openai")

    with pytest.raises(SystemExit) as wrapped:
        main()

    assert wrapped.value.code == 1


@patch("autoppt.main.Config.initialize")
@patch("autoppt.main.Config.validate")
@patch("autoppt.generator.Generator")
def test_main_autoppt_error(mock_generator, mock_validate, mock_initialize, mock_args):
    mock_args.return_value = _default_args()

    gen = _mock_generator_context(mock_generator)
    gen.generate.side_effect = AutoPPTError("Generation failed")

    with pytest.raises(SystemExit) as wrapped:
        main()

    assert wrapped.value.code == 1


@patch("autoppt.main.Config.initialize")
@patch("autoppt.main.Config.validate")
@patch("autoppt.generator.Generator")
def test_main_rate_limit_error(mock_generator, mock_validate, mock_init, mock_args):
    mock_args.return_value = _default_args()

    gen = _mock_generator_context(mock_generator)
    gen.generate.side_effect = RateLimitError("openai", retry_after=60)

    with pytest.raises(SystemExit) as wrapped:
        main()

    assert wrapped.value.code == 1


@patch("autoppt.main.Config.initialize")
@patch("autoppt.main.Config.validate")
@patch("autoppt.generator.Generator")
def test_main_keyboard_interrupt(mock_generator, mock_validate, mock_init, mock_args):
    mock_args.return_value = _default_args()

    gen = _mock_generator_context(mock_generator)
    gen.generate.side_effect = KeyboardInterrupt

    with pytest.raises(SystemExit) as wrapped:
        main()

    assert wrapped.value.code == 130


@patch("autoppt.main.Config.initialize")
@patch("autoppt.main.Config.validate")
@patch("autoppt.generator.Generator")
def test_main_unexpected_error(mock_generator, mock_validate, mock_init, mock_args):
    mock_args.return_value = _default_args()

    gen = _mock_generator_context(mock_generator)
    gen.generate.side_effect = RuntimeError("something unexpected")

    with pytest.raises(SystemExit) as wrapped:
        main()

    assert wrapped.value.code == 1


@patch("autoppt.main.Config.initialize")
@patch("autoppt.main.Config.validate")
@patch("autoppt.generator.Generator")
def test_main_unexpected_error_verbose(mock_generator, mock_validate, mock_init, mock_args):
    """Verbose mode should trigger traceback printing on unexpected errors."""
    mock_args.return_value = _default_args(verbose=True)

    gen = _mock_generator_context(mock_generator)
    gen.generate.side_effect = RuntimeError("verbose crash")

    with pytest.raises(SystemExit) as wrapped:
        main()

    assert wrapped.value.code == 1


# ---------------------------------------------------------------------------
# Quality report logging (lines 167-168)
# ---------------------------------------------------------------------------

@patch("autoppt.main.Config.initialize")
@patch("autoppt.main.Config.validate")
@patch("autoppt.generator.Generator")
def test_main_quality_report_with_issues(mock_generator, mock_validate, mock_init, mock_args):
    mock_args.return_value = _default_args()

    gen = _mock_generator_context(mock_generator)
    gen.generate.return_value = "output/Test_Topic.pptx"
    gen.last_quality_report.has_issues = True
    gen.last_quality_report.issues = ["Empty bullets on slide 3"]

    main()

    gen.generate.assert_called_once()


@patch("autoppt.main.Config.initialize")
@patch("autoppt.main.Config.validate")
@patch("autoppt.generator.Generator")
def test_main_quality_report_no_issues(mock_generator, mock_validate, mock_init, mock_args):
    mock_args.return_value = _default_args()

    gen = _mock_generator_context(mock_generator)
    gen.generate.return_value = "output/Test_Topic.pptx"
    gen.last_quality_report.has_issues = False

    main()

    gen.generate.assert_called_once()


# ---------------------------------------------------------------------------
# Config.validate skipped for mock provider (line 108)
# ---------------------------------------------------------------------------

@patch("autoppt.main.Config.initialize")
@patch("autoppt.main.Config.validate")
@patch("autoppt.generator.Generator")
def test_main_mock_provider_skips_validate(mock_generator, mock_validate, mock_init, mock_args):
    mock_args.return_value = _default_args(provider="mock")

    gen = _mock_generator_context(mock_generator)
    gen.generate.return_value = "output/Test_Topic.pptx"

    main()

    mock_validate.assert_not_called()


@patch("autoppt.main.Config.initialize")
@patch("autoppt.main.Config.validate")
@patch("autoppt.generator.Generator")
def test_main_non_mock_provider_calls_validate(mock_generator, mock_validate, mock_init, mock_args):
    mock_args.return_value = _default_args(provider="openai")

    gen = _mock_generator_context(mock_generator)
    gen.generate.return_value = "output/Test_Topic.pptx"

    main()

    mock_validate.assert_called_once_with("openai")


# ---------------------------------------------------------------------------
# Default output path generation (lines 82-84)
# ---------------------------------------------------------------------------

@patch("autoppt.main.Config.initialize")
@patch("autoppt.main.Config.validate")
@patch("autoppt.generator.Generator")
def test_main_default_output_sanitizes_topic(mock_generator, mock_validate, mock_init, mock_args):
    mock_args.return_value = _default_args(topic="Hello World! @#$", output=None)

    gen = _mock_generator_context(mock_generator)
    gen.generate.return_value = "output/Hello_World______.pptx"

    main()

    kwargs = gen.generate.call_args.kwargs
    output_file = kwargs["output_file"]
    # Should not contain special characters other than underscore and hyphen
    assert "@" not in output_file
    assert "#" not in output_file
    assert "$" not in output_file
    assert output_file.endswith(".pptx")


# ---------------------------------------------------------------------------
# if __name__ == "__main__" (line 194-195)
# ---------------------------------------------------------------------------

@patch("autoppt.main.Config.initialize")
@patch("autoppt.main.Config.validate")
@patch("autoppt.generator.Generator")
def test_main_bare_filename_stays_in_cwd(mock_generator, mock_validate, mock_init, mock_args):
    """When --output is a bare filename (no directory), it should stay in CWD as user intended."""
    mock_args.return_value = _default_args(output="test.pptx")

    gen = _mock_generator_context(mock_generator)
    gen.generate.return_value = "test.pptx"

    with patch("os.makedirs") as mock_makedirs:
        main()

    _, kwargs = gen.generate.call_args
    assert kwargs["output_file"] == "test.pptx"


# ---------------------------------------------------------------------------
# Validation order: topic validated before use
# ---------------------------------------------------------------------------


@patch("autoppt.main.argparse.ArgumentParser.parse_args")
@patch("autoppt.main.Config")
def test_empty_topic_rejected_before_path_computation(mock_config, mock_parse):
    """Empty topic should trigger parser.error before any path computation."""
    mock_parse.return_value = _default_args(topic="   ", output=None)
    with pytest.raises(SystemExit):
        main()


@patch("autoppt.main.argparse.ArgumentParser.parse_args")
@patch("autoppt.main.Config")
def test_output_path_rejects_system_path(mock_config, mock_parse):
    """Output path pointing to system directories should be rejected."""
    mock_parse.return_value = _default_args(topic="Test", output="/etc/evil.pptx")
    with pytest.raises(SystemExit):
        main()


@patch("autoppt.main.argparse.ArgumentParser.parse_args")
@patch("autoppt.main.Config")
def test_output_path_rejects_sensitive_segment_ssh(mock_config, mock_parse):
    """Output path containing .ssh/ should be rejected."""
    mock_parse.return_value = _default_args(topic="Test", output="/home/user/.ssh/evil.pptx")
    with pytest.raises(SystemExit):
        main()


@patch("autoppt.main.argparse.ArgumentParser.parse_args")
@patch("autoppt.main.Config")
def test_output_path_rejects_sensitive_segment_docker(mock_config, mock_parse):
    """Output path containing .docker/ should be rejected."""
    mock_parse.return_value = _default_args(topic="Test", output="/home/user/.docker/evil.pptx")
    with pytest.raises(SystemExit):
        main()


@patch("autoppt.main.argparse.ArgumentParser.parse_args")
@patch("autoppt.main.Config")
def test_output_path_rejects_traversal(mock_config, mock_parse):
    """Output path containing '..' segments should be rejected."""
    mock_parse.return_value = _default_args(topic="Test", output="output/../../../etc/evil.pptx")
    with pytest.raises(SystemExit):
        main()


@patch("autoppt.main.Config.initialize")
def test_main_language_too_long(mock_init, mock_args):
    """Language strings exceeding 50 characters should be rejected."""
    mock_args.return_value = _default_args(language="A" * 51)
    with pytest.raises(SystemExit):
        main()


@patch("autoppt.main.Config.initialize")
@patch("autoppt.main.Config.validate")
@patch("autoppt.generator.Generator")
def test_main_language_at_max_length(mock_generator, mock_validate, mock_init, mock_args):
    """A language string of exactly 50 characters should be accepted."""
    mock_args.return_value = _default_args(language="A" * 50)
    gen = _mock_generator_context(mock_generator)
    gen.generate.return_value = "output/Test_Topic.pptx"
    main()
    gen.generate.assert_called_once()


# ---------------------------------------------------------------------------
# Blocked system prefix in --output (main.py line 99)
# ---------------------------------------------------------------------------

@patch("autoppt.main.Config.initialize")
def test_cli_blocked_system_prefix_etc(mock_init, mock_args):
    """--output pointing under /etc/ must be rejected (BLOCKED_SYSTEM_PREFIXES)."""
    mock_args.return_value = _default_args(output="/etc/foo.pptx")
    with pytest.raises(SystemExit):
        main()


@patch("autoppt.main.Config.initialize")
def test_cli_blocked_system_prefix_proc(mock_init, mock_args):
    """--output pointing under /proc/ must be rejected."""
    mock_args.return_value = _default_args(output="/proc/something.pptx")
    with pytest.raises(SystemExit):
        main()


@patch("autoppt.main.Config.initialize")
def test_cli_blocked_system_prefix_dev(mock_init, mock_args):
    """--output pointing under /dev/ must be rejected."""
    mock_args.return_value = _default_args(output="/dev/null.pptx")
    with pytest.raises(SystemExit):
        main()


# ---------------------------------------------------------------------------
# Blocked path segment in --output (main.py line 102)
# ---------------------------------------------------------------------------

@patch("autoppt.main.Config.initialize")
def test_cli_blocked_path_segment_ssh(mock_init, mock_args):
    """--output containing /.ssh/ must be rejected (BLOCKED_PATH_SEGMENTS)."""
    mock_args.return_value = _default_args(output="/tmp/.ssh/foo.pptx")
    with pytest.raises(SystemExit):
        main()


@patch("autoppt.main.Config.initialize")
def test_cli_blocked_path_segment_gnupg(mock_init, mock_args):
    """--output containing /.gnupg/ must be rejected."""
    mock_args.return_value = _default_args(output="/home/user/.gnupg/evil.pptx")
    with pytest.raises(SystemExit):
        main()


@patch("autoppt.main.Config.initialize")
def test_cli_blocked_path_segment_aws(mock_init, mock_args):
    """--output containing /.aws/ must be rejected."""
    mock_args.return_value = _default_args(output="/home/user/.aws/creds.pptx")
    with pytest.raises(SystemExit):
        main()


@patch("autoppt.main.Config.initialize")
def test_cli_blocked_path_segment_kube(mock_init, mock_args):
    """--output containing /.kube/ must be rejected."""
    mock_args.return_value = _default_args(output="/home/user/.kube/config.pptx")
    with pytest.raises(SystemExit):
        main()


# ---------------------------------------------------------------------------
# Windows reserved filename prefix (main.py lines 106-107)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("reserved_name", ["CON", "PRN", "AUX", "NUL"])
@patch("autoppt.main.Config.initialize")
@patch("autoppt.main.Config.validate")
@patch("autoppt.generator.Generator")
def test_windows_reserved_name_gets_deck_prefix(mock_generator, mock_validate, mock_init, mock_args, reserved_name):
    """Topics matching Windows reserved names (CON, PRN, AUX, NUL) must get a 'deck_' prefix."""
    mock_args.return_value = _default_args(topic=reserved_name, output=None)

    gen = _mock_generator_context(mock_generator)
    gen.generate.return_value = f"output/deck_{reserved_name}.pptx"

    main()

    kwargs = gen.generate.call_args.kwargs
    output_file = kwargs["output_file"]
    assert output_file == os.path.join("output", f"deck_{reserved_name}.pptx")


@pytest.mark.parametrize("reserved_name", ["COM1", "COM2", "COM9", "LPT1", "LPT2", "LPT9"])
@patch("autoppt.main.Config.initialize")
@patch("autoppt.main.Config.validate")
@patch("autoppt.generator.Generator")
def test_windows_reserved_com_lpt_gets_deck_prefix(mock_generator, mock_validate, mock_init, mock_args, reserved_name):
    """Topics matching COM[0-9] or LPT[0-9] must get a 'deck_' prefix."""
    mock_args.return_value = _default_args(topic=reserved_name, output=None)

    gen = _mock_generator_context(mock_generator)
    gen.generate.return_value = f"output/deck_{reserved_name}.pptx"

    main()

    kwargs = gen.generate.call_args.kwargs
    output_file = kwargs["output_file"]
    assert output_file == os.path.join("output", f"deck_{reserved_name}.pptx")


@patch("autoppt.main.Config.initialize")
@patch("autoppt.main.Config.validate")
@patch("autoppt.generator.Generator")
def test_windows_reserved_name_case_insensitive(mock_generator, mock_validate, mock_init, mock_args):
    """The reserved-name check should be case-insensitive (e.g., 'con' or 'Con')."""
    mock_args.return_value = _default_args(topic="con", output=None)

    gen = _mock_generator_context(mock_generator)
    gen.generate.return_value = "output/deck_con.pptx"

    main()

    kwargs = gen.generate.call_args.kwargs
    output_file = kwargs["output_file"]
    assert output_file == os.path.join("output", "deck_con.pptx")


@patch("autoppt.main.Config.initialize")
@patch("autoppt.main.Config.validate")
@patch("autoppt.generator.Generator")
def test_normal_topic_no_deck_prefix(mock_generator, mock_validate, mock_init, mock_args):
    """A normal topic (not a Windows reserved name) should NOT get a 'deck_' prefix."""
    mock_args.return_value = _default_args(topic="AI", output=None)

    gen = _mock_generator_context(mock_generator)
    gen.generate.return_value = "output/AI.pptx"

    main()

    kwargs = gen.generate.call_args.kwargs
    output_file = kwargs["output_file"]
    assert output_file == os.path.join("output", "AI.pptx")
    assert "deck_" not in output_file
