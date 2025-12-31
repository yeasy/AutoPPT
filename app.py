#!/usr/bin/env python3
"""
AutoPPT Web Interface

A Streamlit-based web UI for generating AI-powered presentations.
Run with: streamlit run app.py
"""
import streamlit as st
import os
import tempfile
import time
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="AutoPPT - AI Presentation Generator",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
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
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #E8F5E9;
        border: 1px solid #4CAF50;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header">🚀 AutoPPT</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Generate Professional Presentations with AI</div>', unsafe_allow_html=True)

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Provider selection
    provider = st.selectbox(
        "🤖 AI Provider",
        options=["mock", "google", "openai", "anthropic"],
        index=0,
        help="Select the AI provider. Use 'mock' for testing without API keys."
    )
    
    # Model selection (only for non-mock providers)
    model = None
    if provider != "mock":
        model_options = {
            "openai": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
            "google": ["gemini-2.0-flash", "gemini-1.5-pro"],
            "anthropic": ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229"]
        }
        model = st.selectbox(
            "🧠 Model",
            options=model_options.get(provider, []),
            help="Select the specific model to use."
        )
    
    # Style selection
    style = st.selectbox(
        "🎨 Visual Theme",
        options=[
            "minimalist", "technology", "nature", "creative",
            "corporate", "academic", "startup", "dark"
        ],
        index=0,
        help="Choose the visual theme for your presentation."
    )
    
    # Slides count
    slides_count = st.slider(
        "📊 Number of Slides",
        min_value=3,
        max_value=20,
        value=6,
        help="Target number of content slides."
    )
    
    # Language
    language = st.text_input(
        "🌐 Language",
        value="English",
        help="Output language for the presentation content."
    )
    
    st.divider()
    
    # API Key status
    st.header("🔑 API Keys")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    openai_key = os.getenv("OPENAI_API_KEY")
    google_key = os.getenv("GOOGLE_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    
    st.write("OpenAI:", "✅ Set" if openai_key else "❌ Not set")
    st.write("Google:", "✅ Set" if google_key else "❌ Not set")
    st.write("Anthropic:", "✅ Set" if anthropic_key else "❌ Not set")
    
    if provider != "mock" and not any([openai_key, google_key, anthropic_key]):
        st.warning("⚠️ No API keys found. Please set them in .env file or use 'mock' provider.")

# Main content area
col1, col2 = st.columns([2, 1])

with col1:
    st.header("📝 Presentation Topic")
    topic = st.text_area(
        "Enter your presentation topic",
        placeholder="e.g., The Future of Artificial Intelligence\n人工智能的发展历史\nClimate Change and Renewable Energy",
        height=100,
        label_visibility="collapsed"
    )

with col2:
    st.header("📋 Preview")
    st.info(f"""
    **Topic:** {topic or 'Not specified'}
    
    **Provider:** {provider}
    
    **Style:** {style}
    
    **Slides:** {slides_count}
    
    **Language:** {language}
    """)

st.divider()

# Generate button
generate_button = st.button("🚀 Generate Presentation", type="primary", use_container_width=True)

if generate_button:
    if not topic:
        st.error("❌ Please enter a presentation topic.")
    else:
        # Check API key for non-mock providers
        if provider != "mock":
            key_map = {
                "openai": openai_key,
                "google": google_key,
                "anthropic": anthropic_key
            }
            if not key_map.get(provider):
                st.error(f"❌ API key for {provider} is not set. Please configure it in .env file.")
                st.stop()
        
        # Generate presentation
        with st.spinner("🔄 Generating your presentation... This may take a few minutes."):
            try:
                from core.generator import Generator
                
                # Create output directory
                output_dir = tempfile.mkdtemp()
                safe_topic = "".join(c for c in topic if c.isalnum() or c in (' ', '-', '_'))[:50]
                output_file = os.path.join(output_dir, f"{safe_topic.replace(' ', '_')}.pptx")
                
                # Progress tracking
                progress_bar = st.progress(0, text="Initializing generator...")
                
                # Initialize generator
                gen = Generator(provider_name=provider, model=model)
                progress_bar.progress(10, text="Generating outline...")
                
                # Generate presentation
                result = gen.generate(
                    topic=topic,
                    style=style,
                    output_file=output_file,
                    slides_count=slides_count,
                    language=language
                )
                
                progress_bar.progress(100, text="✅ Complete!")
                time.sleep(0.5)
                progress_bar.empty()
                
                # Success message
                st.success("🎉 Presentation generated successfully!")
                
                # File info and download
                file_size = os.path.getsize(result) / 1024  # KB
                st.info(f"📁 File size: {file_size:.1f} KB")
                
                # Download button
                with open(result, "rb") as f:
                    st.download_button(
                        label="📥 Download Presentation",
                        data=f.read(),
                        file_name=f"{safe_topic.replace(' ', '_')}.pptx",
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                        use_container_width=True
                    )
                    
            except Exception as e:
                st.error(f"❌ Error generating presentation: {str(e)}")
                st.exception(e)

# Footer
st.divider()
st.markdown("""
<div style="text-align: center; color: #888; font-size: 0.9rem;">
    <p>AutoPPT v0.3 | <a href="https://github.com/yeasy/autoppt">GitHub</a> | Apache 2.0 License</p>
</div>
""", unsafe_allow_html=True)
