# LinkedIn Feed Extractor

A research-oriented tool for extracting LinkedIn feed post data through **legitimate, user-authorized** browser sessions.

## ⚠️ Important

This tool does **not**:
- Bypass CAPTCHAs or anti-bot systems
- Circumvent access controls or rate limits
- Exploit vulnerabilities
- Scrape private content unauthorized to the user

It operates exclusively through a user's own authenticated browser session.

## Current Status

| Version | Status | Description |
|---------|--------|-------------|
| V0.1    | ✅ Complete | Project scaffold & development environment |
| V0.2    | ⬜ Pending  | Domain models (FeedPost, Author, etc.) |
| V0.3    | ⬜ Pending  | Extractor contract & mock implementation |
| V0.4    | ⬜ Pending  | Session architecture |
| V0.5    | ⬜ Pending  | Browser connectivity experiment |
| V0.6    | ⬜ Pending  | Feed page DOM discovery |
| V0.7    | ⬜ Pending  | Single post extraction |
| V0.8    | ⬜ Pending  | Multiple post extraction |
| V0.9    | ⬜ Pending  | Normalization layer |
| V1.0    | ⬜ Pending  | Complete extraction pipeline |

## Quick Start

```bash
# Navigate to project
cd linkedin-feed-extractor

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (macOS/Linux)
source .venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Check status
linkedin-feed status

# Run tests
pytest
```

## Setup

1. Copy `.env.example` to `.env`
2. Configure your browser profile path (see [SECURITY.md](docs/SECURITY.md))
3. Install dependencies as shown above

## Project Structure

```
linkedin-feed-extractor/
├── src/linkedin_feed_extractor/   # Source code
│   ├── config.py                  # Configuration management
│   ├── models.py                  # Domain models (V0.2)
│   ├── cli.py                     # CLI interface
│   └── extractor/                 # Extraction implementations
│       └── base.py                # Base extractor interface
├── tests/                         # Test suite
│   ├── unit/                      # Unit tests
│   └── fixtures/                  # Test data
├── docs/                          # Documentation
├── experiments/                   # Experiment records
└── scripts/                       # Utility scripts
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) — System design and component overview
- [Development](docs/DEVELOPMENT.md) — Setup, commands, and workflow
- [Security](docs/SECURITY.md) — Session handling and credential management
- [Experiments](docs/EXPERIMENTS.md) — Extraction experiment index
- [Roadmap](docs/ROADMAP.md) — Development progress tracker
- [Agent Handoff](docs/AGENT_HANDOFF.md) — Guide for human developers

## License

MIT — see [LICENSE](LICENSE).
