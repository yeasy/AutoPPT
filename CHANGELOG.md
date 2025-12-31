# Changelog

All notable changes to AutoPPT will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2025-12-31

### Added
- **Streamlit Web UI**: New `app.py` provides a beautiful web interface for generating presentations without command line.
- **Unit Test Suite**: Comprehensive pytest tests.
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
