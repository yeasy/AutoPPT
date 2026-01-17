# AutoPPT 样例说明

[English README](README.md)

本目录用于存放已提交到仓库的样例 deck，供文档展示、视觉审阅和产品验证使用。

## Showcase 样例

这些文件会随仓库一起提交，代表当前版本的输出效果。

- [cn_tech.pptx](cn_tech.pptx)：中文科技主题样例
- [cn_life.pptx](cn_life.pptx)：中文健康生活样例
- [cn_art.pptx](cn_art.pptx)：中文艺术主题样例
- [cn_visual_showcase.pptx](cn_visual_showcase.pptx)：中文高保真图片型 showcase
- [en_tech.pptx](en_tech.pptx)：英文科技主题样例
- [en_life.pptx](en_life.pptx)：英文健康生活样例
- [en_art.pptx](en_art.pptx)：英文艺术主题样例
- [en_visual_showcase.pptx](en_visual_showcase.pptx)：英文高保真图片型 showcase

当前页数：

- `cn_tech.pptx`: 9
- `cn_life.pptx`: 8
- `cn_art.pptx`: 8
- `cn_visual_showcase.pptx`: 8
- `en_tech.pptx`: 9
- `en_life.pptx`: 8
- `en_art.pptx`: 8
- `en_visual_showcase.pptx`: 8

## 功能样例

这些 deck 更偏向工作流和功能验证，而不是视觉展示。

- [feature_layouts_en.pptx](feature_layouts_en.pptx)：英文 richer layout 版式样例
- [feature_layouts_cn.pptx](feature_layouts_cn.pptx)：中文 richer layout 版式样例
- [feature_workbench.pptx](feature_workbench.pptx)：单页 regenerate 与 remix 工作流样例

## 刷新样例

确定性刷新全部样例：

```bash
python scripts/generate_samples.py --category all --output-dir samples
```

按 sample id 单独生成：

```bash
python scripts/generate_sample.py en_visual_showcase --output-dir samples
python scripts/generate_sample.py feature_workbench --output-dir samples
```

刷新 README 里的预览图：

```bash
python scripts/generate_readme_previews.py --output-dir docs/assets
```

当前可用 sample id：

`cn_tech`, `cn_life`, `cn_art`, `cn_visual_showcase`, `en_tech`, `en_life`, `en_art`, `en_visual_showcase`, `feature_layouts_en`, `feature_layouts_cn`, `feature_workbench`
