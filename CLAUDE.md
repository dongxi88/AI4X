# Claude Code Guidelines

## Privacy & Security Directives
- **Zero Absolute Paths**: Never use local absolute paths (`C:\...`, `D:\...`, `/Users/...`, `/home/...`). Always use relative paths or dynamically resolved paths.
- **Zero Sensitive Data**: Never expose personal names, employee IDs (`h\d{8}`), accounts, passwords, tokens, or company names.
- **Git Commit Enforcement**:
  - Pre-commit and pre-push hooks are active in `.githooks/` via `git config core.hooksPath .githooks`.
  - Never use `--no-verify` or `-n`. If blocked, resolve the reported privacy leak immediately.
  - Never run `git commit` or `git push` automatically without explicit user confirmation.
- **Python**: Primary Python interpreter is `D:\ProgramData\miniforge3\python.exe` (accessible as `python`).
