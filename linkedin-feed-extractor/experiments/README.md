# Experiments

This directory contains individual experiment records documenting
the engineering research process for feed extraction.

## Naming Convention

```
NNN-descriptive-name.md

Examples:
  001-feed-dom-discovery.md
  002-selector-stability.md
  003-dynamic-content-loading.md
```

## When to Create an Experiment

Create an experiment document when:
- Investigating a new extraction approach
- Testing selector stability
- Analyzing page structure
- Evaluating a technology choice
- Documenting a failure for future reference

## Template

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

## Security

Experiment documents must NEVER include:
- Session tokens or cookies
- Personal user data
- Screenshots containing authenticated UI with personal information
- LinkedIn URLs pointing to real user profiles
