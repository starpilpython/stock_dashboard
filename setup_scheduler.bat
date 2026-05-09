@echo off
chcp 65001 >nul
echo ============================================
echo  SFNI 로컬 스케줄러 설정
echo  매일 16:30 ETF/주식/지수 수집 + GitHub 배포
echo  (뉴스는 GitHub Actions가 자동 처리)
echo ============================================
echo.

REM ── 현재 디렉토리 경로 ──
set "DASH_DIR=%~dp0"

REM ── 기존 작업 삭제 (있으면) ──
schtasks /delete /tn "SFNI_Morning_News" /f >nul 2>&1
schtasks /delete /tn "SFNI_Closing_Update" /f >nul 2>&1
schtasks /delete /tn "SFNI_News_Crawl" /f >nul 2>&1
schtasks /delete /tn "SFNI_Local_Update" /f >nul 2>&1

REM ── 16:30 전체 수집 + git push 등록 ──
echo 작업 스케줄러에 등록 중...
schtasks /create /tn "SFNI_Local_Update" /tr "\"%DASH_DIR%local_update.bat\"" /sc daily /st 16:30 /f

if errorlevel 1 (
    echo.
    echo [!] 작업 스케줄러 등록 실패
    echo     관리자 권한으로 실행해보세요.
    echo     (이 파일을 우클릭 → 관리자 권한으로 실행)
    pause
    exit /b 1
)

echo.
echo ============================================
echo  설정 완료!
echo.
echo  자동 스케줄:
echo  ┌─────────────────────────────────────────┐
echo  │ 08:00  뉴스 수집      (GitHub Actions)  │
echo  │ 16:30  ETF/주식/지수  (이 PC)           │
echo  │ 16:30  뉴스 수집      (GitHub Actions)  │
echo  │        → Vercel 자동 재배포             │
echo  └─────────────────────────────────────────┘
echo.
echo  수동 실행: local_update.bat 더블클릭
echo  작업 확인: schtasks /query /tn "SFNI_Local_Update"
echo  작업 삭제: schtasks /delete /tn "SFNI_Local_Update" /f
echo ============================================
pause
