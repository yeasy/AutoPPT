# Changelog

All notable changes to AutoPPT will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Default OpenAI model updated from `gpt-4.1` to `gpt-5.4-mini`.
- OpenAI model catalog reordered to list GPT-5.4 series first; added `o3`, `o3-pro`, `o3-mini`, `o4-mini` reasoning models and `gpt-5.4-pro`.
- Anthropic Haiku model ID changed from snapshot `claude-haiku-4-5-20251001` to alias `claude-haiku-4-5`.
- OpenAI `generate_structure` now logs a warning when called with o-series reasoning models that may have limited structured output support.
- `SlideConfig.bullets` now defaults to an empty list instead of being required, preventing `ValidationError` for non-content slide types.
- `StatisticData.value` and `StatisticData.label` now enforce `max_length` constraints (50 and 200 respectively).
- Web UI error handlers now show differentiated, actionable messages for API key errors, rate limits, and generation failures instead of a generic error.
- `TemplateHandler.get_best_layout_for_type` now has mappings for comparison, quote, chart, statistics, citations, and image slide types.
- Modernized type annotations across all modules to use PEP 604 union syntax and built-in generics (Python 3.10+).
- Research context is now truncated to 100,000 characters to prevent excessive prompt sizes.
- `generate_outline` now raises `RuntimeError` when called on a closed `Generator` instance.

### Fixed
- `slide_from_config` for COMPARISON and TWO_COLUMN slides now treats explicit `left_bullets`/`right_bullets` atomically instead of mixing them with split-from-bullets via falsy `or` evaluation.
- `slide_from_config` now demotes COMPARISON and TWO_COLUMN slides to CONTENT when either column is empty instead of creating a lopsided slide.
- `apply_plan` now falls back to CONTENT when a COMPARISON or TWO_COLUMN plan has insufficient bullets for two columns.
- `apply_plan` now demotes CHART to CONTENT when no `chart_data` is provided, and STATISTICS to CONTENT when no `statistics` data is provided.
- `apply_plan` now logs a warning when a layout-locked COMPARISON or TWO_COLUMN is demoted to CONTENT due to insufficient bullets.
- `apply_plan` now logs an info message when an inferred COMPARISON or TWO_COLUMN is demoted to CONTENT, aiding debugging.
- `_safe_layout_from_plan` now uses `is None` check instead of falsy check for `SlidePlan`.
- `remix_slide` now logs a warning for unsupported target layouts instead of silently returning a copy.
- OpenAI o-series model detection tightened from `startswith("o")` to `startswith(("o3", "o4"))` to prevent false positives.
- `style_selector` now validates (in debug mode) at import time that `STYLE_DESCRIPTIONS` and `STYLE_KEYWORDS` keys match `THEME_DEFINITIONS`.
- `RateLimitError` now normalizes negative `retry_after` values to `None` instead of showing misleading countdown messages.
- Anthropic `generate_structure` JSON fallback now scans for both `{` and `[` delimiters, supporting list-rooted schemas.
- `MockProvider` topic and hint extraction now preserves original casing instead of lowercasing and title-casing.
- `TemplateHandler.get_best_layout_for_type` now falls back to layout index 1 (content) instead of 0 (title) for unknown slide types.
- `TemplateHandler.__init__` now checks for `..` path traversal before resolving, consistent with `Generator._validate_file_path`.
- Slide workbench `selected_index` fallback now uses the first editable slide instead of index 0 (title slide).
- Architecture docs now document all modules including `data_types.py`, `exceptions.py`, `deck_qa.py`, `thumbnail.py`, and `sample_library.py`.

## [0.5.3] - 2026-04-02

### Changed
- Default OpenAI model updated from `gpt-4o` to `gpt-4.1`.
- Default Anthropic model updated from `claude-sonnet-4-5-20250514` to `claude-sonnet-4-6`.
- Default Google model updated from `gemini-2.0-flash` to `gemini-2.5-flash`.
- Provider model lists updated with current model identifiers (added `gpt-4.1`, `gpt-5.4` series, `gemini-3-flash-preview`, `gemini-2.5-flash-lite`, `gemini-3.1-pro-preview`, `gemini-3.1-flash-lite-preview`).
- `auto_select_style` now covers `magazine`, `tech_gradient`, `ocean`, and `sunset` themes (previously unreachable by auto-detection).
- `_sanitize_prompt_field` now handles `None` and non-string inputs defensively.
- `DeckQA.analyze()` now reports an `empty_deck` issue instead of silently passing.
- `load_deck_spec` field size check now also validates `statistics` lists.
- `Config.configure_logging` is now thread-safe (called inside the class lock).
- Web UI uses `with Generator(...)` context manager consistently instead of manual `try/finally`.

### Fixed
- Research context sanitization now strips control characters (including null bytes) before further processing.
- Removed unreachable dead code in article fetch redirect handling.
- `PPTRenderer.save()` now writes to the resolved path to close a TOCTOU gap with symlinks.
- `fetch_article_content` rejects non-text Content-Type responses to prevent binary data reaching the HTML parser.
- `PIL.Image.MAX_IMAGE_PIXELS` set globally to 25M to prevent decompression bombs before full decode.
- Aggregated research context is now capped at 100K characters to prevent memory exhaustion from large web results.
- `_coerce_slide_type` now catches unmatched `SlideLayout` to `SlideType` conversion with a clear error message.
- `add_chart_slide` guards against empty data after length-mismatch truncation.
- Sample library sync check wrapped in `if __debug__` to avoid crashing production on partial deploys.
- `download_image` now writes to the resolved path consistently, closing a TOCTOU gap.
- CLI argument validation now runs before topic is used for path computation or style detection.
- Removed dead `user_provided_output` variable in CLI entry point.
- Web UI preview panel escapes user-supplied topic, language, style, and provider to prevent markdown injection.
- `_is_safe_url` now unwraps IPv6-mapped IPv4 addresses before checking for private ranges.
- `_is_safe_url` now blocks multicast and unspecified addresses (0.0.0.0, 224.0.0.0/4).
- `TemplateHandler` now validates paths against `BLOCKED_SYSTEM_PREFIXES`.
- CLI and thumbnail output paths are now validated against `BLOCKED_SYSTEM_PREFIXES`.
- `generate_thumbnails` now propagates `ValueError` and `FileNotFoundError` instead of swallowing them.
- Production `assert` in `fetch_article_content` replaced with explicit None check.
- `_generate_from_outline_internal` no longer creates a spurious directory when `output_file` is a bare filename.
- Web UI `_render_deck_file` guards against `os.path.basename` returning empty string on trailing-slash filenames.
- Anthropic JSON `raw_decode` fallback now logs a warning to aid debugging.
- Renamed shadowed `block` variable in Anthropic code fence extraction to `fenced`.
- `_looks_like_image` heuristic tightened to avoid false positives on common business terms like "experience", "journey", "product".
- `_infer_comparison_titles` now strips leading dots and trailing whitespace from "vs." splits (e.g., "Cloud vs. On-Premise" no longer produces a leading dot in the right title).
- `comparison_slide` now coerces string `points` values into a single-element list instead of iterating character-by-character.
- Anthropic `raw_decode` fallback now picks the largest JSON object in the response, reducing the chance of matching a small nested fragment.
- `_infer_from_content` no longer promotes content slides with `image_query` to IMAGE layout when bullets are present, preventing loss of bullet content.

## [0.5.2] - 2026-03-28

### Added
- Slide planning layer with `SlidePlan` and `slide_planner.py`.
- Editable `DeckSpec` workflow with save, load, regenerate, and remix helpers.
- Web slide workbench for post-generation single-slide operations.
- Deterministic sample library and README preview generation.
- Prompt input sanitization strips control characters and truncates user-supplied fields.
- `ChartData` Pydantic validator ensures categories and values have matching lengths.

### Changed
- Richer layout flow now treats comparison, two-column, and quote slides as first-class editable layouts.
- Rendering now uses theme tokens for spacing, panels, image treatment, and typography.
- Repository docs are split into separate English and Chinese files where needed.
- Slide-building exception catch narrowed from `Exception` to `(AutoPPTError, ValueError)`.
- Gradient application failures now log at WARNING instead of DEBUG.
- Render slide dispatch uses `elif` for clearer fallback control flow.

### Fixed
- `_is_local_base_url` now uses URL parsing instead of substring matching to prevent bypasses.
- Image downloads validate each redirect in the chain to prevent redirect-based SSRF.
- Blank layout selection searches by name instead of hardcoded index, preventing `IndexError` on custom templates.
- Incomplete QUOTE/STATISTICS/IMAGE/CHART slides log a warning before falling back to content layout.
- Streaming HTTP response leak in researcher fixed with `try/finally` block.
- Double-close safety in `Generator.close()` prevents repeated cleanup failures.
- Anthropic code fence extraction handles language-tagged fences like ` ```python `.
- `build_sample_deck()` raises `ValueError` for `None` asset directory instead of silently leaking temp dirs.
- Subprocess `--` separator in thumbnail generation prevents flag injection from filenames.

### Removed
- Redundant `chart_mismatch` QA check superseded by `ChartData` Pydantic validator.

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

[Unreleased]: https://github.com/yeasy/autoppt/compare/v0.5.3...HEAD
[0.5.3]: https://github.com/yeasy/autoppt/compare/v0.5.2...v0.5.3
[0.5.2]: https://github.com/yeasy/autoppt/compare/v0.5.1...v0.5.2
[0.5.1]: https://github.com/yeasy/autoppt/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/yeasy/autoppt/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/yeasy/autoppt/compare/v0.3...v0.4.0
[0.3.0]: https://github.com/yeasy/autoppt/compare/v0.2...v0.3
[0.2.0]: https://github.com/yeasy/autoppt/compare/v0.1...v0.2
[0.1.0]: https://github.com/yeasy/autoppt/releases/tag/v0.1
