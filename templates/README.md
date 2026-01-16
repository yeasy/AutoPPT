# PowerPoint Templates

[中文说明](README.zh-CN.md)

This directory stores reusable custom `.pptx` templates for AutoPPT. Generated decks belong in `output/`, not here.

## Usage

Use the `--template` flag to render a deck with your own template:

```bash
autoppt --topic "Your Topic" --template templates/your-template.pptx
```

## How To Build A Template

1. Create a new presentation in PowerPoint, Google Slides, or LibreOffice Impress.
2. Define a slide master with the layouts you want AutoPPT to target.
3. Apply your brand colors, fonts, and logo assets.
4. Save the file as `.pptx` and place it in this directory.

## Recommended Layouts

AutoPPT works best when it can identify these layouts:

- Title slide
- Section header
- Standard content slide with title and body placeholders
- Two-column slide
- Blank slide for charts or image-heavy placement

## Tips

- Keep placeholder positions consistent across layouts.
- Use high-resolution logo assets.
- Test the template with mock mode before sharing it:

```bash
autoppt --topic "Template Test" \
  --template templates/your-template.pptx \
  --provider mock \
  --output output/template-test.pptx
```
