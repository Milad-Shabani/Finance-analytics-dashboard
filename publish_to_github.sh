#!/usr/bin/env bash
# One-command publish for the Finance Analytics Dashboard repo (macOS/Linux).
#
# Usage:
#   1. Create a new EMPTY repository on GitHub named "finance-analytics-dashboard"
#      (do NOT initialize it with a README/license/gitignore).
#   2. From this project's root folder, run:
#        chmod +x publish_to_github.sh
#        ./publish_to_github.sh https://github.com/<your-username>/finance-analytics-dashboard.git
#
set -euo pipefail

REMOTE_URL="${1:-}"
if [ -z "$REMOTE_URL" ]; then
  echo "Usage: ./publish_to_github.sh <git-remote-url>"
  echo "Example: ./publish_to_github.sh https://github.com/milad-shabani/finance-analytics-dashboard.git"
  exit 1
fi

GIT_USER_NAME="Milad Shabani"
GIT_USER_EMAIL="MILAD.SHABANI6515@GMAIL.COM"

echo "==> Configuring git identity for this repo"
git init -q
git config user.name "$GIT_USER_NAME"
git config user.email "$GIT_USER_EMAIL"

echo "==> Staging and committing"
git add -A
git commit -q -m "Initial commit: Finance Analytics Dashboard + Excel workbook + forecasting engine" || echo "(nothing new to commit)"
git branch -M main

echo "==> Adding remote and pushing"
git remote remove origin 2>/dev/null || true
git remote add origin "$REMOTE_URL"
git push -u origin main

echo ""
echo "Done. Now enable GitHub Pages: Settings -> Pages -> Source -> GitHub Actions"
echo "The included workflow (.github/workflows/deploy-pages.yml) will build and publish the dashboard automatically."
