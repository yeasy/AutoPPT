# AutoPPT 🚀

![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![Status](https://img.shields.io/badge/status-active-success.svg)

**Generate Professional Presentations in Seconds using AI.**

**AutoPPT** leverages the power of advanced LLMs (OpenAI, Anthropic, Google) to research, structure, and create PowerPoint presentations on *any* topic automatically.

---

## ✨ Features

- **🤖 AI-Powered Content**: Automatically researches topics and writes professional slide content with citations.
- **🔌 Multi-Provider Support**: Seamlessly switch between OpenAI (GPT-4o), Anthropic (Claude 3.5), and Google (Gemini) models.
- **🧪 Mock Provider**: Test generation instantly without API keys or quota usage using `--provider mock`.
- **🎨 Persona Styles**: Choose from tailored personas like *Minimalist*, *Technology*, *Nature*, or *Creative*.
- **📊 Customizable**: Control slide count, language, specific model, and output details.
- **⚡️ Instant Output**: Get a ready-to-present `.pptx` file in under a minute.

## 🚀 Quick Start

### 1. Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/yeasy/AutoPPT.git
cd AutoPPT
pip install -r requirements.txt
```

### 2. Configuration

Set up your API keys. Copy the example file and add at least one key:

```bash
cp .env.example .env
# Edit .env and add your keys
# Example content for .env:
# OPENAI_API_KEY=sk-proj-xxxx...
# GOOGLE_API_KEY=AIzaSy...
```

### 3. Usage

Generate your first presentation with a single command:

```bash
python main.py --topic "The Future of Artificial Intelligence"
```

## 🛠️ Usage Options

Customize your generation with these powerful flags:

| Flag | Description | Default |
|------|-------------|---------|
| `--topic` | The main subject of your presentation. | **Required** |
| `--provider` | Choose from `openai`, `anthropic`, `google`, or `mock`. | `openai` |
| `--model` | Specify a specific model name (e.g., `gpt-4o`, `gemini-1.5-flash`). | Provider default |
| `--slides` | Number of slides to generate. | `10` |
| `--language` | Target language (e.g., "Spanish", "Chinese"). | `English` |
| `--style` | Tone and structure style (e.g., `Technology`, `Nature`). | `minimalist` |

### Supported Styles
- **Minimalist** (Default): Clean, bullet-point focused, easy to read.
- **Professional**: Business-first tone, suitable for corporate environments.
- **Technology**: Futuristic, data-driven, and innovative focus.
- **Creative**: Engaging narrative structure for storytelling.
- **Nature/Art**: Specialized personas for specific topic domains.

### Examples

Generate a 5-slide presentation on AI in Chinese using Google Gemini:
```bash
python main.py --topic "人工智能的发展" --provider google --slides 5 --language "Chinese"
```

Test with the mock provider (no API key needed):
```bash
python main.py --topic "History of Jazz" --provider mock --slides 3
```

## 📂 Samples

Explore the pre-generated samples in the [samples/](samples/) directory:

- [**AI Future (CN)**](samples/cn_tech.pptx)
- [**Healthy Living (CN)**](samples/cn_life.pptx)
- [**Art History (CN)**](samples/cn_art.pptx)
- [**AI Future (EN)**](samples/en_tech.pptx)
- [**Healthy Living (EN)**](samples/en_life.pptx)
- [**Art History (EN)**](samples/en_art.pptx)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

*Generated with ❤️ by AutoPPT*
