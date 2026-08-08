# Security

## Overview

This project accesses LinkedIn through a user's **own authenticated browser session**. Handling session data requires strict security practices.

## Core Principles

1. **No credential storage in code** — All secrets stay in `.env` or local browser profiles
2. **No credential logging** — Cookies, tokens, and session IDs are never printed
3. **No credential commits** — `.gitignore` blocks all sensitive files
4. **Fail safe** — Missing credentials produce clear errors, not silent failures
5. **User authorization only** — The tool accesses only what the authenticated user can normally see

## Session Handling

### Preferred: Browser Profile Reuse

The extractor uses a local browser profile directory where the user has already authenticated with LinkedIn through normal browser usage.

This approach:
- ✅ Does not require copying cookies
- ✅ Does not store credentials in files
- ✅ Uses the browser's own session management
- ✅ Respects LinkedIn's session lifecycle

### Configuration

Set the browser profile path in `.env`:

```env
LINKEDIN_BROWSER_PROFILE_PATH=C:\Users\YourName\AppData\Local\Google\Chrome\User Data
LINKEDIN_BROWSER_PROFILE_NAME=Default
```

**Never commit the `.env` file.**

## What Must NEVER Be Committed

| Item | Reason |
|------|--------|
| `.env` | Contains configuration paths and potentially sensitive data |
| `*.cookies` / `*.cookies.json` | Session cookies |
| `browser_profile/` | Browser session data |
| `*.session` / `*.token` | Authentication tokens |
| `*.key` / `*.pem` / `*.crt` | Cryptographic material |
| `secrets/` / `credentials/` | Credential stores |
| `output/` | May contain session-linked content |

## `.gitignore` Coverage

The project `.gitignore` blocks:
- Environment files (`.env`, `.env.local`, etc.)
- Cookie files and session artifacts
- Browser profile directories
- Output directories (may contain PII)
- Log files

## If Credentials Are Accidentally Committed

**Immediately:**

1. Remove the sensitive file:
   ```bash
   git rm --cached <file>
   git commit -m "security: remove accidentally committed credentials"
   ```

2. If pushed to a remote:
   - Rotate/invalidate the exposed credentials immediately
   - Consider using `git filter-branch` or BFG Repo-Cleaner to purge from history
   - LinkedIn sessions: log out of all sessions and log back in

3. Verify the fix:
   ```bash
   git log --all --full-history -- <file>
   ```

## What This Tool Does NOT Do

This tool is designed for **authorized access only**. It does NOT:

- ❌ Bypass CAPTCHAs
- ❌ Defeat anti-bot detection
- ❌ Bypass access controls
- ❌ Circumvent rate limits
- ❌ Exploit vulnerabilities
- ❌ Evade LinkedIn security mechanisms
- ❌ Access content the user isn't authorized to see

If LinkedIn blocks an approach, the tool **stops** and documents the limitation.

## Logging Safety

The `ExtractorConfig.__repr__()` method explicitly redacts sensitive paths:

```python
# Shows "browser_profile=SET" instead of the actual path
ExtractorConfig(browser_profile=SET, ...)
```

All logging must follow this pattern: **log the existence of credentials, never their values.**

## Security Checklist (Before Every Commit)

- [ ] No `.env` files in the commit
- [ ] No cookie files in the commit
- [ ] No session tokens in code or output
- [ ] No browser profile data in the commit
- [ ] No PII in test fixtures
- [ ] `.gitignore` is up to date
- [ ] `git diff` shows no credential leakage
- [ ] Log output does not contain secrets
