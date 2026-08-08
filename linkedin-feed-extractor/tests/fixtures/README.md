# Test Fixtures

This directory contains test fixtures such as:

- Sample HTML fragments representing LinkedIn feed structures
- Mock data for testing normalization
- Expected output data for comparison tests

Fixtures are loaded by tests to enable offline testing without
requiring access to LinkedIn.

## Naming Convention

```
<component>_<scenario>.<ext>

Examples:
  feed_single_post.html
  feed_multiple_posts.html
  post_with_media.json
  post_missing_author.json
```

## Security

Fixtures must NEVER contain:
- Real user data
- Session tokens or cookies
- Identifiable personal information
- Actual LinkedIn URLs pointing to real profiles

Use synthetic/anonymized data only.
