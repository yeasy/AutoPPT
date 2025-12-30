# AutoPPT 🚀

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![Status](https://img.shields.io/badge/status-active-success.svg)

**Generate Professional Presentations in Seconds using AI.**

**AutoPPT** leverages the power of advanced LLMs (OpenAI, Anthropic, Google) to research, structure, and create PowerPoint presentations on *any* topic automatically.

---

## ✨ Features

- **🤖 AI-Powered Content**: Automatically researches topics and writes professional slide content with citations.
- **🔌 Multi-Provider Support**: Seamlessly switch between OpenAI (GPT-4o), Anthropic (Claude 3.5), and Google (Gemini) models.
- **🎨 Smart Styles**: Choose from tailored personas like *Minimalist*, *Professional*, or *Creative*.
- **📊 Customizable**: Control slide count, language, and output details.
- **⚡️ Instant Output**: Get a ready-to-present `.pptx` file in under a minute.

## 🚀 Quick Start

### 1. Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/yourusername/auto_ppt_generator.git
cd auto_ppt_generator
pip install -r requirements.txt
```

### 2. Configuration

Set up your API keys. Copy the example file and add at least one key:

```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
# Example content for .env:
# OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

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
| `--provider` | Choose your AI model: `openai`, `anthropic`, `google`. | `openai` |
| `--slides` | Number of slides to generate. | `10` |
| `--language` | Target language (e.g., "Spanish", "Chinese"). | `English` |
| `--style` | Tone and structure style. | `minimalist` |

### Supported Styles
- **Minimalist** (Default): Clean, bullet-point focused, ease to read.
- **Professional**: Business-first tone, suitable for corporate environments.
- **Creative**: Engaging narrative structure for storytelling.

### Example

Generate a 12-slide presentation on Climate Change in Chinese using Google Gemini:

```bash
python main.py --topic "Climate Change Solutions" --provider google --slides 12 --language "Chinese" --style professional
```

## 📂 Samples

Want to see what it can do without running code? 
[**Download Sample Presentation**](samples/sample.pptx)

## 🤝 Contributing

Contributions are welcome! Please read the contributing guidelines to get started.

---

*Generated with ❤️ by AutoPPT*
