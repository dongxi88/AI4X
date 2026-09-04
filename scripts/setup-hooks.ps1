# Configure git to use version-controlled .githooks directory
Write-Host "Configuring Git hooks path to .githooks..." -ForegroundColor Cyan
git config core.hooksPath .githooks

if ($LASTEXITCODE -eq 0) {
    Write-Host "[SUCCESS] Git hooks configured successfully! Commits and pushes will now be checked for privacy leaks." -ForegroundColor Green
} else {
    Write-Host "[ERROR] Failed to configure git hooks path." -ForegroundColor Red
}
