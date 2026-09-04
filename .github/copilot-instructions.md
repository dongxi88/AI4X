# GitHub Copilot Instructions

- **Privacy Protection**: Do not suggest or write local machine absolute paths (`C:\...`, `D:\...`, `/Users/...`, `/home/...`). Suggest relative paths or environment variable lookups.
- **Credential & Identity Safety**: Do not insert personal names, employee IDs, corporate names, passwords, tokens, or secret keys into code.
- **Git Hooks**: Pre-commit and pre-push hooks check for privacy leaks before any commit or push.
