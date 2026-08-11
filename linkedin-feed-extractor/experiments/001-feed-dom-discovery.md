# Experiment 001 — Feed DOM Discovery

## Date
2026-08-11

## Objective
Identify stable DOM selectors and markers for LinkedIn feed posts that can
be used for automated extraction.

## Approach
Research LinkedIn's feed page structure by analyzing:
- The rendered DOM structure of the feed
- CSS class naming patterns
- Semantic HTML markers
- Dynamic loading behavior
- Post type variations

## Environment
- OS: Windows
- Browser: Chrome (via Playwright)
- Python: 3.12
- Playwright: 1.62.0

## Observations

### Feed Container Structure

LinkedIn's feed uses a single-page application (SPA) architecture.
The feed is rendered within a scaffold layout:

```
body
  └── div#main (or div.application-outlet)
       └── div.scaffold-layout
            └── div.scaffold-layout__main
                 └── div.scaffold-layout__list
                      └── div.feed-shared-update-v2  (individual posts)
```

### Post Container

Each post is wrapped in `div.feed-shared-update-v2`. This appears to be
the most stable container selector identified.

**Stability assessment**: HIGH — This class has been consistent across
observations and is semantically meaningful.

### Post Components (within each feed-shared-update-v2)

| Component | Selector(s) | Stability | Notes |
|-----------|-------------|-----------|-------|
| **Author name** | `.update-components-actor__name span[aria-hidden='true']` | MEDIUM | The `aria-hidden` span contains the visible text |
| **Author headline** | `.update-components-actor__description span[aria-hidden='true']` | MEDIUM | May also use `__subtitle` |
| **Author profile link** | `a.update-components-actor__container-link` | MEDIUM | Contains href to profile |
| **Post text** | `.update-components-text span[dir='ltr']` | MEDIUM | Multiple spans for long text |
| **Relative time** | `.update-components-actor__sub-description span[aria-hidden='true']` | MEDIUM | Shows "2h", "1d", etc. |
| **Reaction count** | `.social-details-social-counts__reactions-count` | LOW | Format varies: "42", "1,234", "2K" |
| **Comment count** | `button.social-details-social-counts__comments` | LOW | Text like "23 comments" |
| **Repost indicator** | `.update-components-header__text-view` | MEDIUM | Present for reposts |

### Dynamic Loading

- Feed uses **infinite scroll** / lazy loading
- New posts are appended to the DOM when the user scrolls near the bottom
- Each scroll triggers network requests for additional feed items
- Initial page load typically renders 5-10 posts
- `window.scrollBy()` can trigger loading of additional posts

### Post Types Identified

| Type | Indicator | Structure Difference |
|------|-----------|---------------------|
| Original post | No header text | Standard structure |
| Repost | `.update-components-header__text-view` with "reposted" | Has header above author |
| Shared post | Nested `.feed-shared-update-v2` | Contains an inner post |
| Article | Link preview card | Has `.update-components-article` |
| Poll | Poll component | Has `.update-components-poll` |
| Sponsored | "Promoted" label | Has sponsor-specific classes |

### Unstable Selectors (AVOID)

- Any selector based on dynamically generated IDs
- React-specific `data-*` attributes that change per render
- Positional selectors (nth-child) — post order changes
- Image src URLs — CDN paths change

### Engagement Count Formats

Observed formats for counts:
- Plain number: `42`
- With comma: `1,234`
- Abbreviated: `2K`, `1.5M`
- With text: `23 comments`, `8 reposts`
- Missing entirely (for posts with no engagement)

The extractor must handle all these formats.

## Selectors/Markers Considered

### Selected (used in BrowserExtractor)

1. `div.feed-shared-update-v2` — post container (HIGH stability)
2. `.update-components-actor__name span[aria-hidden='true']` — author
3. `.update-components-text span[dir='ltr']` — post text
4. `.update-components-actor__sub-description span[aria-hidden='true']` — time
5. `.social-details-social-counts__reactions-count` — reactions

### Rejected

- `div[data-urn]` — URN attribute on post containers (sometimes missing)
- `.feed-shared-actor__name` — old class name, deprecated
- `#ember*` — Ember.js component IDs, change every render

## What Appeared Stable

1. **Post container**: `div.feed-shared-update-v2` — consistently present
2. **Component naming pattern**: `update-components-*` namespace
3. **Aria attributes**: `aria-hidden='true'` spans for visible text
4. **Social counts container**: `.social-details-social-counts`
5. **Main content area**: `[role='main']` and `.scaffold-layout__main`

## What Appeared Unstable

1. **Exact class suffixes** — LinkedIn occasionally updates component names
2. **Engagement count formats** — varies by locale and magnitude
3. **Post ordering** — algorithm-driven, non-deterministic
4. **Nested content structure** — shared posts have different DOM depth
5. **Media selectors** — different for images, videos, documents

## What Failed

- **Direct API approach**: LinkedIn's Voyager API endpoints change frequently
  and require session cookies, making them unreliable for long-term use
- **HTTP-only extraction**: Feed content is dynamically rendered; static HTML
  contains only the shell/skeleton
- **Universal CSS selectors**: No single selector works for ALL post types

## Conclusion

The `div.feed-shared-update-v2` container with `update-components-*` child
selectors provides a reasonable extraction strategy. The architecture should:

1. Use the container selector for post discovery
2. Apply fallback selectors for each field (try multiple patterns)
3. Handle missing fields gracefully (optional everywhere)
4. Normalize varied engagement count formats
5. Log unrecognized post structures for future analysis
6. Be prepared for selector breakage when LinkedIn updates their frontend

## Limitations

- Only visible (rendered) posts can be extracted
- Posts behind "see more" are truncated
- Some post types (polls, events) have unique structures not yet handled
- Engagement counts may not be perfectly accurate (LinkedIn rounds them)
- Selectors may break with LinkedIn frontend updates

## Next Experiment

Experiment 002 should focus on:
- Testing selector reliability across different post types
- Handling "see more" text expansion
- Exploring post URN extraction for stable identification
- Measuring extraction success rate across a sample of 50+ posts
