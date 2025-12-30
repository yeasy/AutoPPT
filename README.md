# AutoPPT 🚀

![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![Status](https://img.shields.io/badge/status-active-success.svg)

**Generate Professional Presentations in Seconds using AI.**

**AutoPPT** combines the power of advanced LLMs (OpenAI, Anthropic, Google) with real-time web research to create structured, researched, and visually styled PowerPoint presentations automatically.

---

## ✨ Features

- **🧱 Hierarchical Sectioning**: Unlike basic generators, AutoPPT structures content into logical sections and chapters for a professional narrative flow.
- **🎨 Thematic Styling**: Automatic application of curated color palettes, typography, and background themes (Technology, Nature, Creative, Minimalist).
- **🤖 Research-Driven Content**: Real-time web searching provides accurate data, citations, and comprehensive slide bullets.
- **🖼️ Smart Visuals**: Integrated image search and downloading with intelligent layout adjustment to accommodate graphics.
- **🔌 Multi-Provider Support**: Choose your preferred engine: OpenAI (GPT-5.2), Google (Gemini 3), or Anthropic (Claude 4.5).
- **🧪 Mock Provider**: Instant end-to-end testing without API keys or token costs using `--provider mock`.
- **🛡️ Privacy-First & Open Source**: Run the entire pipeline locally. Your data stays with you, reducing leakage risks compared to proprietary web-based services.

## 🚀 Quick Start

### 1. Installation

```bash
git clone https://github.com/yeasy/autoppt.git
cd autoppt
pip install -r requirements.txt
```

### 2. Configuration

Set up your API keys in a `.env` file:

```bash
cp .env.example .env
# Add your keys (at least one is required for real generation)
# OPENAI_API_KEY=sk-...
# GOOGLE_API_KEY=AIza...
```

### 3. Usage

```bash
# Generate a full presentation (10 slides by default)
python main.py --topic "The Future of Quantum Computing"

# Test instantly with mock data (no API key needed)
python main.py --topic "Space Travel" --provider mock --slides 6
```

## 🛠️ Configuration Options

| Flag | Description | Default |
|------|-------------|---------|
| `--topic` | The presentation subject. | **Required** |
| `--provider` | AI backend: `openai`, `google`, `anthropic`, or `mock`. | `openai` |
| `--model` | Specific model name (e.g., `gemini-3-flash`, `gpt-5.2`). | Default |
| `--slides` | Target number of slides. | `10` |
| `--language` | Output language (e.g., `Chinese`, `English`, `French`). | `English` |
| `--style` | Visual theme: `Technology`, `Nature`, `Creative`, `Minimalist`. | `minimalist` |

### 🎨 Visual Themes
- **Technology**: Dark mode, blueprints blue, futuristic typography.
- **Nature**: Earthy greens, mint backgrounds, classic serif fonts.
- **Creative**: Vibrant magenta/purple accents, artistic layout.
- **Minimalist**: Clean grayscale, white backgrounds, high readability.

## 📂 Samples

See AutoPPT in action (with real content and images):

- [**AI & Robotics (CN)**](samples/cn_tech.pptx)
- [**Healthy Living (CN)**](samples/cn_life.pptx)
- [**Renaissance Art (CN)**](samples/cn_art.pptx)
- [**AI & Robotics (EN)**](samples/en_tech.pptx)
- [**Healthy Living (EN)**](samples/en_life.pptx)
- [**Renaissance Art (EN)**](samples/en_art.pptx)

## 🤝 Contributing

We welcome contributions from the community! To contribute to AutoPPT:

1. **Fork** the repository.
2. **Create a new branch** for your feature or bugfix (`git checkout -b feature/awesome-feature`).
3. **Commit your changes** with descriptive messages.
4. **Push to the branch** (`git push origin feature/awesome-feature`).
5. **Open a [Pull Request](https://github.com/yeasy/autoppt/pulls)** and describe your changes.

If you find any bugs or have feature requests, please open an **[Issue](https://github.com/yeasy/autoppt/issues)**.

### Ideas for Contribution:
- Add support for more LLM providers (e.g., DeepSeek, Mistral).
- Implement more visual themes and layout templates.
- Improve the research algorithm for even deeper content analysis.
- Add support for exporting to other formats (PDF, Google Slides).