# Development Guide

## Prerequisites

- Python 3.11 or later
- Git
- A Chromium-based browser (Chrome, Edge) with an active LinkedIn session

## Environment Setup

### 1. Clone and navigate

```bash
cd linkedin-feed-extractor
```

### 2. Create virtual environment

```bash
python -m venv .venv
```

### 3. Activate virtual environment

**Windows (PowerShell):**
```powershell
.venv\Scripts\Activate.ps1
```

**Windows (cmd):**
```cmd
.venv\Scripts\activate.bat
```

**macOS / Linux:**
```bash
source .venv/bin/activate
```

### 4. Install in development mode

```bash
pip install -e ".[dev]"
```

### 5. Configure environment

```bash
copy .env.example .env   # Windows
cp .env.example .env      # macOS/Linux
```

Edit `.env` with your actual configuration. See [SECURITY.md](SECURITY.md) for guidance.

## Commands

### CLI

```bash
# Show help
linkedin-feed --help

# Show version
linkedin-feed --version

# Check configuration status
linkedin-feed status

# Run extraction (not yet implemented)
linkedin-feed extract
```

### Testing

```bash
# Run all unit tests
pytest

# Run with coverage
pytest --cov=linkedin_feed_extractor

# Run only unit tests
pytest tests/unit/

# Run integration tests (when available)
pytest -m integration

# Run with verbose output
pytest -v
```

### Code Quality

```bash
# Lint with ruff
ruff check src/ tests/

# Auto-fix lint issues
ruff check --fix src/ tests/

# Format code
ruff format src/ tests/

# Type checking
mypy src/
```

## Git Workflow

### Before every commit

```bash
# 1. Check status
git status

# 2. Review changes
git diff

# 3. Run tests
pytest

# 4. Run lints
ruff check src/ tests/

# 5. Security check — verify no secrets in diff
git diff --cached | findstr /i "cookie token password secret key"   # Windows
git diff --cached | grep -iE "cookie|token|password|secret|key"     # macOS/Linux

# 6. Commit
git add <files>
git commit -m "type: description"
```

### Commit message format

```
type: description

Types:
  feat:     New feature
  fix:      Bug fix
  docs:     Documentation
  test:     Tests
  chore:    Maintenance
  refactor: Code restructuring
  exp:      Experiment
```

## Project Organization

| Directory | Purpose |
|-----------|---------|
| `src/linkedin_feed_extractor/` | Source code |
| `tests/unit/` | Unit tests |
| `tests/fixtures/` | Test data |
| `docs/` | Documentation |
| `experiments/` | Experiment records |
| `scripts/` | Utility scripts |

## Adding a New Experiment

1. Create `experiments/NNN-experiment-name.md`
2. Use the template from [experiments/README.md](../experiments/README.md)
3. Update [EXPERIMENTS.md](EXPERIMENTS.md)
4. Commit with `docs: record experiment NNN`
