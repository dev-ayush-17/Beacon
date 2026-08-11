# Experiments Index

Experiments document the engineering research process for feed extraction.
Each experiment is a self-contained investigation into a specific approach.

## Index

| # | Name | Status | Date | Summary |
|---|------|--------|------|---------|
| 001 | [Feed DOM Discovery](../experiments/001-feed-dom-discovery.md) | Complete | 2026-08-11 | Identified stable selectors and post structure |

## Experiment Template

Each experiment should be documented in `experiments/NNN-name.md` with:

```markdown
# Experiment NNN — Title

## Date
YYYY-MM-DD

## Objective
What are we trying to learn or prove?

## Approach
What technique/strategy was used?

## Environment
- OS:
- Browser:
- Python:

## Procedure
Step-by-step what was done.

## Observations
What was observed during the experiment.

## Results
What data or outcomes were produced?

## Conclusion
What was learned?

## Limitations
What wasn't tested or remains uncertain?

## Next Experiment
What should be investigated next based on these results?
```

## Guidelines

- **Failed experiments are valuable** — always document them
- **No sensitive data** — never include session tokens, cookies, or PII
- **Be specific** — include selectors, timings, error messages
- **Be honest** — distinguish between "works reliably" and "worked once"
