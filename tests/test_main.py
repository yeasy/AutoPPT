from unittest.mock import MagicMock, patch

import pytest

from autoppt.exceptions import APIKeyError, AutoPPTError
from autoppt.main import main


@pytest.fixture
def mock_args():
    with patch("argparse.ArgumentParser.parse_args") as mock:
        yield mock


@patch("autoppt.main.Config.initialize")
@patch("autoppt.main.Config.validate")
@patch("autoppt.generator.Generator")
def test_main_success_mock(mock_generator, mock_validate, mock_initialize, mock_args):
    mock_args.return_value = MagicMock(
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

    mock_gen_instance = mock_generator.return_value
    mock_gen_instance.generate.return_value = "output/Test_Topic.pptx"

    main()

    mock_initialize.assert_called_once()
    mock_generator.assert_called_once()
    mock_gen_instance.generate.assert_called_once()
    kwargs = mock_gen_instance.generate.call_args.kwargs
    assert kwargs["create_thumbnails"] is False


@patch("autoppt.main.Config.initialize")
@patch("autoppt.main.Config.validate")
@patch("autoppt.generator.Generator")
def test_main_custom_output(mock_generator, mock_validate, mock_initialize, mock_args):
    mock_args.return_value = MagicMock(
        topic="Topic",
        style="dark",
        provider="mock",
        slides=10,
        language="English",
        model=None,
        output="custom/path.pptx",
        template=None,
        thumbnails=False,
        auto_style=False,
        outline_only=False,
        confirm_outline=False,
        verbose=True,
    )

    main()

    _, kwargs = mock_generator.return_value.generate.call_args
    assert kwargs["output_file"] == "custom/path.pptx"


@patch("autoppt.main.Config.initialize")
@patch("autoppt.main.Config.validate")
def test_main_api_key_error(mock_validate, mock_initialize, mock_args):
    mock_args.return_value = MagicMock(
        topic="Test Topic",
        style="minimalist",
        provider="openai",
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
    mock_validate.side_effect = APIKeyError("openai")

    with pytest.raises(SystemExit) as wrapped:
        main()

    assert wrapped.value.code == 1


@patch("autoppt.main.Config.initialize")
@patch("autoppt.main.Config.validate")
@patch("autoppt.generator.Generator")
def test_main_generator_error(mock_generator, mock_validate, mock_initialize, mock_args):
    mock_args.return_value = MagicMock(
        topic="Fail",
        provider="mock",
        style="minimalist",
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

    mock_generator.return_value.generate.side_effect = AutoPPTError("Generation failed")

    with pytest.raises(SystemExit) as wrapped:
        main()

    assert wrapped.value.code == 1
