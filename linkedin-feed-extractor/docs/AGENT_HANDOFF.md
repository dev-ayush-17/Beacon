# Agent Handoff Guide

This document is for the **human developer** taking over after the automated agent completes its work. It explains everything you need to know to continue development.

---

## Environment Setup

### Prerequisites

- **Python 3.11+** — [Download](https://www.python.org/downloads/)
- **Git** — [Download](https://git-scm.com/)
- **Chromium-based browser** (Chrome or Edge) with an active LinkedIn login

### Installation

```bash
# 1. Navigate to the project
cd linkedin-feed-extractor

# 2. Create virtual environment
python -m venv .venv

# 3. Activate it
#    Windows PowerShell:
.venv\Scripts\Activate.ps1
#    Windows cmd:
.venv\Scripts\activate.bat
#    macOS/Linux:
source .venv/bin/activate

# 4. Install with dev dependencies
pip install -e ".[dev]"

# 5. Install Playwright browsers (needed for V0.5+)
playwright install chromium
```

---

## Repository Setup

The project lives inside the Beacon workspace:

```
Beacon/
├── frontend/          # Next.js frontend
├── backend/           # Python backend
└── linkedin-feed-extractor/   # ← This project
```

Git is initialized at the Beacon root level. All commits include the `linkedin-feed-extractor/` path prefix.

### Pushing to remote

```bash
# From the Beacon root
cd ..
git remote add origin <your-repo-url>   # if not already set
git push -u origin main
```

---

## Environment Variables

Copy the template and configure:

```bash
copy .env.example .env    # Windows
cp .env.example .env       # macOS/Linux
```

### Required variables

| Variable | Description | Example |
|----------|-------------|---------|
| `LINKEDIN_BROWSER_PROFILE_PATH` | Path to Chrome user data directory | `C:\Users\You\AppData\Local\Google\Chrome\User Data` |
| `LINKEDIN_BROWSER_PROFILE_NAME` | Chrome profile name | `Default` |

### Optional variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LINKEDIN_MAX_POSTS` | `20` | Max posts per extraction |
| `LINKEDIN_PAGE_TIMEOUT` | `30` | Page load timeout (seconds) |
| `LINKEDIN_OUTPUT_DIR` | `./output` | Output directory |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `LINKEDIN_HEADLESS` | `false` | Run browser headlessly |

**⚠️ NEVER commit `.env` to version control.**

---

## Authorized Session Setup

The extractor reuses your existing browser session rather than requiring you to paste cookies.

### How it works

1. Open Chrome normally and log into LinkedIn
2. Close Chrome completely
3. Set `LINKEDIN_BROWSER_PROFILE_PATH` in `.env` to your Chrome user data directory
4. The extractor launches a browser instance using that profile
5. LinkedIn sees the same authenticated session

### Finding your Chrome profile path

**Windows:**
```
C:\Users\<YourName>\AppData\Local\Google\Chrome\User Data
```

**macOS:**
```
/Users/<YourName>/Library/Application Support/Google/Chrome
```

**Linux:**
```
/home/<yourname>/.config/google-chrome
```

### Important notes

- Close Chrome before running the extractor (two Chrome instances can conflict)
- The extractor does NOT modify your browser profile
- If your LinkedIn session expires, log in again through Chrome normally

---

## Running the Extractor

```bash
# Check configuration and readiness
linkedin-feed status

# Run extraction (available after V0.7+)
linkedin-feed extract

# Show help
linkedin-feed --help
```

---

## Running Tests

```bash
# All unit tests
pytest

# With coverage report
pytest --cov=linkedin_feed_extractor

# Verbose output
pytest -v

# Only unit tests
pytest tests/unit/

# Only integration tests (when available, V0.5+)
pytest -m integration

# Exclude integration tests
pytest -m "not integration"
```

---

## Running Integration Experiments

Integration experiments require a configured browser session.

```bash
# Run experiment-tagged tests
pytest -m experiment -v

# Run integration tests
pytest -m integration -v
```

These tests:
- Require a real browser and LinkedIn session
- May take 30+ seconds
- Should NOT be run in CI without configuration
- Will be clearly marked in test output

---

## Where Extracted Data Appears

Extracted data is written to the `output/` directory (configurable via `LINKEDIN_OUTPUT_DIR`):

```
output/
├── feed_2026-08-08T18-30-00.json    # Timestamped extraction results
└── ...
```

The `output/` directory is in `.gitignore` — extracted data is never committed.

---

## How to Inspect Logs

Logs are printed to stdout with structured formatting (via `structlog`).

```bash
# Run with verbose flag for more detail
linkedin-feed -v status

# Set log level in .env
LOG_LEVEL=DEBUG
```

**Logs never contain cookies, tokens, or session data.**

---

## How to Add Another Experiment

1. **Create the experiment document:**
   ```
   experiments/NNN-descriptive-name.md
   ```

2. **Use the template from** `experiments/README.md`

3. **Update the index** in `docs/EXPERIMENTS.md`

4. **Commit:**
   ```bash
   git add experiments/NNN-*.md docs/EXPERIMENTS.md
   git commit -m "docs: record experiment NNN — descriptive name"
   ```

---

## How to Continue Development

The next recommended step is **V0.2 — Domain Models**.

### V0.2 tasks:
1. Define Pydantic models in `src/linkedin_feed_extractor/models.py`
2. Models needed: `FeedPost`, `Author`, `PostContent`, `Engagement`, `Media`, `PostMetadata`, `ExtractionResult`, `ExtractionError`
3. Use optional fields for data that may not always be present
4. Add unit tests in `tests/unit/test_models.py`
5. Commit with `feat: add feed post domain models`

### Development pattern for every version:
```
PLAN → IMPLEMENT → TEST → INSPECT → DOCUMENT → SECURITY CHECK → COMMIT
```

---

## Git Workflow

### Common commands

```bash
# Check what's changed
git status

# Review changes
git diff

# View commit history
git log --oneline -20

# See a specific commit
git show <hash>

# Create a feature branch
git checkout -b feat/v0.2-models

# Switch branches
git checkout main

# Commit (after testing)
git add <files>
git commit -m "type: description"

# Push to remote
git push origin main
```

### Commit conventions

| Prefix | Usage |
|--------|-------|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `docs:` | Documentation |
| `test:` | Test addition/change |
| `chore:` | Maintenance |
| `refactor:` | Code restructure |
| `exp:` | Experiment |

---

## Troubleshooting

### `linkedin-feed` command not found

```bash
# Ensure virtual environment is active
.venv\Scripts\Activate.ps1    # Windows
source .venv/bin/activate       # macOS/Linux

# Reinstall
pip install -e ".[dev]"
```

### Tests fail to import modules

```bash
# Ensure installed in editable mode
pip install -e ".[dev]"
```

### Browser profile issues

- **"Profile path does not exist"** — Verify the path in `.env` matches your actual Chrome installation
- **Browser crashes on start** — Close all Chrome windows first; two instances can't share a profile
- **Session not authenticated** — Log into LinkedIn through Chrome normally, then retry

### `playwright` errors

```bash
# Install browser binaries
playwright install chromium
```

---

## Security Checklist

Before every commit, verify:

- [ ] No `.env` file in the commit (`git status`)
- [ ] No cookies or session files in the commit
- [ ] No tokens or passwords in code
- [ ] No sensitive data in test fixtures
- [ ] No PII in experiment documents
- [ ] `.gitignore` covers all sensitive patterns
- [ ] `git diff` shows no credential leakage
- [ ] Log output in test results has no secrets

### If credentials are accidentally committed:

```bash
# Remove from tracking (keeps local copy)
git rm --cached <file>
git commit -m "security: remove accidentally committed credentials"

# If pushed: rotate credentials immediately
# LinkedIn: log out of all sessions and re-authenticate
```

See [SECURITY.md](SECURITY.md) for full details.
