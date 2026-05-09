@echo off
chcp 65001 >nul
echo ============================================
echo  SFNI 대시보드 데이터 업데이트
echo  API 키 불필요 (공개 데이터 + 내장 키)
echo ============================================
echo.

REM ── 1단계: 데이터 수집 ──
echo [1/2] 최신 데이터 수집 중...
py scripts/collect_data.py %*
if errorlevel 1 (
    echo [!] 데이터 수집 실패
    pause
    exit /b 1
)

REM ── 2단계: JSON 생성 ──
echo.
echo [2/2] 대시보드 JSON 생성 중...
py scripts/process_data.py
if errorlevel 1 (
    echo [!] JSON 생성 실패
    pause
    exit /b 1
)

echo.
echo ============================================
echo  업데이트 완료!
echo  http://localhost:8080 에서 확인하세요
echo ============================================
pause
