# MediaLLM Makefile - Simplified
# ===============================
# Essential commands for development and release

.PHONY: help lint format build release clean bump docs-install docs-serve docs-build docs-deploy docs-clean

# Default target
help:  ## Show available commands
	@echo "MediaLLM Development Commands"
	@echo "============================="
	@echo
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-12s\033[0m %s\n", $$1, $$2}'

# Code Quality
lint:  ## Lint with ruff (autofix) across mediallm and mediallm-mcp
	uv run ruff check --fix packages/mediallm/src/ packages/mediallm/tests/ packages/mediallm-mcp/src/

format:  ## Format code with black and ruff (autofix) for both packages
	uv run black packages/mediallm/src/ packages/mediallm/tests/ packages/mediallm-mcp/src/
	uv run ruff format packages/mediallm/src/ packages/mediallm/tests/ packages/mediallm-mcp/src/
	uv run ruff check --fix packages/mediallm/src/ packages/mediallm/tests/ packages/mediallm-mcp/src/

# Build and Release
build: clean  ## Build both distribution packages
	cd packages/mediallm && uvx --from build pyproject-build
	cd packages/mediallm-mcp && uvx --from build pyproject-build

bump:  ## Auto-bump version (semver) based on Conventional Commits since last tag
	@NEW_VERSION=$$(uv run python - <<-'PY'
	import os, re, subprocess, sys, pathlib
	root = pathlib.Path(__file__).resolve().parent
	def git_out(args):
	    try:
	        return subprocess.check_output(args, cwd=root).decode()
	    except subprocess.CalledProcessError:
	        return ""
	last_tag = git_out(['git','describe','--tags','--abbrev=0']).strip() or 'v0.0.0'
	log_range = f"{last_tag}..HEAD" if last_tag else 'HEAD'
	commits = git_out(['git','log',log_range,'--pretty=%s%n%b'])
	text = commits.lower()
	bump = 'patch'
	if 'breaking change' in text or re.search(r'!:', commits):
	    bump = 'major'
	elif re.search(r'(^|\n)feat(\(|:|!)', text):
	    bump = 'minor'
	elif re.search(r'(^|\n)(fix|perf)(\(|:|!)', text):
	    bump = 'patch'
	version_file = root/'packages/mediallm/src/mediallm/utils/version.py'
	m = re.search(r'__version__\s*=\s*"(\d+)\.(\d+)\.(\d+)"', version_file.read_text())
	if not m:
	    current = (0,0,1)
	else:
	    current = tuple(map(int, m.groups()))
	major, minor, patch = current
	if bump=='major':
	    major, minor, patch = major+1, 0, 0
	elif bump=='minor':
	    major, minor, patch = major, minor+1, 0
	else:
	    major, minor, patch = major, minor, patch+1
	new_version = f"{major}.{minor}.{patch}"
	def replace(path, pattern, repl):
	    p = (root/path)
	    s = p.read_text()
	    s = re.sub(pattern, repl, s, flags=re.MULTILINE)
	    p.write_text(s)
	# Ensure baseline 0.0.1 if files don't exist yet
	replace('packages/mediallm/src/mediallm/utils/version.py', r'__version__\s*=\s*"[^"]+"', f'__version__ = "{new_version}"')
	replace('packages/mediallm-mcp/pyproject.toml', r'^version\s*=\s*"[^"]+"', f'version = "{new_version}"')
	replace('packages/mediallm-mcp/src/mediallm_mcp/__about__.py', r'__version__\s*=\s*"[^"]+"', f'__version__ = "{new_version}"')
	print(new_version)
	PY
	); \
	V=$$NEW_VERSION; \
	echo "Bumped version to $$V"; \
	git add packages/mediallm/src/mediallm/utils/version.py packages/mediallm-mcp/pyproject.toml packages/mediallm-mcp/src/mediallm_mcp/__about__.py; \
	git commit -m "chore(release): v$$V" || true; \
	git tag v$$V -f

release: bump build  ## Bump version, build both, and upload to PyPI
	uvx --from twine twine upload packages/mediallm/dist/* packages/mediallm-mcp/dist/*
	git push --follow-tags

# Documentation
docs-install:  ## Install documentation dependencies
	pip install -e "packages/mediallm[docs]"

docs-serve:  ## Serve documentation locally with hot reload
	mkdocs serve --config-file mkdocs.yml

docs-build:  ## Build static documentation site
	mkdocs build --config-file mkdocs.yml

docs-deploy:  ## Deploy documentation to GitHub Pages
	mkdocs gh-deploy --config-file mkdocs.yml

docs-clean:  ## Clean built documentation
	rm -rf site/

# Cleanup
clean:  ## Clean all build artifacts
	rm -rf dist/ build/ *.egg-info/
	rm -rf packages/mediallm/dist/ packages/mediallm/build/ packages/mediallm/*.egg-info/
	rm -rf packages/mediallm-mcp/dist/ packages/mediallm-mcp/build/ packages/mediallm-mcp/*.egg-info/
	rm -rf .ruff_cache/ .pytest_cache/ __pycache__/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete