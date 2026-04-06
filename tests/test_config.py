import os
from unittest.mock import patch

import pytest

from autoppt.config import Config
from autoppt.exceptions import APIKeyError


class TestConfig:
    def setup_method(self):
        Config._env_loaded = False
        Config.OPENAI_API_KEY = None
        Config.ANTHROPIC_API_KEY = None
        Config.GOOGLE_API_KEY = None
        Config.OFFLINE_MODE = False

    def test_initialize_loads_env_once(self):
        Config._env_loaded = False
        Config.initialize()
        assert Config._env_loaded is True

    def test_refresh_reads_env_vars(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test123"}):
            Config.refresh()
            assert Config.OPENAI_API_KEY == "sk-test123"

    def test_offline_mode_from_env(self):
        with patch.dict(os.environ, {"AUTOPPT_OFFLINE": "1"}):
            Config.refresh()
            assert Config.OFFLINE_MODE is True

    def test_offline_mode_false_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            Config.refresh()
            assert Config.OFFLINE_MODE is False

    def test_provider_api_key_returns_none_for_unknown(self):
        assert Config.provider_api_key("unknown_provider") is None

    def test_has_api_key_mock_always_true(self):
        assert Config.has_api_key("mock") is True

    def test_has_api_key_returns_false_without_key(self):
        Config.OPENAI_API_KEY = None
        assert Config.has_api_key("openai") is False

    def test_validate_raises_for_missing_key(self):
        Config.OPENAI_API_KEY = None
        with pytest.raises(APIKeyError):
            Config.validate("openai")

    def test_validate_mock_always_passes(self):
        assert Config.validate("mock") is True

    def test_validate_returns_false_with_no_keys(self):
        Config.OPENAI_API_KEY = None
        Config.ANTHROPIC_API_KEY = None
        Config.GOOGLE_API_KEY = None
        assert Config.validate() is False

    def test_is_offline_mode(self):
        with patch.dict(os.environ, {"AUTOPPT_OFFLINE": "true"}):
            Config._env_loaded = False
            assert Config.is_offline_mode() is True

    def test_whitespace_api_keys_normalized_to_none(self):
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "  ",
            "ANTHROPIC_API_KEY": "\t\n",
            "GOOGLE_API_KEY": "",
        }):
            Config.refresh()
            assert Config.OPENAI_API_KEY is None
            assert Config.ANTHROPIC_API_KEY is None
            assert Config.GOOGLE_API_KEY is None

    def test_configure_logging_sets_level(self):
        import logging
        Config.configure_logging(logging.WARNING)
        assert logging.getLogger().level == logging.WARNING

    def test_initialize_with_configure_logging(self):
        """initialize calls _configure_logging_locked when flag is True."""
        import logging

        Config._env_loaded = False
        with patch.object(Config, "_configure_logging_locked") as mock_cl:
            Config.initialize(configure_logging=True, log_level=logging.DEBUG)
            mock_cl.assert_called_once_with(logging.DEBUG)

    def test_configure_logging_basicconfig_when_no_handlers(self):
        """Line 65: logging.basicConfig branch when root logger has no handlers."""
        import logging

        root = logging.getLogger()
        original_handlers = root.handlers[:]
        try:
            root.handlers.clear()
            with patch("autoppt.config.logging.basicConfig") as mock_bc:
                Config.configure_logging(logging.WARNING)
                mock_bc.assert_called_once_with(
                    level=logging.WARNING,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
        finally:
            root.handlers = original_handlers

    def test_validate_specific_provider_with_key_returns_true(self):
        """Line 96: validate returns True when a named provider has a key."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-valid"}):
            Config._env_loaded = False
            assert Config.validate("openai") is True

    def test_validate_no_provider_with_keys_returns_true(self):
        """Line 101: validate returns True when at least one key exists."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-valid"}):
            Config._env_loaded = False
            assert Config.validate() is True

    def test_concurrent_initialize_is_safe(self):
        import threading
        Config._env_loaded = False
        errors = []

        def init_config():
            try:
                Config.initialize()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=init_config) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert Config._env_loaded is True

    def test_initialize_with_configure_logging_actually_configures(self):
        """initialize(configure_logging=True) must not crash and must configure logging."""
        import logging

        Config._env_loaded = False
        Config.initialize(configure_logging=True, log_level=logging.DEBUG)

        assert Config._env_loaded is True
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_blocked_system_prefixes_available(self):
        """BLOCKED_SYSTEM_PREFIXES exists and contains expected system paths."""
        prefixes = Config.BLOCKED_SYSTEM_PREFIXES
        assert isinstance(prefixes, tuple)
        assert "/etc/" in prefixes
        assert "/proc/" in prefixes
        assert "/dev/" in prefixes

    def test_template_size_constants(self):
        """MAX_TEMPLATE_BYTES and MAX_DECOMPRESSED_BYTES are defined with expected values."""
        assert Config.MAX_TEMPLATE_BYTES == 50 * 1024 * 1024
        assert Config.MAX_DECOMPRESSED_BYTES == 200 * 1024 * 1024

    def test_article_fetch_timeout_defined(self):
        """ARTICLE_FETCH_TIMEOUT must be a positive number."""
        assert hasattr(Config, "ARTICLE_FETCH_TIMEOUT")
        assert Config.ARTICLE_FETCH_TIMEOUT > 0
