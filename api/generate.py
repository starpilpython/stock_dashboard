"""
Vercel Serverless Function — 데이터 재생성 API
GET /api/generate 호출 시 CSV 데이터를 다시 처리하여 dashboard.json 갱신
"""

from http.server import BaseHTTPRequestHandler
import json
import sys
import os

# scripts 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            from process_data import main
            main()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "message": "Dashboard data regenerated"}).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode())
