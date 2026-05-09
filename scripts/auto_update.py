"""
SFNI 자동 업데이트 스크립트
Windows 작업 스케줄러에 의해 하루 2회 실행됩니다.

스케줄:
  08:00  --mode morning   → 뉴스만 수집 + JSON 갱신
  16:30  --mode closing    → ETF/주식/지수/뉴스 전체 수집 + JSON 갱신

사용법:
  py scripts/auto_update.py --mode morning    # 아침 뉴스
  py scripts/auto_update.py --mode closing    # 장 마감 후 전체
  py scripts/auto_update.py                   # 기본: 전체 수집
"""

import os
import sys
import argparse
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
LOG_DIR = os.path.join(BASE_DIR, "logs")

# scripts 디렉토리를 path에 추가
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)


class Tee:
    """stdout/stderr를 파일과 콘솔에 동시 출력"""
    def __init__(self, *files):
        self.files = files
    def write(self, text):
        for f in self.files:
            f.write(text)
            f.flush()
    def flush(self):
        for f in self.files:
            f.flush()


def run_morning():
    """08:00 아침 업데이트 — 뉴스만 수집"""
    import collect_data
    print("[모드] 아침 뉴스 수집")
    print("-" * 40)
    collect_data.collect_news()


def run_closing():
    """16:30 장 마감 후 업데이트 — 전체 수집"""
    import collect_data

    print("[모드] 장 마감 후 전체 업데이트")
    print("-" * 40)

    # 수집 날짜 (최신 1영업일)
    dates = collect_data.get_business_days(1)
    print(f"수집 대상 날짜: {dates}")

    # 1. ETF 마스터
    etf_master = collect_data.collect_etf_master(dates[-1])

    # 2. ETF 가격
    collect_data.collect_etf_prices(dates)

    # 3. ETF PDF (구성종목 — 1일치 약 5~10분 소요)
    collect_data.collect_etf_pdf(dates, etf_master)

    # 4. 시장 지수
    collect_data.collect_index(dates)

    # 5. 종목 가격
    collect_data.collect_stock_prices(dates)

    # 6. 뉴스
    collect_data.collect_news()


def main():
    parser = argparse.ArgumentParser(description="SFNI 자동 업데이트")
    parser.add_argument(
        "--mode",
        choices=["morning", "closing"],
        default="closing",
        help="morning: 뉴스만 (08:00) / closing: 전체 (16:30)"
    )
    args = parser.parse_args()

    # 로그 설정 (GitHub Actions에서는 콘솔만, 로컬에서는 파일도)
    is_ci = os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS")
    log_file = None

    if not is_ci:
        os.makedirs(LOG_DIR, exist_ok=True)
        today = datetime.now().strftime("%Y-%m-%d")
        log_path = os.path.join(LOG_DIR, f"update_{today}_{args.mode}.log")
        log_file = open(log_path, "a", encoding="utf-8")
        sys.stdout = Tee(sys.__stdout__, log_file)
        sys.stderr = Tee(sys.__stderr__, log_file)

    print(f"\n{'='*50}")
    print(f"SFNI 자동 업데이트 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if is_ci:
        print("[환경] GitHub Actions")
    print(f"{'='*50}")

    try:
        # 데이터 수집
        if args.mode == "morning":
            run_morning()
        else:
            run_closing()

        # JSON 갱신
        print(f"\n{'='*40}")
        print("대시보드 JSON 갱신 중...")
        import process_data
        process_data.main()
        print("JSON 갱신 완료!")

        print(f"\n완료 - {datetime.now().strftime('%H:%M:%S')}")

    except Exception as e:
        print(f"\n[오류] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)  # CI에서 실패 표시

    finally:
        if log_file:
            log_file.close()
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__


if __name__ == "__main__":
    main()
