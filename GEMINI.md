# Antigravity & Gemini Workspace Instructions

This repository enforces strict privacy and sensitive information security protocols.

## Privacy & Security Directives
1. **Never Hardcode Absolute Paths**:
   - Do NOT produce local Windows drive paths (`C:\...`, `D:\...`) or Unix home paths (`/home/...`, `/Users/...`) in any codebase files or commit logs.
   - Always use relative paths or environment variables.
2. **Never Hardcode Personal / Corporate Data**:
   - Do NOT include personal names, employee IDs (`h\d{8}`), accounts, or company names in source files.
3. **Never Hardcode Secrets**:
   - Passwords, API tokens, and private keys must never be committed.
4. **Git Hooks & Zero Bypass**:
   - Git hooks are configured via `.githooks`. Commits and pushes automatically scan for privacy leaks via `python scripts/check_privacy.py`.
   - Never bypass hooks with `--no-verify` or `-n`. Always fix violations directly.
5. **Python Environment**:
   - Python is installed at `D:\ProgramData\miniforge3\python.exe` and available via `python`.
6. **Explicit Approval for Commit & Push**:
   - Never run `git commit` or `git push` automatically without explicit user permission. Always ask first.
