@echo off
chcp 65001 >nul
echo ============================================
echo  SFNI 로컬 데이터 수집 + GitHub 배포
echo  (ETF/주식/지수 + 뉴스 → git push)
echo ============================================
echo.

REM ── 1단계: 전체 데이터 수집 ──
echo [1/3] 데이터 수집 중...
py scripts/auto_update.py --mode closing
if errorlevel 1 (
    echo [!] 데이터 수집 실패
    pause
    exit /b 1
)

REM ── 2단계: git에 변경사항 커밋 ──
echo.
echo [2/3] GitHub에 커밋 중...
git add data/ public/data/
git diff --staged --quiet
if errorlevel 1 (
    for /f "tokens=*" %%i in ('powershell -command "Get-Date -Format 'yyyy-MM-dd HH:mm'"') do set NOW=%%i
    git commit -m "data: 로컬 전체 업데이트 %NOW%"
) else (
    echo     변경사항 없음, 커밋 건너뜀
    goto done
)

REM ── 3단계: push ──
echo.
echo [3/3] GitHub에 push 중...
git push
if errorlevel 1 (
    echo [!] push 실패 — 네트워크를 확인하세요
    pause
    exit /b 1
)

:done
echo.
echo ============================================
echo  완료! Vercel이 자동으로 재배포합니다.
echo ============================================
pause
