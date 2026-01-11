# Changelog

All notable changes to AutoPPT will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-01-11

### Added - Visual & Content Upgrade
- **High-Density Content**: Prompts now generate 5-8 substantive bullet points with sub-bullets, data, and statistics.
- **Modern Styling System**: 
  - Gradient background support.
  - Decorative accent lines for headers.
  - Enhanced typography for titles and special slides.
- **New Slide Types**:
  - `Fullscreen Image`: For impactful visual breaks or section headers.
  - `Statistics`: Dedicated layout for showcasing key metrics (big numbers).
- **5 New Premium Themes**:
  - `luxury` (Gold/Dark)
  - `magazine` (Editorial style)
  - `tech_gradient` (Indigo/Purple)
  - `ocean` (Deep Blue)
  - `sunset` (Warm Gradients)
- **Smart Layout Handling**: Generator now automatically selects between Content, Statistics, Image, and Chart layouts based on context.

### Changed
- Updated `SlideConfig` to support `slide_type` and `statistics` data fields.
- Refactored `ppt_renderer` to support cleaner XML-based gradient fills.

## [0.3.0] - 2025-12-31

### Added
- **PyPI Packaging**: Structured as `autoppt` package with `pyproject.toml` and CLI entry point.
- **Automated Safety Audit**: Integrated Git pre-commit hook to block sensitive data (API keys, local paths) and unwanted files (.log).
- **Unit Test Suite**: Comprehensive pytest tests (38/38 passing).
- **Documentation Workflow**: New `.agent/workflows/update-docs.md`.
- **Enhanced Gitignore**: Comprehensive `.gitignore`.
- **Cleaner History**: Used `git-filter-repo` to remove old logs.
- **Config Cleanup**: Refactored `.env.example` for better clarity.


### Removed
- **Cleanup**: Removed 11 unnecessary files from project root:
  - `generate_hq_research_samples.py`
  - `regenerate_v0.1_samples.py`
  - `populate_high_quality_samples.py`
  - `list_models_v2.py`
  - `available_models.txt`
  - `run_demo.sh`
  - Multiple `.log` files

### Dependencies
- Added: `streamlit`, `pytest`, `pytest-cov`

---

## [0.2.0] - 2025-12-30

### Added
- **Anthropic Claude Support**: Full `AnthropicProvider` with retry logic.
- **Wikipedia Integration**: Enhanced research with Wikipedia API.
- **Chart Generation**: Bar, pie, line, and column charts.
- **4 New Visual Themes**: corporate, academic, startup, dark.
- **Progress Indicators**: tqdm integration.
- **Custom Exceptions**: Friendly error messages.
- **Logging System**: Configurable verbosity.

### Changed
- Dynamic retry delays from config.
- Improved image download stability.

### Fixed
- Missing `import os` in ppt_renderer.py.
- Citations slide styling.

---

## [0.1.0] - 2025-12-30

### Added
- Initial release with core functionality.
- OpenAI and Google Gemini providers.
- Mock provider for testing.
- DuckDuckGo research integration.
- 4 visual themes.
- 6 sample presentations.

---

[0.3.0]: https://github.com/yeasy/autoppt/compare/v0.2...v0.3
[0.2.0]: https://github.com/yeasy/autoppt/compare/v0.1...v0.2
[0.1.0]: https://github.com/yeasy/autoppt/releases/tag/v0.1
