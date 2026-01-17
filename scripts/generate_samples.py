#!/usr/bin/env python3
"""Generate deterministic AutoPPT sample decks."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from autoppt.sample_library import get_sample_definition, get_sample_definitions, render_sample


def generate_samples(output_dir: str, category: str = "all", sample_ids: list[str] | None = None) -> list[Path]:
    destination = Path(output_dir).resolve()
    destination.mkdir(parents=True, exist_ok=True)

    if sample_ids:
        definitions = [get_sample_definition(sample_id) for sample_id in sample_ids]
    else:
        definitions = get_sample_definitions(category)

    generated: list[Path] = []
    for definition in definitions:
        output_path = render_sample(definition.sample_id, destination)
        generated.append(output_path)
        print(f"Generated {definition.sample_id} -> {output_path}")

    return generated


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate deterministic AutoPPT sample decks")
    parser.add_argument(
        "--category",
        default="all",
        choices=["all", "showcase", "feature"],
        help="Select which sample group to generate",
    )
    parser.add_argument(
        "--sample",
        action="append",
        dest="sample_ids",
        help="Generate only the given sample id; can be provided multiple times",
    )
    parser.add_argument(
        "--output-dir",
        default=os.path.join(os.path.dirname(__file__), "..", "samples"),
        help="Directory to write sample PPTX files into",
    )
    args = parser.parse_args()

    generated = generate_samples(output_dir=args.output_dir, category=args.category, sample_ids=args.sample_ids)
    if not generated:
        raise SystemExit("No samples were generated.")
    print(f"Generated {len(generated)} sample decks.")


if __name__ == "__main__":
    main()
