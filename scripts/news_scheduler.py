"""
뉴스 자동 수집 스크립트
매일 아침 8시에 Windows 작업 스케줄러로 실행됩니다.
뉴스만 수집하고 대시보드 JSON을 갱신합니다.

사용법:
  py scripts/news_scheduler.py          # 뉴스 수집 + JSON 갱신
  py scripts/news_scheduler.py --dry    # 수집만 (JSON 갱신 안 함)
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


def main():
    parser = argparse.ArgumentParser(description="SFNI 뉴스 자동 수집")
    parser.add_argument("--dry", action="store_true", help="수집만 (JSON 갱신 안 함)")
    args = parser.parse_args()

    # 로그 디렉토리 생성
    os.makedirs(LOG_DIR, exist_ok=True)
    log_path = os.path.join(LOG_DIR, f"news_{datetime.now().strftime('%Y-%m-%d')}.log")

    # 로그 파일에도 출력
    class Tee:
        def __init__(self, *files):
            self.files = files
        def write(self, text):
            for f in self.files:
                f.write(text)
                f.flush()
        def flush(self):
            for f in self.files:
                f.flush()

    log_file = open(log_path, "a", encoding="utf-8")
    sys.stdout = Tee(sys.__stdout__, log_file)
    sys.stderr = Tee(sys.__stderr__, log_file)

    print(f"\n{'='*50}")
    print(f"뉴스 자동 수집 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")

    try:
        import collect_data
        collect_data.collect_news()

        if not args.dry:
            print("\n대시보드 JSON 갱신 중...")
            import process_data
            process_data.main()
            print("JSON 갱신 완료!")

        print(f"\n수집 완료 - {datetime.now().strftime('%H:%M:%S')}")

    except Exception as e:
        print(f"\n[오류] {e}")
        import traceback
        traceback.print_exc()

    finally:
        log_file.close()
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__


if __name__ == "__main__":
    main()
