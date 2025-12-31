---
description: How to update documentation after making changes
---

# Documentation Update Workflow

After making any code changes to AutoPPT, follow these steps to ensure documentation stays up-to-date:

## 1. Update CHANGELOG.md

Add a new entry under the current version section:
- Use categories: `Added`, `Changed`, `Fixed`, `Removed`, `Dependencies`
- Be specific about what changed
- Include links to relevant files if helpful

Example:
```markdown
### Added
- New feature X in `module.py`

### Fixed
- Bug Y in `renderer.py`
```

## 2. Update README.md (if needed)

Update README when:
- Adding new features that users should know about
- Changing CLI options or usage
- Adding new dependencies
- Updating configuration options

Sections to check:
- Features list
- Configuration Options table
- Visual Themes table
- Quick Start instructions

## 3. Update requirements.txt (if needed)

When adding new dependencies:
// turbo
```bash
pip freeze | grep <package> >> requirements.txt
```

Or manually add with version constraints.

## 4. Run Tests

Before committing, ensure all tests pass:
// turbo
```bash
pytest tests/ -v
```

## 5. Commit with Descriptive Message

Use conventional commit format:
```bash
git add .
git commit -m "feat: Add feature X

- Updated CHANGELOG.md
- Updated README.md with new usage"
```

## 6. Tag Releases

For version releases:
```bash
git tag v0.X.0
git push origin main
git push origin v0.X.0
```
