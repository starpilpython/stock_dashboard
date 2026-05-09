@echo off
chcp 65001 >nul
echo ============================================
echo  SFNI 자동 업데이트 스케줄러 설정
echo  08:00 아침 뉴스 / 16:30 전체 업데이트
echo ============================================
echo.

REM ── 현재 디렉토리 경로 ──
set "DASH_DIR=%~dp0"
set "PYTHON_PATH=py"

REM ── 기존 작업 삭제 (있으면) ──
schtasks /delete /tn "SFNI_Morning_News" /f >nul 2>&1
schtasks /delete /tn "SFNI_Closing_Update" /f >nul 2>&1
schtasks /delete /tn "SFNI_News_Crawl" /f >nul 2>&1

REM ── 1. 아침 08:00 뉴스 수집 ──
echo [1/2] 아침 뉴스 수집 (08:00) 등록 중...
schtasks /create /tn "SFNI_Morning_News" /tr "\"%PYTHON_PATH%\" \"%DASH_DIR%scripts\auto_update.py\" --mode morning" /sc daily /st 08:00 /f

if errorlevel 1 (
    echo.
    echo [!] 작업 스케줄러 등록 실패
    echo     관리자 권한으로 실행해보세요.
    echo     (이 파일을 우클릭 → 관리자 권한으로 실행)
    pause
    exit /b 1
)

REM ── 2. 장 마감 후 16:30 전체 업데이트 ──
echo [2/2] 장 마감 후 전체 업데이트 (16:30) 등록 중...
schtasks /create /tn "SFNI_Closing_Update" /tr "\"%PYTHON_PATH%\" \"%DASH_DIR%scripts\auto_update.py\" --mode closing" /sc daily /st 16:30 /f

if errorlevel 1 (
    echo.
    echo [!] 작업 스케줄러 등록 실패
    pause
    exit /b 1
)

echo.
echo ============================================
echo  설정 완료!
echo.
echo  [1] SFNI_Morning_News    - 매일 08:00
echo      → 뉴스만 수집 + JSON 갱신
echo.
echo  [2] SFNI_Closing_Update  - 매일 16:30
echo      → ETF/주식/지수/뉴스 전체 수집 + JSON 갱신
echo.
echo  로그: %DASH_DIR%logs\
echo.
echo  수동 실행:
echo    py scripts\auto_update.py --mode morning
echo    py scripts\auto_update.py --mode closing
echo.
echo  작업 확인:
echo    schtasks /query /tn "SFNI_Morning_News"
echo    schtasks /query /tn "SFNI_Closing_Update"
echo.
echo  작업 삭제:
echo    schtasks /delete /tn "SFNI_Morning_News" /f
echo    schtasks /delete /tn "SFNI_Closing_Update" /f
echo ============================================
pause
