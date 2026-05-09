@echo off
chcp 65001 >/dev/null
cd /d "%~dp0"

echo ============================================
echo  SFNI Local Data Update + GitHub Deploy
echo ============================================
echo.

echo [1/4] Collecting data...
py scripts/auto_update.py --mode closing
if %errorlevel% neq 0 (
    echo Data collection failed
    pause
    exit /b 1
)

echo.
echo [2/4] Git pull...
git pull --rebase origin main
if %errorlevel% neq 0 (
    echo Pull failed
    pause
    exit /b 1
)

echo.
echo [3/4] Git commit...
git add data/ public/data/
git diff --staged --quiet
if %errorlevel% neq 0 (
    git commit -m "data: local update %date% %time:~0,5%"
    echo.
    echo [4/4] Git push...
    git push
) else (
    echo No changes to commit
)

echo.
echo ============================================
echo  Done - Vercel will auto-deploy
echo ============================================
pause
