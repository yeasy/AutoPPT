# PowerPoint 模板说明

[English README](README.md)

本目录用于存放 AutoPPT 可复用的自定义 `.pptx` 模板。生成出来的 deck 应放在 `output/`，不要放在这里。

## 使用方式

通过 `--template` 参数指定你自己的模板：

```bash
autoppt --topic "Your Topic" --template templates/your-template.pptx
```

## 如何制作模板

1. 在 PowerPoint、Google Slides 或 LibreOffice Impress 中创建新演示文稿。
2. 在幻灯片母版中定义希望 AutoPPT 使用的布局。
3. 配置品牌色、字体和 Logo 等资产。
4. 将文件保存为 `.pptx` 并放到本目录。

## 推荐布局

当模板中包含以下布局时，AutoPPT 的兼容性通常最好：

- 标题页
- 章节过渡页
- 带标题和正文占位符的标准内容页
- 双栏页
- 适合图表或图片布局的空白页

## 建议

- 尽量让不同布局中的占位符位置保持一致。
- 使用高分辨率 Logo 和品牌素材。
- 在共享模板前，先用 mock 模式做一次验证：

```bash
autoppt --topic "Template Test" \
  --template templates/your-template.pptx \
  --provider mock \
  --output output/template-test.pptx
```
