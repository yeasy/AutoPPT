from argparse import ArgumentParser
from pathlib import Path

from autoppt.sample_library import render_readme_showcase_previews


def main() -> None:
    parser = ArgumentParser(description="Generate deterministic README showcase preview images.")
    parser.add_argument(
        "--output-dir",
        default="docs/assets",
        help="Directory for generated preview images.",
    )
    args = parser.parse_args()

    outputs = render_readme_showcase_previews(Path(args.output_dir))
    for output in outputs:
        print(output)


if __name__ == "__main__":
    main()
