# Changelog

All notable changes to AutoPPT will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Slide planning layer with `SlidePlan` and `slide_planner.py`.
- Editable `DeckSpec` workflow with save, load, regenerate, and remix helpers.
- Web slide workbench for post-generation single-slide operations.
- Deterministic sample library and README preview generation.

### Changed
- Richer layout flow now treats comparison, two-column, and quote slides as first-class editable layouts.
- Rendering now uses theme tokens for spacing, panels, image treatment, and typography.
- Repository docs are split into separate English and Chinese files where needed.

## [0.5.1] - 2026-03-27

### Fixed
- Empty statistics slides no longer leave orphaned blank slides in the deck.
- Slide dimension helpers use explicit `None` checks instead of falsy fallback.
- Temp file leak in `_cover_image` when image save fails.
- Use-after-close guard prevents silent writes to current directory after `Generator.close()`.
- Research context truncation now appends `[...truncated]` for LLM awareness.
- Mutable session state defaults no longer shared across Streamlit sessions.
- Empty sanitized topic falls back to `"presentation"` instead of producing a bare `.pptx` filename.
- Post-close access to `Generator` attributes captured before `close()` in both generation and remix paths.
- Multi-master templates no longer overwrite layouts with duplicate indices.
- Null layout guard in slide planner prevents `AttributeError` during remix.
- SSRF DNS resolution failures now emit debug-level log for diagnosis.
- OpenAI localhost detection uses consistent `_is_local_base_url` helper.
- Slide count validation runs before the info banner is logged.
- Outline file path construction handles `.pptx` in directory names.
- `RateLimitError` correctly formats message when `retry_after=0`.
- Unknown theme names log a warning before falling back to minimalist.
- Error slide truncation indicator shows `...` suffix.

### Changed
- Removed deprecated `version` key from `docker-compose.yml`.
- Corrected PyPI classifier to `Topic :: Office/Business`.
- Enabled `pydantic.mypy` plugin for stricter type checking.
- Removed unused `json` import from `template_handler.py`.
- Fixed typo "segway" to "segue" in template layout matching.
- Type annotations use `Optional[]` consistently in `exceptions.py`.

## [0.5.0] - 2026-01-20

### Added
- Auto-style selection with the `--auto-style` flag.
- Outline preview flow with `--outline-only` and `--confirm-outline`.
- Five new creative themes: `chalkboard`, `blueprint`, `sketch`, `retro`, and `neon`.
- `style_selector` module with English and Chinese keyword support.
- Web UI enhancements for automatic style recommendation.
- Generator helpers for outline-only workflows.

### Changed
- Updated README with new CLI flags and 18 visual themes.
- Total built-in visual themes increased from 13 to 18.

## [0.4.0] - 2026-01-11

### Added
- Higher-density content prompts with stronger bullets, data, and statistics.
- Modern styling system with gradient backgrounds, accent lines, and stronger typography.
- New slide types for fullscreen images and key statistics.
- Five premium themes: `luxury`, `magazine`, `tech_gradient`, `ocean`, and `sunset`.
- Smarter layout handling across content, statistics, image, and chart slides.

### Changed
- Updated `SlideConfig` to support `slide_type` and `statistics`.
- Refactored `ppt_renderer` to support cleaner XML-based gradient fills.

## [0.3.0] - 2025-12-31

### Added
- PyPI packaging with `pyproject.toml` and a CLI entry point.
- Automated safety audit hooks for sensitive data and unwanted files.
- Comprehensive pytest suite.
- Documentation workflow support.
- Expanded `.gitignore`.
- Cleaner repository history after log cleanup.
- Clearer `.env.example`.

### Removed
- Old utility scripts and obsolete log files from the project root.

### Changed
- Added `streamlit`, `pytest`, and `pytest-cov`.

## [0.2.0] - 2025-12-30

### Added
- Anthropic Claude provider with retry logic.
- Wikipedia integration.
- Bar, pie, line, and column chart generation.
- Four visual themes: `corporate`, `academic`, `startup`, and `dark`.
- Progress indicators.
- Custom exceptions.
- Configurable logging.

### Changed
- Dynamic retry delays from config.
- Improved image download stability.

### Fixed
- Missing `import os` in `ppt_renderer.py`.
- Citations slide styling.

## [0.1.0] - 2025-12-30

### Added
- Initial release with core functionality.
- OpenAI and Google Gemini providers.
- Mock provider for testing.
- DuckDuckGo research integration.
- Four visual themes.
- Six sample presentations.

[Unreleased]: https://github.com/yeasy/autoppt/compare/v0.5.1...HEAD
[0.5.1]: https://github.com/yeasy/autoppt/compare/v0.5...v0.5.1
[0.5.0]: https://github.com/yeasy/autoppt/compare/v0.4...v0.5
[0.4.0]: https://github.com/yeasy/autoppt/compare/v0.3...v0.4
[0.3.0]: https://github.com/yeasy/autoppt/compare/v0.2...v0.3
[0.2.0]: https://github.com/yeasy/autoppt/compare/v0.1...v0.2
[0.1.0]: https://github.com/yeasy/autoppt/releases/tag/v0.1
