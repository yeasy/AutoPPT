#!/usr/bin/env python3
"""
AutoPPT - AI-Powered Presentation Generator

Generate professional PowerPoint presentations using AI and real-time research.
"""
import argparse
import logging
import os
import re
from pathlib import Path
import sys

from .config import Config
from .exceptions import APIKeyError, AutoPPTError, RateLimitError
from .llm_provider import get_supported_providers
from .style_selector import auto_select_style, get_all_styles, get_style_description

logger = logging.getLogger(__name__)


def main() -> None:
    supported_themes = get_all_styles()
    supported_providers = get_supported_providers()

    parser = argparse.ArgumentParser(
        description="AutoPPT - Generate professional presentations using AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  autoppt --topic "The Future of AI" --style technology
  autoppt --topic "Healthy Living" --provider google --slides 8
  autoppt --topic "Machine Learning 101" --auto-style
  autoppt --topic "Q1 Report" --outline-only
  autoppt --topic "Startup Pitch" --confirm-outline
  autoppt --topic "Test Topic" --provider mock
        """,
    )
    parser.add_argument("--topic", required=True, help="Topic for the presentation")
    parser.add_argument(
        "--style",
        default="minimalist",
        choices=supported_themes,
        help=f"Visual theme: {', '.join(supported_themes)}",
    )
    parser.add_argument(
        "--auto-style",
        action="store_true",
        help="Auto-detect the best visual style based on topic keywords",
    )
    parser.add_argument(
        "--provider",
        default="openai",
        choices=supported_providers,
        help=f"LLM Provider: {', '.join(supported_providers)}",
    )
    parser.add_argument("--slides", type=int, default=10, help="Number of slides (default: 10)")
    parser.add_argument("--language", default="English", help="Output language (default: English)")
    parser.add_argument("--model", help="Specific LLM model name to use")
    parser.add_argument("--output", help="Output file path (default: output/<topic>.pptx)")
    parser.add_argument("--template", help="Path to a PPTX template file to use")
    parser.add_argument("--thumbnails", action="store_true", help="Generate thumbnail grid images after creation")
    parser.add_argument(
        "--outline-only",
        action="store_true",
        help="Generate only the outline and save to markdown file, skip PPT generation",
    )
    parser.add_argument(
        "--confirm-outline",
        action="store_true",
        help="Interactive mode: preview outline and confirm before generating PPT",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    Config.initialize(configure_logging=True, log_level=log_level)

    if not args.topic or not args.topic.strip():
        parser.error("--topic must not be empty")
    if len(args.topic) > 1000:
        parser.error("--topic must not exceed 1000 characters")
    if args.template and not os.path.isfile(args.template):
        parser.error(f"Template file not found: {args.template}")
    if not 3 <= args.slides <= 50:
        parser.error("--slides must be between 3 and 50")
    if len(args.language) > 50:
        parser.error("--language must not exceed 50 characters")

    if args.output:
        if ".." in args.output.replace("\\", "/").split("/"):
            parser.error(f"Path traversal detected: {args.output}")
        resolved_output = os.path.realpath(args.output)
        for prefix in Config.BLOCKED_SYSTEM_PREFIXES:
            if resolved_output.startswith(prefix):
                parser.error(f"Output path is not allowed: {args.output}")
        for segment in Config.BLOCKED_PATH_SEGMENTS:
            if segment in resolved_output:
                parser.error(f"Output path is not allowed: {args.output}")
        output_filename = args.output
    else:
        safe_name = re.sub(r"[^\w\-]", "_", args.topic)[:100]
        output_filename = os.path.join(Config.OUTPUT_DIR, f"{safe_name}.pptx")

    selected_style = args.style
    if args.auto_style:
        selected_style = auto_select_style(args.topic, args.language)
        logger.info("🎨 Auto-selected style: %s (%s)", selected_style, get_style_description(selected_style))

    logger.info("=" * 50)
    logger.info("AutoPPT - AI Presentation Generator")
    logger.info("=" * 50)
    logger.info("Topic:    %s", args.topic)
    logger.info("Style:    %s%s", selected_style, " (auto)" if args.auto_style else "")
    logger.info("Provider: %s", args.provider)
    logger.info("Slides:   %s", args.slides)
    logger.info("Language: %s", args.language)
    if args.model:
        logger.info("Model:    %s", args.model)
    logger.info("Output:   %s", output_filename)
    logger.info("=" * 50)

    try:
        if args.provider != "mock":
            Config.validate(args.provider)

        from .generator import Generator

        output_dir = os.path.dirname(output_filename)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        with Generator(provider_name=args.provider, model=args.model) as gen:
            if args.outline_only:
                outline = gen.generate_outline(args.topic, args.slides, args.language)
                outline_file = str(Path(output_filename).with_suffix("")) + "_outline.md"
                gen.save_outline(outline, outline_file)
                logger.info("=" * 50)
                logger.info("✅ Outline saved to: %s", outline_file)
                logger.info("=" * 50)
                print("\n" + gen.outline_to_markdown(outline))
                return

            if args.confirm_outline:
                outline = gen.generate_outline(args.topic, args.slides, args.language)
                print("\n" + "=" * 50)
                print("📋 OUTLINE PREVIEW")
                print("=" * 50)
                print(gen.outline_to_markdown(outline))
                print("=" * 50)

                try:
                    response = input("\n✅ Continue with this outline? [Y/n/q]: ").strip().lower()
                    if response in ("n", "no"):
                        logger.info("Outline rejected. Please modify topic or try again.")
                        sys.exit(0)
                    if response in ("q", "quit"):
                        logger.info("Generation cancelled.")
                        sys.exit(0)
                except EOFError:
                    logger.warning("No interactive input available; proceeding with current outline.")

                result = gen.generate_from_outline(
                    outline,
                    args.topic,
                    style=selected_style,
                    output_file=output_filename,
                    language=args.language,
                    template_path=args.template,
                    create_thumbnails=args.thumbnails,
                )
            else:
                result = gen.generate(
                    args.topic,
                    style=selected_style,
                    output_file=output_filename,
                    slides_count=args.slides,
                    language=args.language,
                    template_path=args.template,
                    create_thumbnails=args.thumbnails,
                )

            logger.info("=" * 50)
            logger.info("✅ SUCCESS! Presentation saved to: %s", result)
            if gen.last_quality_report.has_issues:
                logger.warning("Deck QA reported %s issue(s).", len(gen.last_quality_report.issues))
            logger.info("=" * 50)
    except APIKeyError as exc:
        logger.error("❌ API Key Error: %s", exc.message)
        logger.info("💡 Tip: Set up your API key in the .env file, or use --provider mock for testing.")
        sys.exit(1)
    except RateLimitError as exc:
        logger.error("❌ Rate Limit Error: %s", exc.message)
        logger.info("💡 Tip: Wait a few minutes and try again, or use a paid API plan.")
        sys.exit(1)
    except AutoPPTError as exc:
        logger.error("❌ AutoPPT Error: %s", exc)
        sys.exit(1)
    except KeyboardInterrupt:
        logger.warning("\n⚠️ Generation interrupted by user.")
        sys.exit(130)
    except Exception as exc:
        logger.error("❌ Unexpected Error: %s", exc)
        if args.verbose:
            import traceback

            traceback.print_exc()
        logger.info("💡 Tip: Run with -v flag for detailed error information.")
        sys.exit(1)


if __name__ == "__main__":
    main()
