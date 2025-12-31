#!/usr/bin/env python3
"""
AutoPPT - AI-Powered Presentation Generator

Generate professional PowerPoint presentations using AI and real-time research.
"""
import argparse
import sys
import os
import logging

from config import Config
from core.exceptions import AutoPPTError, APIKeyError, RateLimitError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


SUPPORTED_THEMES = [
    "minimalist", "technology", "nature", "creative",
    "corporate", "academic", "startup", "dark"
]

SUPPORTED_PROVIDERS = ["openai", "google", "anthropic", "mock"]


def main():
    parser = argparse.ArgumentParser(
        description="AutoPPT - Generate professional presentations using AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --topic "The Future of AI" --style technology
  python main.py --topic "Healthy Living" --provider google --slides 8
  python main.py --topic "Test Topic" --provider mock  # No API key needed
        """
    )
    parser.add_argument("--topic", required=True, help="Topic for the presentation")
    parser.add_argument(
        "--style", 
        default="minimalist", 
        choices=SUPPORTED_THEMES,
        help=f"Visual theme: {', '.join(SUPPORTED_THEMES)}"
    )
    parser.add_argument(
        "--provider", 
        default="openai",
        choices=SUPPORTED_PROVIDERS,
        help=f"LLM Provider: {', '.join(SUPPORTED_PROVIDERS)}"
    )
    parser.add_argument("--slides", type=int, default=10, help="Number of slides (default: 10)")
    parser.add_argument("--language", default="English", help="Output language (default: English)")
    parser.add_argument("--model", help="Specific LLM model name to use")
    parser.add_argument("--output", help="Output file path (default: output/<topic>.pptx)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Configure verbose logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate configuration
    if args.provider != "mock":
        Config.validate()
    
    # Determine output path
    if args.output:
        output_filename = args.output
    else:
        output_filename = f"output/{args.topic.replace(' ', '_')}.pptx"
    
    # Print configuration
    logger.info("=" * 50)
    logger.info("AutoPPT - AI Presentation Generator")
    logger.info("=" * 50)
    logger.info(f"Topic:    {args.topic}")
    logger.info(f"Style:    {args.style}")
    logger.info(f"Provider: {args.provider}")
    logger.info(f"Slides:   {args.slides}")
    logger.info(f"Language: {args.language}")
    if args.model:
        logger.info(f"Model:    {args.model}")
    logger.info(f"Output:   {output_filename}")
    logger.info("=" * 50)
    
    try:
        from core.generator import Generator
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_filename) or "output", exist_ok=True)
        
        gen = Generator(provider_name=args.provider, model=args.model)
        result = gen.generate(
            args.topic, 
            style=args.style, 
            output_file=output_filename, 
            slides_count=args.slides, 
            language=args.language
        )
        
        logger.info("=" * 50)
        logger.info(f"✅ SUCCESS! Presentation saved to: {result}")
        logger.info("=" * 50)
        
    except APIKeyError as e:
        logger.error(f"❌ API Key Error: {e.message}")
        logger.info("💡 Tip: Set up your API key in the .env file, or use --provider mock for testing.")
        sys.exit(1)
        
    except RateLimitError as e:
        logger.error(f"❌ Rate Limit Error: {e.message}")
        logger.info("💡 Tip: Wait a few minutes and try again, or use a paid API plan.")
        sys.exit(1)
        
    except AutoPPTError as e:
        logger.error(f"❌ AutoPPT Error: {e}")
        sys.exit(1)
        
    except KeyboardInterrupt:
        logger.warning("\n⚠️ Generation interrupted by user.")
        sys.exit(130)
        
    except Exception as e:
        logger.error(f"❌ Unexpected Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        logger.info("💡 Tip: Run with -v flag for detailed error information.")
        sys.exit(1)


if __name__ == "__main__":
    main()

