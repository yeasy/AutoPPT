# AutoPPT 🚀

![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![Status](https://img.shields.io/badge/status-active-success.svg)
![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)

**Generate Professional Presentations in Seconds using AI.**

**AutoPPT** combines the power of advanced LLMs (OpenAI, Anthropic, Google) with real-time web research to create structured, researched, and visually styled PowerPoint presentations automatically.

---

## ✨ Features

- **🧱 Hierarchical Sectioning**: Structures content into logical sections and chapters.
- **🎨 8 Visual Themes**: Technology, Nature, Creative, Minimalist, Corporate, Academic, Startup, Dark.
- **🤖 Research-Driven Content**: DuckDuckGo + Wikipedia integration for accurate data.
- **📊 Chart Generation**: Automatic bar, pie, line, and column charts.
- **🖼️ Smart Visuals**: Integrated image search with intelligent layout.
- **🔌 Multi-Provider Support**: OpenAI, Google Gemini, Anthropic Claude.
- **🌐 Web UI**: Streamlit-based interface for easy generation.
- **🧪 Mock Provider**: Test without API keys using `--provider mock`.
- **📈 Progress Indicators**: Real-time progress bars during generation.
- **✅ Test Coverage**: Comprehensive pytest test suite.

## 🚀 Quick Start

### 1. Installation

From PyPI:
```bash
pip install autoppt
```

From source:
```bash
git clone https://github.com/yeasy/autoppt.git
cd autoppt
pip install .
```

### 2. Configuration

```bash
cp .env.example .env
# Add your API keys (at least one for real generation)
# OPENAI_API_KEY=sk-...
# GOOGLE_API_KEY=AIza...
# ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Usage

#### Command Line
```bash
# Generate with default settings
autoppt --topic "The Future of AI"

# Use Google Gemini with dark theme
autoppt --topic "Planets in Solar System" --provider google --style dark
```

#### Web UI
```bash
streamlit run autoppt/app.py
```
Then open http://localhost:8501 in your browser.

## 🌐 Web Interface

AutoPPT includes a beautiful Streamlit-based web UI:

- **Easy Configuration**: Select provider, model, theme, and language
- **Real-time Progress**: See generation progress as it happens
- **Direct Download**: Download your PPTX immediately after generation
- **No Coding Required**: Perfect for non-technical users

## 🛠️ Configuration Options

| Flag | Description | Default |
|------|-------------|---------|
| `--topic` | The presentation subject. | **Required** |
| `--provider` | AI backend: `openai`, `google`, `anthropic`, `mock`. | `openai` |
| `--model` | Specific model name. | Provider default |
| `--slides` | Target number of slides. | `10` |
| `--language` | Output language. | `English` |
| `--style` | Visual theme (see below). | `minimalist` |
| `--output` | Custom output file path. | `output/<topic>.pptx` |
| `-v` | Enable debug logging. | `false` |

### 🎨 Visual Themes

| Theme | Style |
|-------|-------|
| `minimalist` | Clean grayscale |
| `technology` | Dark blue |
| `nature` | Earthy greens |
| `creative` | Vibrant colors |
| `corporate` | Professional blue |
| `academic` | Traditional maroon |
| `startup` | Modern orange |
| `dark` | Cyan on dark |

## 🧪 Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=autoppt --cov-report=term-missing

# Run specific test file
pytest tests/test_renderer.py -v
```

## 📂 Samples

- [**AI & Technology (CN)**](samples/cn_tech.pptx)
- [**Healthy Living (CN)**](samples/cn_life.pptx)
- [**Renaissance Art (CN)**](samples/cn_art.pptx)
- [**AI & Technology (EN)**](samples/en_tech.pptx)
- [**Healthy Living (EN)**](samples/en_life.pptx)
- [**Renaissance Art (EN)**](samples/en_art.pptx)

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/awesome`
3. Run tests & safety audit: `pytest && python3 scripts/check_sensitive.py`
4. Commit changes: `git commit -m "feat: Add awesome feature"`
5. Push: `git push origin feature/awesome`
6. Open a Pull Request

## 📜 License

Apache 2.0 - See [LICENSE](LICENSE)

## 📝 Changelog

See [CHANGELOG.md](CHANGELOG.md)