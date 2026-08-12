# Roadmap

Development progress for LinkedIn Feed Extractor.

## Versions

- [x] **V0.1** — Project Scaffold (commit 6c379a3)
- [x] **V0.2** — Domain Models (commit bcf0dfc)
- [x] **V0.3** — Extractor Contract (commit 53980b6)
- [x] **V0.4** — Session Architecture (commit 0d2d8c3)
- [x] **V0.5** — Browser Connectivity (commit cdb00fd)
- [x] **V0.6** — Feed Page Discovery (commit 4fe7b89)
- [x] **V0.9** — Normalization Layer (commit 355b6e7)
- [x] **V1.0** — Complete Pipeline (commit 6977654)
- [x] **V1.1** — Export Formats & Dedup (commit cc85e51)
- [x] **V1.2** — Retry & Resilience (commit fa3bd5f)

## Statistics

| Metric | Value |
|--------|-------|
| Total unit tests | 190 |
| Tests passing | 190 |
| Versions complete | 10 |
| Total commits | 10 |
| Source modules | 9 |
| Test modules | 8 |

## Source Modules

| Module | Purpose |
|--------|---------|
| `config.py` | Environment-based configuration with validation |
| `models.py` | Pydantic domain models (FeedPost, Author, etc.) |
| `cli.py` | CLI entry point (status, extract, version) |
| `session.py` | Browser profile session management |
| `normalizer.py` | Text, URL, timestamp normalization |
| `persistence.py` | JSON, CSV, Markdown output |
| `dedup.py` | Post deduplication and ID generation |
| `resilience.py` | Retry logic and fallback selectors |
| `extractor/base.py` | Abstract extractor interface |
| `extractor/mock.py` | Mock extractor for testing |
| `extractor/browser.py` | Playwright-based browser extractor |

## Future Considerations

- [ ] Integrate SelectorFallback into BrowserExtractor
- [ ] Integrate retry_async into BrowserExtractor navigation
- [ ] "See more" text expansion (click to reveal full text)
- [ ] Post URN extraction for stable identification
- [ ] Pagination / infinite scroll optimization
- [ ] Media extraction (images, video thumbnails)
- [ ] Rate limiting / polite crawling delays
- [ ] Output to SQLite database
- [ ] Incremental extraction (only new posts since last run)
- [ ] Post content change tracking
