# Roadmap

Development progress for LinkedIn Feed Extractor.

## Versions

- [x] **V0.1** — Project Scaffold
  - Repository structure, configuration, CLI entry point, tests, documentation
  - Status: Complete (commit 6c379a3)

- [x] **V0.2** — Domain Models
  - FeedPost, Author, PostContent, Engagement, Media, ExtractionResult
  - 32 unit tests for all models and serialization
  - Status: Complete (commit bcf0dfc)

- [x] **V0.3** — Extractor Contract
  - BaseFeedExtractor interface with typed contract
  - MockExtractor with 5 realistic sample posts
  - Configurable failure simulation
  - 17 contract + mock tests
  - Status: Complete (commit 53980b6)

- [x] **V0.4** — Session Architecture
  - Browser profile session management
  - Secure credential validation (never logs paths)
  - Playwright launch argument generation
  - 11 session tests
  - Status: Complete (commit 0d2d8c3)

- [ ] **V0.5** — Browser Connectivity Experiment
  - Start browser with authenticated session
  - Navigate to LinkedIn feed
  - Verify authentication status
  - Diagnostic logging

- [ ] **V0.6** — Feed Page Discovery
  - DOM structure investigation
  - Stable selector identification
  - Lazy loading analysis
  - Experiment documentation

- [ ] **V0.7** — Single Post Extraction
  - Extract author, text, URL, timestamp
  - Graceful handling of missing fields
  - Normalization tests

- [ ] **V0.8** — Multiple Post Extraction
  - Multi-post identification
  - Error tolerance per post
  - Deduplication

- [ ] **V0.9** — Normalization Layer
  - Raw -> normalized pipeline
  - Whitespace, timestamps, engagement parsing
  - Comprehensive unit tests

- [ ] **V1.0** — Complete Pipeline
  - End-to-end extraction CLI
  - JSON output
  - Full integration test

## Statistics

| Metric | Value |
|--------|-------|
| Total tests | 75 |
| Tests passing | 75 |
| Versions complete | 4 of 10 |
| Total commits | 4 |

## Future Considerations

- API-based extraction (if LinkedIn provides suitable endpoints)
- Pagination / infinite scroll handling
- Post type differentiation (articles, polls, shared posts)
- Media extraction (images, videos)
- Rate limiting / polite crawling
- Output format options (CSV, database)
