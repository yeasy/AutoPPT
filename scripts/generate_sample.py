#!/usr/bin/env python3
"""Generate a single deterministic AutoPPT sample deck."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from autoppt.sample_library import get_sample_definitions, render_sample


def main() -> None:
    definitions = get_sample_definitions()
    sample_ids = [definition.sample_id for definition in definitions]

    parser = argparse.ArgumentParser(description="Generate one deterministic AutoPPT sample deck")
    parser.add_argument("sample_id", choices=sample_ids, help="Sample id to render")
    parser.add_argument(
        "--output-dir",
        default=os.path.join(os.path.dirname(__file__), "..", "samples"),
        help="Directory to write the sample PPTX file into",
    )
    args = parser.parse_args()

    output_path = render_sample(args.sample_id, Path(args.output_dir))
    print(f"Generated {args.sample_id} -> {output_path}")


if __name__ == "__main__":
    main()
