"""
SFNI 로컬 개발 서버
- 정적 파일 서빙 (public/)
- 데이터 업데이트 API (/api/update)
- API 키 불필요 (pykrx 공개 데이터 + 네이버 API 내장)

사용법:
  py server.py
  → http://localhost:8080 에서 대시보드 접속
"""

import os
import sys
import json
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = os.path.join(BASE_DIR, "public")

# 업데이트 상태 관리
update_status = {"running": False, "message": "", "progress": []}


def run_update(options):
    """백그라운드에서 데이터 수집 + JSON 생성 실행"""
    global update_status
    update_status = {"running": True, "message": "시작 중...", "progress": []}

    try:
        # scripts 경로 추가
        scripts_dir = os.path.join(BASE_DIR, "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)

        days = options.get("days", 1)
        skip_pdf = options.get("skip_pdf", False)
        news_only = options.get("news_only", False)

        # ── 1단계: 데이터 수집 ──
        update_status["message"] = "데이터 수집 중..."
        update_status["progress"].append("데이터 수집 시작 (API 키 불필요)")

        import importlib
        import collect_data
        importlib.reload(collect_data)

        if news_only:
            update_status["message"] = "뉴스 수집 중..."
            collect_data.collect_news()
            update_status["progress"].append("뉴스 수집 완료")
        else:
            # 날짜 결정
            dates = collect_data.get_business_days(days)
            update_status["progress"].append(f"수집 기간: {dates[0]} ~ {dates[-1]} ({len(dates)}일)")

            # ETF 마스터
            update_status["message"] = "ETF 마스터 수집 중..."
            etf_master = collect_data.collect_etf_master(dates[-1])
            update_status["progress"].append(f"ETF 마스터: {len(etf_master)}개")

            # ETF 가격
            update_status["message"] = "ETF 가격 수집 중..."
            collect_data.collect_etf_prices(dates)
            update_status["progress"].append("ETF 가격 수집 완료")

            # ETF PDF
            if not skip_pdf:
                update_status["message"] = "ETF PDF 수집 중... (시간이 걸릴 수 있습니다)"
                collect_data.collect_etf_pdf(dates, etf_master)
                update_status["progress"].append("ETF PDF 수집 완료")
            else:
                update_status["progress"].append("ETF PDF 건너뜀")

            # 시장 지수
            update_status["message"] = "시장 지수 수집 중..."
            collect_data.collect_index(dates)
            update_status["progress"].append("시장 지수 수집 완료")

            # 종목 가격
            update_status["message"] = "종목 가격 수집 중..."
            collect_data.collect_stock_prices(dates)
            update_status["progress"].append("종목 가격 수집 완료")

            # 뉴스
            update_status["message"] = "뉴스 수집 중..."
            collect_data.collect_news()
            update_status["progress"].append("뉴스 수집 완료")

        # ── 2단계: JSON 생성 ──
        update_status["message"] = "대시보드 데이터 생성 중..."
        update_status["progress"].append("JSON 생성 시작")

        import process_data
        importlib.reload(process_data)
        process_data.main()

        update_status["progress"].append("JSON 생성 완료")
        update_status["message"] = "업데이트 완료!"
        update_status["running"] = False

    except Exception as e:
        update_status["message"] = f"오류: {str(e)}"
        update_status["running"] = False
        update_status["progress"].append(f"오류 발생: {str(e)}")


class DashboardHandler(SimpleHTTPRequestHandler):
    """정적 파일 + API 핸들러"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PUBLIC_DIR, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/status":
            return self._json_response(update_status)

        # 정적 파일 서빙
        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/update":
            if update_status["running"]:
                return self._json_response({"status": "busy", "message": "이미 업데이트가 진행 중입니다"})

            body = self._read_body()
            options = body.get("options", {})

            # 백그라운드에서 실행
            t = threading.Thread(target=run_update, args=(options,), daemon=True)
            t.start()
            return self._json_response({"status": "started"})

        self.send_error(404)

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors_headers()
        self.end_headers()

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def _json_response(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._cors_headers()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, format, *args):
        # API 요청만 로그
        if "/api/" in str(args[0]) if args else False:
            super().log_message(format, *args)


def main():
    port = 8080
    server = HTTPServer(("0.0.0.0", port), DashboardHandler)
    print(f"SFNI Dashboard Server")
    print(f"http://localhost:{port}")
    print(f"Ctrl+C 로 종료")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n서버 종료")
        server.server_close()


if __name__ == "__main__":
    main()
