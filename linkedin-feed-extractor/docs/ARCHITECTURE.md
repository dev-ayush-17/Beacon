# Architecture

## Overview

The LinkedIn Feed Extractor follows a layered architecture that cleanly separates concerns and enables swapping extraction mechanisms without impacting consuming code.

## High-Level Flow

```
CLI (click)
  ↓
Extractor (abstract)
  ↓
Session (browser profile)
  ↓
Raw Data (HTML/DOM)
  ↓
Normalizer (parsing + cleanup)
  ↓
Domain Models (FeedPost, Author, etc.)
  ↓
Output (JSON export)
```

## Component Diagram

```
┌─────────────────────────────────────────┐
│                  CLI                     │
│            (cli.py / click)             │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│           Configuration                  │
│          (config.py)                     │
│   Loads from .env, validates settings    │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│         Feed Extractor                   │
│      (extractor/base.py)                │
│                                          │
│  ┌──────────────┐  ┌───────────────┐    │
│  │ Browser      │  │ Mock          │    │
│  │ Extractor    │  │ Extractor     │    │
│  │ (V0.5+)      │  │ (V0.3)        │    │
│  └──────────────┘  └───────────────┘    │
│                                          │
│  ┌──────────────┐                       │
│  │ API          │                       │
│  │ Extractor    │                       │
│  │ (future)     │                       │
│  └──────────────┘                       │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│         Domain Models                    │
│         (models.py)                      │
│  FeedPost, Author, Engagement, etc.     │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│            Output                        │
│     JSON / structured data              │
└─────────────────────────────────────────┘
```

## Design Principles

### 1. Separation of Concerns
Each module has a single responsibility:
- `config.py` — environment and settings
- `models.py` — data structures
- `extractor/` — extraction logic
- `cli.py` — user interface

### 2. Pluggable Extractors
The `BaseFeedExtractor` abstract class enables:
- `BrowserExtractor` — Playwright-based browser automation
- `MockExtractor` — offline testing without LinkedIn
- `ApiExtractor` — future official API integration

### 3. Security by Design
- Credentials never in source code
- Browser profile reuse instead of raw cookies
- Safe repr/logging (no secret leakage)
- Validation before execution

### 4. Testability
- Domain models testable in isolation
- Mock extractor enables full pipeline testing
- Fixtures enable parser testing without network

## Technology Choices

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Language | Python 3.11+ | Strong ecosystem for automation, data modeling |
| CLI | Click | Composable commands, testing support |
| Browser | Playwright | Modern, async, reliable automation |
| Models | Pydantic | Validation, serialization, type safety |
| Config | python-dotenv | Simple, standard env var loading |
| Logging | structlog | Structured, filterable logging |
| Output | Rich | Beautiful terminal output |
| Testing | pytest | Standard, extensible, great UX |

## Directory Layout

```
src/linkedin_feed_extractor/
├── __init__.py          # Package metadata
├── config.py            # Configuration from environment
├── models.py            # Domain models (V0.2)
├── cli.py               # CLI entry point
└── extractor/
    ├── __init__.py
    └── base.py           # Abstract extractor interface
```

## Future Components (not yet implemented)

- `extractor/browser.py` — Playwright browser extractor
- `extractor/mock.py` — Mock extractor for testing
- `normalizer.py` — Raw data → domain model transformation
- `session.py` — Browser session management
- `persistence.py` — Output storage
