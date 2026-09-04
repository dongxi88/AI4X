# AI Agent Guidelines & Privacy Protection Rules

This repository enforces strict privacy and sensitive information security protocols.
All AI agents (Antigravity, Cursor, Claude Code, GitHub Copilot, Windsurf, Aider, Devin, etc.) operating in this repository MUST strictly comply with the following instructions.

---

## 1. Zero Sensitive Information Policy (强制绝不泄漏敏感信息)

- **No Absolute Local Paths**:
  - NEVER write local machine absolute paths (e.g., `C:\Users\...`, `D:\...`, `/Users/...`, `/home/...`, or network UNC paths) in code, scripts, configs, documentation, or commit messages.
  - ALWAYS use relative paths (e.g., `./...`, `os.path.dirname(__file__)`, `Path(__file__).resolve().parent`) or project-relative references.
- **No Personal / Corporate Identifiers**:
  - NEVER output real names, employee IDs, internal department names, internal domain names, or company names into tracked files.
  - Use generic placeholders, sanitized mock data, or environment variables.
- **No Credentials / Tokens / Secrets**:
  - NEVER hardcode passwords, API keys, tokens (e.g., `sk-...`, `ghp_...`, AWS keys), JWTs, or private keys.
  - ALWAYS load secrets from environment variables or ignored `.env` files.

---

## 2. Mandatory Pre-Commit Check (提交前必须检查)

- This repository uses version-controlled Git hooks located in `.githooks/` (`pre-commit` and `pre-push`).
- The hooks run `scripts/check_privacy.py`, which checks staged changes for privacy violations.
- Before committing or pushing, you should run:
  ```bash
  python scripts/check_privacy.py --staged
  ```
- If you are in a new clone or environment, ensure hooks are active:
  ```bash
  git config core.hooksPath .githooks
  ```

---

## 3. Strict Zero-Bypass Rule (严禁绕过拦截)

- **NEVER** run `git commit --no-verify` or `git commit -n`.
- **NEVER** run `git push --no-verify`.
- **NEVER** modify, disable, or delete `.githooks/` or `.privacy-config.json` to bypass checks.
- If a commit is blocked by the privacy check:
  1. Carefully read the error output showing the file, line number, and matched violation.
  2. Fix the violation immediately in the source code (replace absolute path with relative path, sanitize sensitive words, move secret to `.env`).
  3. Re-stage the cleaned file with `git add` and retry `git commit`.

---

## 4. Environment & Tooling Guidelines

- **Python Interpreter**: Python is located at `D:\ProgramData\miniforge3\python.exe` (and configured in User PATH). Run Python scripts via `python` or `D:\ProgramData\miniforge3\python.exe`.
- **Custom Keywords**: To customize or add sensitive keywords, update `.privacy-config.json` under `custom_keywords` or `custom_patterns`.

---

## 5. Explicit User Approval Required (未获许可严禁自动 Commit 或 Push)

- **NEVER Automatically Commit or Push**: AI agents must NEVER execute `git commit` or `git push` autonomously without explicit user instruction and permission.
- **Mandatory User Consent**: Always present proposed changes to the user and wait for explicit confirmation before committing code or pushing to remote repositories.

