# Changelog

All notable changes to AutoPPT will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-12-31

### Added
- **Anthropic Claude Support**: Full implementation of `AnthropicProvider` with retry logic and JSON-based structured output.
- **Wikipedia Integration**: Enhanced research capabilities with direct Wikipedia API queries for richer, more authoritative content.
- **Chart Generation**: New `add_chart_slide()` method supporting bar, pie, line, and column charts using `python-pptx` native charting.
- **4 New Visual Themes**:
  - `corporate`: Professional blue tones with Calibri font
  - `academic`: Traditional maroon/cream for scholarly presentations
  - `startup`: Vibrant orange accents for modern pitches
  - `dark`: Cyan/purple on dark background for tech presentations
- **Progress Indicators**: `tqdm` integration for real-time progress bars during generation.
- **Custom Exceptions**: New `core/exceptions.py` with `APIKeyError`, `RateLimitError`, `ResearchError`, `RenderError` for friendly error messages.
- **Logging System**: Replaced all `print()` calls with Python `logging` module for configurable verbosity.
- **Verbose Mode**: `-v/--verbose` flag for detailed debug output.
- **Output Path Option**: `--output` flag to specify custom output file path.

### Changed
- **Config Improvements**: Synchronized default model names with actual implementations; added performance settings.
- **Dynamic Retry Delays**: Rate limit handling now uses configurable delays from `Config.API_RETRY_DELAY_SECONDS`.
- **Image Download Stability**: Increased timeout to 30s with retry logic for failed downloads.
- **Generator Refactoring**: Cleaner architecture with type hints, docstrings, and graceful error fallback.
- **Main Entry Point**: Enhanced argument parsing with examples, choices validation, and structured error handling.

### Fixed
- **Missing Import**: Added `import os` to `ppt_renderer.py` (previously caused runtime errors).
- **Type Annotations**: Added complete type hints across all core modules.
- **Citations Slide Styling**: Now applies theme colors to the references slide.

### Dependencies
- Added: `anthropic`, `wikipedia`, `tqdm`

---

## [0.1.0] - 2025-12-30

### Added
- Initial release with core presentation generation functionality.
- Support for OpenAI and Google Gemini providers.
- Mock provider for API-free testing.
- DuckDuckGo web research integration.
- Hierarchical section/slide structure.
- 4 visual themes: minimalist, technology, nature, creative.
- Image search and embedding.
- Speaker notes and citations.
- 6 sample presentations (CN/EN: Tech, Life, Art).

---

[0.2.0]: https://github.com/yeasy/autoppt/compare/v0.1...v0.2
[0.1.0]: https://github.com/yeasy/autoppt/releases/tag/v0.1
