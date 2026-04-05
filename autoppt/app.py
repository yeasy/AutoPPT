#!/usr/bin/env python3
"""
AutoPPT Web Interface

Run with: streamlit run autoppt/app.py
"""
import html as html_mod
import os
import tempfile
import logging
import time

import streamlit as st

from . import __version__
from .config import Config
from .data_types import SlideLayout
from .exceptions import APIKeyError, AutoPPTError, RateLimitError
from .llm_provider import get_provider_models, get_supported_providers
from .style_selector import auto_select_style, get_all_styles, get_style_description

logger = logging.getLogger(__name__)

Config.initialize()

WORKBENCH_LAYOUT_OPTIONS = {
    "Keep current layout": None,
    "Content": SlideLayout.CONTENT,
    "Two column": SlideLayout.TWO_COLUMN,
    "Comparison": SlideLayout.COMPARISON,
    "Quote": SlideLayout.QUOTE,
    "Statistics": SlideLayout.STATISTICS,
    "Chart": SlideLayout.CHART,
    "Image": SlideLayout.IMAGE,
}

SESSION_DEFAULTS: dict[str, object] = {
    "generated_deck_spec": None,
    "generated_file_bytes": None,
    "generated_filename": None,
    "generated_quality_issues": [],
    "generated_provider": "mock",
    "generated_model": None,
    "generated_style": "minimalist",
    "generated_language": "English",
}
for session_key, default_value in SESSION_DEFAULTS.items():
    if session_key not in st.session_state:
        st.session_state[session_key] = list(default_value) if isinstance(default_value, list) else default_value


def _editable_slide_options(deck_spec):
    options = []
    if not deck_spec:
        return options
    for index, slide in enumerate(deck_spec.slides):
        if not slide.editable or slide.layout in {SlideLayout.TITLE, SlideLayout.SECTION, SlideLayout.CITATIONS}:
            continue
        options.append((index, f"Slide {index + 1}: {slide.title} [{slide.layout.value}]"))
    return options


def _render_deck_file(remix_gen, deck_spec, filename):
    with tempfile.TemporaryDirectory(prefix="autoppt-remix-") as output_dir:
        safe_name = os.path.basename(filename or "autoppt_remix.pptx") or "autoppt_remix.pptx"
        output_file = os.path.join(output_dir, safe_name)
        remix_gen.save_deck(deck_spec, output_file)
        with open(output_file, "rb") as file_handle:
            return file_handle.read()

st.set_page_config(
    page_title="AutoPPT - AI Presentation Generator",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stButton>button {
        width: 100%;
        height: 3rem;
        font-size: 1.1rem;
        font-weight: bold;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown('<div class="main-header">🚀 AutoPPT</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Generate Professional Presentations with AI</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Configuration")

    provider_options = get_supported_providers()
    provider = st.selectbox(
        "🤖 AI Provider",
        options=provider_options,
        index=provider_options.index("mock") if "mock" in provider_options else 0,
        help="Select the AI provider. Use mock for testing without API keys.",
    )

    model = None
    if provider != "mock":
        model = st.selectbox(
            "🧠 Model",
            options=get_provider_models(provider),
            help="Select the specific model to use.",
        )

    style = st.selectbox(
        "🎨 Visual Theme",
        options=get_all_styles(),
        index=0,
        help="Choose the visual theme for your presentation.",
    )

    auto_style = st.checkbox(
        "✨ Auto-detect style",
        value=False,
        help="Automatically select the best style based on your topic keywords",
    )

    slides_count = st.slider(
        "📊 Number of Slides",
        min_value=3,
        max_value=20,
        value=6,
        help="Target number of content slides.",
    )

    language = st.text_input(
        "🌐 Language",
        value="English",
        max_chars=50,
        help="Output language for the presentation content.",
    )

    st.divider()
    st.header("🔑 API Keys")
    st.write("OpenAI:", "✅ Set" if Config.OPENAI_API_KEY else "❌ Not set")
    st.write("Google:", "✅ Set" if Config.GOOGLE_API_KEY else "❌ Not set")
    st.write("Anthropic:", "✅ Set" if Config.ANTHROPIC_API_KEY else "❌ Not set")

    if provider != "mock" and not Config.has_api_key(provider):
        st.warning(f"⚠️ API key for {provider} is not set. Please configure it in .env file or switch to mock.")

col1, col2 = st.columns([2, 1])

with col1:
    st.header("📝 Presentation Topic")
    topic = st.text_area(
        "Enter your presentation topic",
        placeholder="e.g., The Future of Artificial Intelligence\n人工智能的发展历史\nClimate Change and Renewable Energy",
        height=100,
        max_chars=500,
        label_visibility="collapsed",
    )

effective_style = style
style_display = style
if auto_style and topic:
    effective_style = auto_select_style(topic, language)
    style_display = f"{effective_style} ✨ (auto)"

with col2:
    st.header("📋 Preview")
    _preview_topic = html_mod.escape(topic) if topic else "Not specified"
    _preview_language = html_mod.escape(language) if language else "English"
    _preview_style = html_mod.escape(style_display) if style_display else "default"
    _preview_provider = html_mod.escape(provider) if provider else "openai"
    st.info(
        f"""
**Topic:** {_preview_topic}

**Provider:** {_preview_provider}

**Style:** {_preview_style}

**Slides:** {slides_count}

**Language:** {_preview_language}
"""
    )

    if auto_style and topic:
        st.caption(f"💡 {get_style_description(effective_style)}")

st.divider()
generate_button = st.button("🚀 Generate Presentation", type="primary", use_container_width=True)

if generate_button:
    if not topic:
        st.error("❌ Please enter a presentation topic.")
    elif provider != "mock" and not Config.has_api_key(provider):
        st.error(f"❌ API key for {provider} is not set. Please configure it in .env file.")
    else:
        with st.spinner("🔄 Generating your presentation... This may take a few minutes."):
            try:
                from .generator import Generator

                safe_topic = "".join(char for char in topic if char.isalnum() or char in (" ", "-", "_"))[:50].strip() or "presentation"
                progress_bar = st.progress(0, text="Initializing generator...")

                with tempfile.TemporaryDirectory(prefix="autoppt-web-") as output_dir:
                    output_file = os.path.join(output_dir, f"{safe_topic.replace(' ', '_')}.pptx")
                    with Generator(provider_name=provider, model=model) as gen:
                        progress_bar.progress(10, text="Generating outline...")
                        result = gen.generate(
                            topic=topic,
                            style=effective_style,
                            output_file=output_file,
                            slides_count=slides_count,
                            language=language,
                        )
                        with open(result, "rb") as file_handle:
                            file_bytes = file_handle.read()
                        deck_spec = gen.last_deck_spec
                        quality_report = gen.last_quality_report

                progress_bar.progress(100, text="✅ Complete!")
                time.sleep(0.5)
                progress_bar.empty()

                st.session_state.generated_deck_spec = deck_spec
                st.session_state.generated_file_bytes = file_bytes
                st.session_state.generated_filename = f"{safe_topic.replace(' ', '_')}.pptx"
                st.session_state.generated_quality_issues = list(quality_report.issues)
                st.session_state.generated_provider = provider
                st.session_state.generated_model = model
                st.session_state.generated_style = effective_style
                st.session_state.generated_language = language

                st.success("🎉 Presentation generated successfully!")
                st.info(f"📁 File size: {len(file_bytes) / 1024:.1f} KB")
                if quality_report.has_issues:
                    with st.expander(f"⚠️ Deck QA detected {len(quality_report.issues)} issue(s)"):
                        for issue in quality_report.issues:
                            st.write(f"Slide {issue.slide_index}: {issue.message}")
                st.download_button(
                    label="📥 Download Presentation",
                    data=file_bytes,
                    file_name=f"{safe_topic.replace(' ', '_')}.pptx",
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    use_container_width=True,
                )
            except APIKeyError as exc:
                st.error(f"API key error for {exc.provider}: {exc.message}")
            except RateLimitError as exc:
                st.error(f"Rate limit exceeded for {exc.provider}: {exc.message}")
            except AutoPPTError as exc:
                logger.exception("Error generating presentation")
                st.error("Generation error. Please check logs or try again.")
            except Exception:
                logger.exception("Unexpected error generating presentation")
                st.error("Unexpected error. Please check logs or try again.")

if st.session_state.generated_file_bytes:
    st.divider()
    st.header("📦 Current Deck")
    st.info(f"Latest file size: {len(st.session_state.generated_file_bytes) / 1024:.1f} KB")
    if st.session_state.generated_quality_issues:
        with st.expander(f"⚠️ Deck QA detected {len(st.session_state.generated_quality_issues)} issue(s)"):
            for issue in st.session_state.generated_quality_issues:
                st.write(f"Slide {issue.slide_index}: {issue.message}")
    st.download_button(
        label="📥 Download Current Presentation",
        data=st.session_state.generated_file_bytes,
        file_name=st.session_state.generated_filename or "autoppt.pptx",
        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        use_container_width=True,
    )

editable_options = _editable_slide_options(st.session_state.generated_deck_spec)
if editable_options:
    st.divider()
    st.header("🛠️ Slide Workbench")
    selected_label = st.selectbox(
        "Select a slide to update",
        options=[label for _, label in editable_options],
        key="remix_slide_selector",
    )
    selected_index = next(
        (index for index, label in editable_options if label == selected_label),
        editable_options[0][0] if editable_options else 0,
    )
    selected_slide = st.session_state.generated_deck_spec.slides[selected_index]
    target_layout_label = st.selectbox(
        "Preferred layout",
        options=list(WORKBENCH_LAYOUT_OPTIONS.keys()),
        key="remix_layout_selector",
    )
    remix_instruction = st.text_area(
        "Remix instruction",
        placeholder="e.g., Turn this into a cleaner comparison with sharper metrics and fewer bullets.",
        height=100,
        key="remix_instruction",
    )
    st.caption(selected_slide.layout_rationale or "This slide can be regenerated from its saved plan and source config.")
    action_col1, action_col2 = st.columns(2)
    regenerate_button = action_col1.button("🔄 Regenerate Selected Slide", use_container_width=True)
    remix_button = action_col2.button("♻️ Remix Selected Slide", use_container_width=True)

    if regenerate_button or remix_button:
        with st.spinner("🔄 Updating selected slide..."):
            try:
                from .generator import Generator

                current_deck = st.session_state.generated_deck_spec
                with Generator(
                    provider_name=st.session_state.generated_provider,
                    model=st.session_state.generated_model,
                ) as remix_gen:
                    target_layout = WORKBENCH_LAYOUT_OPTIONS[target_layout_label]
                    if remix_button:
                        updated_deck = remix_gen.remix_slide(
                            deck_spec=current_deck,
                            slide_index=selected_index,
                            instruction=remix_instruction.strip(),
                            style=st.session_state.generated_style,
                            language=st.session_state.generated_language,
                            target_layout=target_layout,
                        )
                    else:
                        updated_deck = remix_gen.regenerate_slide(
                            deck_spec=current_deck,
                            slide_index=selected_index,
                            style=st.session_state.generated_style,
                            language=st.session_state.generated_language,
                            target_layout=target_layout,
                        )
                    remixed_bytes = _render_deck_file(
                        remix_gen,
                        updated_deck,
                        st.session_state.generated_filename or "autoppt_remix.pptx",
                    )

                    remix_deck_spec = updated_deck
                    remix_quality_issues = list(remix_gen.last_quality_report.issues)
                    st.session_state.generated_deck_spec = remix_deck_spec
                    st.session_state.generated_file_bytes = remixed_bytes
                    st.session_state.generated_quality_issues = remix_quality_issues
                    action_label = "regenerated" if regenerate_button else "remixed"
                    st.success(f"✅ Selected slide {action_label} successfully.")
                    st.rerun()
            except APIKeyError as exc:
                st.error(f"API key error for {exc.provider}: {exc.message}")
            except RateLimitError as exc:
                st.error(f"Rate limit exceeded for {exc.provider}: {exc.message}")
            except AutoPPTError as exc:
                logger.exception("Error updating slide")
                st.error("Slide update error. Please check logs or try again.")
            except Exception:
                logger.exception("Unexpected error updating slide")
                st.error("Unexpected error. Please check logs or try again.")

st.divider()
st.markdown(
    f"""
<div style="text-align: center; color: #888; font-size: 0.9rem;">
    <p>AutoPPT v{html_mod.escape(__version__)} | <a href="https://github.com/yeasy/autoppt">GitHub</a> | Apache 2.0 License</p>
</div>
""",
    unsafe_allow_html=True,
)
