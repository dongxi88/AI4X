#!/bin/sh
# Configure git to use version-controlled .githooks directory
echo "Configuring Git hooks path to .githooks..."
git config core.hooksPath .githooks
chmod +x .githooks/pre-commit .githooks/pre-push 2>/dev/null || true
echo "[SUCCESS] Git hooks configured successfully! Commits and pushes will now be checked for privacy leaks."
