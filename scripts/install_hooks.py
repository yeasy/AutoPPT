#!/usr/bin/env python3
"""
Installer for AutoPPT Git hooks.
Sets up the pre-commit hook to run safety audits automatically.
"""
import os
import stat

HOOK_CONTENT = """#!/bin/bash
echo "🛡️ Running pre-commit safety audit..."
python3 scripts/check_sensitive.py
if [ $? -ne 0 ]; then
    echo "🚨 Commit aborted. Please fix the security/cleanup issues above."
    exit 1
fi

echo "🧪 Running unit tests..."
export PYTHONPATH=$PYTHONPATH:.
pytest tests/ -q
if [ $? -ne 0 ]; then
    echo "🚨 Commit aborted. Some tests failed."
    exit 1
fi

echo "✅ All checks passed. Proceeding with commit."
exit 0
"""

def install_hook():
    hook_path = ".git/hooks/pre-commit"
    if not os.path.exists(".git"):
        print("❌ Error: .git directory not found. Are you in the project root?")
        return
    
    with open(hook_path, "w") as f:
        f.write(HOOK_CONTENT)
    
    # Make executable
    st = os.stat(hook_path)
    os.chmod(hook_path, st.st_mode | stat.S_IEXEC)
    print(f"✅ Git pre-commit hook installed at {hook_path}")

if __name__ == "__main__":
    install_hook()
