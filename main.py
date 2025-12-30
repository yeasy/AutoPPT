import argparse
import sys
from config import Config

def main():
    parser = argparse.ArgumentParser(description="AutoPPT - AI Presentation Generator")
    parser.add_argument("--topic", help="Topic for the presentation")
    parser.add_argument("--style", default="minimalist", help="Visual style of the PPT")
    parser.add_argument("--provider", default="openai", help="LLM Provider (openai, anthropic, google)")
    parser.add_argument("--slides", type=int, default=10, help="Number of slides to generate (default: 10)")
    parser.add_argument("--language", default="English", help="Language of the presentation (default: English)")
    parser.add_argument("--model", help="Specific LLM model name to use")
    
    args = parser.parse_args()
    
    Config.validate()
    
    if not args.topic:
        print("Please provide a --topic")
        sys.exit(1)
        
    print(f"Generating PPT for: {args.topic}")
    print(f"Style: {args.style}")
    print(f"Provider: {args.provider}")
    if args.model:
        print(f"Model: {args.model}")
    print(f"Slides: {args.slides}")
    print(f"Language: {args.language}")
    
    CONFIG_MAP = {
        "openai": "openai",
        "anthropic": "anthropic",
        "google": "google"
    }
    
    try:
        from core.generator import Generator
        
        gen = Generator(provider_name=args.provider, model=args.model)
        output_filename = f"output/{args.topic.replace(' ', '_')}.pptx"
        
        # Ensure output directory exists
        import os
        os.makedirs("output", exist_ok=True)
        
        gen.generate(args.topic, style=args.style, output_file=output_filename, slides_count=args.slides, language=args.language)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
