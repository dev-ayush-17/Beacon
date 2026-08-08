# Scripts

Utility scripts for development and operations.

## Planned Scripts

- `setup.sh` / `setup.ps1` — Automated environment setup
- `check_secrets.sh` — Pre-commit secret scanning
- `run_extraction.sh` — Wrapper for common extraction commands

## Guidelines

- Scripts should be idempotent (safe to run multiple times)
- Scripts should not contain hardcoded credentials
- Include usage comments at the top of each script
