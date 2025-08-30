# Contributing to MediaLLM

Thank you for your interest in contributing to MediaLLM! We're excited to collaborate with you in making media processing accessible through natural language.

## Quick Start

### 1. Fork and Clone

```bash
# Clone the repository
git clone https://github.com/iamarunbrahma/mediallm.git

# Navigate to the repository
cd mediallm

# Add the upstream repository
git remote add upstream https://github.com/iamarunbrahma/mediallm.git
```

### 2. Set Up Development Environment

Install uv (optional, recommended): `curl -LsSf https://astral.sh/uv/install.sh | sh`

#### A. Set up MediaLLM package (`packages/mediallm`)

Using uv:
```bash
cd packages/mediallm
uv sync --dev
uv pip install -e .
```

Using pip:
```bash
cd packages/mediallm
pip install -e .
```

#### B. Set up MCP server package (`packages/mediallm-mcp`)

Using uv:
```bash
cd packages/mediallm-mcp
uv sync --dev
uv pip install -e .
```

Using pip:
```bash
cd packages/mediallm-mcp
pip install -e .
```

### 3. Verify Setup

```bash
# Run tests
cd packages/mediallm && uv run pytest tests/ -v

# Check code quality
make lint
make format
```

Optional (for manual checks):
```bash
ollama serve
ollama pull llama3.1
```

## Development Workflow

1. **Create a feature branch**: `git checkout -b feature/your-feature-name`
2. **Make your changes** following existing patterns
3. **Add tests** for new functionality in `packages/mediallm/tests/`
4. **Test thoroughly**: Navigate to `packages/mediallm/` and run `uv run pytest tests/ -v`
5. **Format code**: `make format` (from root directory)
6. **Check quality**: `make lint` (from root directory)

## Pull Request Process

1. Push your branch to your fork
2. Open a Pull Request against the `main` branch
3. Ensure all tests pass and code is formatted
4. Address any review feedback

## Testing

**Note:** All test commands must be run from the `packages/mediallm/` directory:

```bash
# Navigate to the MediaLLM package directory
cd packages/mediallm

# Run all tests
uv run pytest tests/ -v
```

## Need Help?

- **Issues**: [GitHub Issues](https://github.com/iamarunbrahma/mediallm/issues)
- **Commands**: Run `make help` to see available make commands

---

*Your contributions help make media processing accessible to everyone through natural language.*