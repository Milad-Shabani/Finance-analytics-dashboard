@echo off
REM One-click publish for the Finance Analytics Dashboard repo (Windows).
REM Requires: git, GitHub CLI (gh) authenticated (gh auth login).

setlocal
set REPO_NAME=finance-analytics-dashboard
set DESCRIPTION=Full-stack Finance / FP&A portfolio project -- synthetic 3-statement financial model (balance sheet ties exactly), revenue/EBITDA/cash-flow forecasting, explainable budget-overrun risk model, self-contained HTML dashboard (zero external dependencies). Fictional TelNova Communications ISP.
set GIT_USER_NAME=Milad Shabani
set GIT_USER_EMAIL=MILAD.SHABANI6515@GMAIL.COM

echo ==^> Configuring git identity for this repo
git init -q
git config user.name "%GIT_USER_NAME%"
git config user.email "%GIT_USER_EMAIL%"

echo ==^> Staging and committing
git add -A
git commit -q -m "Initial commit: Finance Analytics Dashboard + Excel workbook + forecasting engine"
git branch -M main

echo ==^> Creating GitHub repository: %REPO_NAME%
gh repo view %REPO_NAME% >nul 2>&1
if errorlevel 1 (
    gh repo create %REPO_NAME% --public --source=. --remote=origin --description "%DESCRIPTION%"
) else (
    echo Repo already exists on GitHub, skipping create.
)

echo ==^> Syncing repo description (also fixes it if it was garbled before)
gh repo edit --description "%DESCRIPTION%"

echo ==^> Pushing
git push -u origin main

echo ==^> Setting topics
gh repo edit --add-topic finance --add-topic fpa --add-topic financial-modeling --add-topic python --add-topic excel --add-topic dashboard --add-topic data-visualization --add-topic business-intelligence

echo ==^> Enabling GitHub Pages (workflow build)
for /f "delims=" %%i in ('gh api user --jq .login') do set OWNER=%%i
gh api "repos/%OWNER%/%REPO_NAME%/pages" -f build_type=workflow >nul 2>&1
if errorlevel 1 (
    echo Pages site already exists, updating build type instead
    gh api -X PUT "repos/%OWNER%/%REPO_NAME%/pages" -f build_type=workflow
)

echo.
echo Done. Repo: https://github.com/%OWNER%/%REPO_NAME%
echo Dashboard (after Pages workflow runs): https://%OWNER%.github.io/%REPO_NAME%/
endlocal
