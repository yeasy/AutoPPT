#!/usr/bin/env python3
"""
Safety check script for AutoPPT.
Checks for sensitive information (API keys, local paths) and unwanted files.
"""
import os
import sys
import re
import subprocess

# Patterns to search for (pattern, description, skip_tests)
SENSITIVE_PATTERNS = [
    (r"sk-[a-zA-Z0-9]{32,}", "Potential OpenAI/Anthropic API Key", False),
    (r"AIza[0-9A-Za-z-_]{35}", "Potential Google API Key", False),
    (r"/Users/[a-zA-Z0-9._-]+(?=/)", "Local macOS user path leakage", True),
    (r"/home/[a-zA-Z0-9._-]+(?=/)", "Local Linux user path leakage", True),
    (r"https?://[^\"'\s]+:[^\"'\s]+@[^\"'\s]+", "Hardcoded credentials in URL", False),
]

UNWANTED_EXTENSIONS = [".log", ".tmp", ".temp"]
UNWANTED_FILES = ["sample_output.pptx", "test.pptx"]

def check_files():
    print("🔍 Running safety audit...")
    errors = 0
    
    # Check for unwanted files in Git index
    try:
        git_files = subprocess.check_output(["git", "ls-files"]).decode("utf-8").splitlines()
    except Exception:
        git_files = []
    
    for file_path in git_files:
        if "check_sensitive.py" in file_path:
            continue
            
        # Check extensions
        _, ext = os.path.splitext(file_path)
        if ext in UNWANTED_EXTENSIONS or os.path.basename(file_path) in UNWANTED_FILES:
            print(f"❌ Unwanted file found in index: {file_path}")
            errors += 1
            
        # Check content of text files
        if ext in [".py", ".md", ".txt", ".json", ".yaml", ".yml", ".toml"]:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    is_test = file_path.startswith("tests/")
                    for pattern, description, skip_tests in SENSITIVE_PATTERNS:
                        if skip_tests and is_test:
                            continue
                        if re.search(pattern, content):
                            print(f"❌ {description} found in: {file_path}")
                            errors += 1
            except Exception as e:
                print(f"⚠️ Could not read {file_path}: {e}")

    if errors == 0:
        print("✅ Safety audit passed! No sensitive data or unwanted files detected.")
        return True
    else:
        print(f"🚨 Safety audit failed with {errors} errors.")
        return False

if __name__ == "__main__":
    if not check_files():
        sys.exit(1)
