# AutoPPT 🚀

![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![Status](https://img.shields.io/badge/status-active-success.svg)

**Generate Professional Presentations in Seconds using AI.**

**AutoPPT** combines the power of advanced LLMs (OpenAI, Anthropic, Google) with real-time web research to create structured, researched, and visually styled PowerPoint presentations automatically.

---

## ✨ Features

- **🧱 Hierarchical Sectioning**: Unlike basic generators, AutoPPT structures content into logical sections and chapters for a professional narrative flow.
- **🎨 8 Visual Themes**: Technology, Nature, Creative, Minimalist, Corporate, Academic, Startup, and Dark mode.
- **🤖 Research-Driven Content**: Real-time web searching + Wikipedia integration for accurate data and citations.
- **📊 Chart Generation**: Automatically create bar, pie, line, and column charts from data.
- **🖼️ Smart Visuals**: Integrated image search with intelligent layout adjustment.
- **🔌 Multi-Provider Support**: OpenAI (GPT-4o), Google (Gemini 2.0), Anthropic (Claude 3.5).
- **🧪 Mock Provider**: Instant testing without API keys using `--provider mock`.
- **📈 Progress Indicators**: Real-time progress bars during generation.
- **🛡️ Privacy-First & Open Source**: Run locally. Your data stays with you.

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
# ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Usage

```bash
# Generate with default settings (OpenAI, 10 slides)
python main.py --topic "The Future of Quantum Computing"

# Use Google Gemini with a specific theme
python main.py --topic "Healthy Living" --provider google --style nature --slides 8

# Use Anthropic Claude with dark theme
python main.py --topic "AI Ethics" --provider anthropic --style dark

# Test without API keys
python main.py --topic "Test Presentation" --provider mock --slides 5

# Verbose mode for debugging
python main.py --topic "Debug Test" --provider mock -v
```

## 🛠️ Configuration Options

| Flag | Description | Default |
|------|-------------|---------|
| `--topic` | The presentation subject. | **Required** |
| `--provider` | AI backend: `openai`, `google`, `anthropic`, or `mock`. | `openai` |
| `--model` | Specific model name (e.g., `gpt-4o`, `gemini-2.0-flash`). | Provider default |
| `--slides` | Target number of slides. | `10` |
| `--language` | Output language (e.g., `Chinese`, `English`, `French`). | `English` |
| `--style` | Visual theme (see below). | `minimalist` |
| `--output` | Custom output file path. | `output/<topic>.pptx` |
| `-v, --verbose` | Enable debug logging. | `false` |

### 🎨 Visual Themes

| Theme | Description |
|-------|-------------|
| `minimalist` | Clean grayscale, high readability |
| `technology` | Dark mode, blueprint blue |
| `nature` | Earthy greens, serif fonts |
| `creative` | Vibrant magenta/purple |
| `corporate` | Professional blue tones |
| `academic` | Traditional maroon/cream |
| `startup` | Modern orange accents |
| `dark` | Cyan/purple on dark background |

## 📊 Chart Generation

AutoPPT can automatically generate charts when the LLM identifies numerical data. Supported types:
- Bar charts
- Column charts
- Pie charts
- Line charts

## 📂 Samples

See AutoPPT in action with substantive, research-driven content:

- [**AI & Technology (CN)**](samples/cn_tech.pptx)
- [**Healthy Living (CN)**](samples/cn_life.pptx)
- [**Renaissance Art (CN)**](samples/cn_art.pptx)
- [**AI & Technology (EN)**](samples/en_tech.pptx)
- [**Healthy Living (EN)**](samples/en_life.pptx)
- [**Renaissance Art (EN)**](samples/en_art.pptx)

## 🤝 Contributing

We welcome contributions! To contribute:

1. **Fork** the repository
2. **Clone** your fork: `git clone https://github.com/your-username/autoppt.git`
3. **Create a branch**: `git checkout -b feature/awesome-feature`
4. **Commit changes**: `git commit -m "Add awesome feature"`
5. **Push**: `git push origin feature/awesome-feature`
6. **Open a Pull Request**

### Ideas for Contribution
- Add support for more LLM providers (DeepSeek, Mistral, Ollama)
- Implement PDF export
- Add Google Slides API integration
- Create a web UI with Streamlit/Gradio
- Add more visual themes

## 📜 License

Apache 2.0 - See [LICENSE](LICENSE) for details.

## 📝 Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.