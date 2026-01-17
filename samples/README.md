# AutoPPT Samples

[中文说明](README.zh-CN.md)

This folder stores committed decks used for documentation, visual review, and product validation.

## Showcase Samples

These files are part of the repository and represent the current presentation quality.

- [cn_tech.pptx](cn_tech.pptx): Chinese technology deck
- [cn_life.pptx](cn_life.pptx): Chinese healthy-living deck
- [cn_art.pptx](cn_art.pptx): Chinese art deck
- [cn_visual_showcase.pptx](cn_visual_showcase.pptx): Chinese high-fidelity image showcase
- [en_tech.pptx](en_tech.pptx): English technology deck
- [en_life.pptx](en_life.pptx): English healthy-living deck
- [en_art.pptx](en_art.pptx): English art deck
- [en_visual_showcase.pptx](en_visual_showcase.pptx): English high-fidelity image showcase

Current slide counts:

- `cn_tech.pptx`: 9
- `cn_life.pptx`: 8
- `cn_art.pptx`: 8
- `cn_visual_showcase.pptx`: 8
- `en_tech.pptx`: 9
- `en_life.pptx`: 8
- `en_art.pptx`: 8
- `en_visual_showcase.pptx`: 8

## Feature Samples

These decks focus on workflow and feature validation rather than visual polish.

- [feature_layouts_en.pptx](feature_layouts_en.pptx): English richer layout gallery
- [feature_layouts_cn.pptx](feature_layouts_cn.pptx): Chinese richer layout gallery
- [feature_workbench.pptx](feature_workbench.pptx): Slide regenerate and remix workflow sample

## Refresh Samples

Refresh all samples deterministically:

```bash
python scripts/generate_samples.py --category all --output-dir samples
```

Generate one sample by id:

```bash
python scripts/generate_sample.py en_visual_showcase --output-dir samples
python scripts/generate_sample.py feature_workbench --output-dir samples
```

Refresh README preview assets:

```bash
python scripts/generate_readme_previews.py --output-dir docs/assets
```

Current sample ids:

`cn_tech`, `cn_life`, `cn_art`, `cn_visual_showcase`, `en_tech`, `en_life`, `en_art`, `en_visual_showcase`, `feature_layouts_en`, `feature_layouts_cn`, `feature_workbench`
