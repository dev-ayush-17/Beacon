# Technology Evaluation

Evaluation of approaches for LinkedIn feed data extraction.

## Evaluation Matrix

| Approach | Advantages | Disadvantages | Authentication | Reliability | Recommendation |
|----------|-----------|---------------|----------------|-------------|----------------|
| **Playwright + Browser Profile** | Full DOM access, renders JS, handles dynamic content, modern async API, good debugging tools | Heavyweight, requires browser install, slower than HTTP | Reuses existing browser session — no credential storage needed | High — sees exactly what user sees | **Selected for V0.5+** |
| **Selenium + Browser Profile** | Mature ecosystem, wide browser support, well-documented | Older API, sync-only by default, WebDriver version management | Same browser profile reuse approach | High — equivalent to Playwright | Alternative option |
| **HTTP + Cookies** | Lightweight, fast, no browser needed | No JS rendering, LinkedIn heavily relies on client-side rendering, API responses may differ from visible feed | Requires raw cookie extraction — less secure | Low — LinkedIn's feed depends on JS | Not recommended |
| **LinkedIn Official API** | Fully legitimate, stable, documented | Very limited scope (Marketing APIs focus on company pages), no feed access for personal accounts, requires app review | OAuth 2.0 | High for supported endpoints | Not viable for feed extraction |
| **LinkedIn Voyager API (Internal)** | Direct data access, structured JSON responses | Undocumented, changes without notice, may violate ToS, requires session cookies | Requires li_at cookie | Very Low — endpoints change frequently | Not recommended |

## Decision: Playwright + Browser Profile

### Rationale

1. **Full rendering**: LinkedIn's feed is a JavaScript-heavy SPA. HTTP-only approaches cannot reliably extract content.
2. **Browser profile reuse**: The user logs in through their normal browser. Playwright reuses that session — no cookies need to be copied or stored.
3. **Modern API**: Playwright's async Python API is well-suited for our architecture.
4. **Debugging**: Playwright provides headed mode, screenshots, and trace recording for experiment documentation.
5. **Security**: No credential storage in source code. The browser handles session management.

### Risks

- LinkedIn may detect automation through browser fingerprinting
- Browser profile sharing can cause session conflicts
- Playwright requires downloading browser binaries (~100MB+)
- DOM structure may change, breaking selectors

### Mitigation

- Use the real Chrome channel (not Chromium) to match the user's normal browser
- Close Chrome before running the extractor to avoid profile lock conflicts
- Design selectors to be semantic rather than structural
- Document all selector choices in experiments for easy updates
- If LinkedIn blocks automation, STOP and document the limitation

## Architecture Impact

The selected approach drives this architecture:

```
CLI
  |
  v
BrowserExtractor (implements BaseFeedExtractor)
  |
  v
SessionConfig (validates browser profile)
  |
  v
Playwright (launches Chrome with user profile)
  |
  v
LinkedIn Feed Page (rendered in browser)
  |
  v
DOM Extraction (selectors applied to rendered page)
  |
  v
Raw Data -> Normalizer -> FeedPost[]
```

## Date

2026-08-08

## Status

Playwright selected. Implementation begins at V0.5 (Browser Connectivity Experiment).
