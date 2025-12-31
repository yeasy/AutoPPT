#!/usr/bin/env python3
"""
Safety check script for AutoPPT.
Checks for sensitive information (API keys, local paths) and unwanted files.
"""
import os
import sys
import re
import subprocess

# Patterns to search for
SENSITIVE_PATTERNS = [
    (r"sk-[a-zA-Z0-9]{32,}", "Potential OpenAI/Anthropic API Key"),
    (r"AIza[0-9A-Za-z-_]{35}", "Potential Google API Key"),
    (r"/Users/baohua", "Local user path leakage"),
    (r"\"(http|https)://[^\"]*:[^\"]*@\"", "Hardcoded credentials in URL"),
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
                    for pattern, description in SENSITIVE_PATTERNS:
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
