# SFNI Dashboard

> **S**mart **F**low & **N**ews **I**nsight -- ETF 자금 흐름 + 뉴스 감성 기반 산업 투자 신호 대시보드

[![Live](https://img.shields.io/badge/status-live-brightgreen)](https://stock-dashboard-starpilpythons-projects.vercel.app)
![Update](https://img.shields.io/badge/auto--update-08%3A00%20%7C%2016%3A30%20KST-blue)
![Python](https://img.shields.io/badge/python-3.12-3776AB)

---

## Overview

21개 한국 산업 테마를 실시간으로 분석합니다.

- **ETF 자금 흐름** -- 기관이 어디에 돈을 넣고 있는지
- **뉴스 감성** -- 시장이 무엇에 주목하는지
- **IS Score** -- 두 신호를 결합한 산업 랭킹 지표

## Features

| Panel | Description |
|-------|-------------|
| **Heatmap** | 21개 산업 수익률/거래대금 시각화 |
| **IS Score Ranking** | ETF Flow(50%) + News(30%) + Sentiment(20%) 복합 지표 TOP 5 |
| **Sentiment** | 산업별 뉴스 긍정/중립/부정 분류 + 헤드라인 |
| **Stock Explorer** | ETF 비중 TOP 10 종목, 매집 신호, 거래량 추이 |
| **Hidden Opportunities** | IS Score 상위 산업 내 저반응 종목 자동 탐지 |

> 기간(1주/1개월/3개월/1년/커스텀) 전환 시 전체 패널 연동 재계산

## Architecture

```
pykrx (KRX)  ──┐
Naver News API ─┤
                ▼
    collect_data.py  →  CSV (append-only)
                            │
                    process_data.py  →  dashboard.json
                                            │
                                    git push → Vercel auto-deploy
```

## Tech Stack

| Layer | Stack |
|-------|-------|
| Frontend | Vanilla HTML/CSS/JS, dark theme, responsive |
| Data | Python 3.12, pandas, pykrx, Naver API |
| Automation | GitHub Actions (cron), Windows Task Scheduler |
| Deploy | Vercel (static), GitHub (CSV storage) |

## Project Structure

```
├── public/
│   ├── index.html              # UI
│   ├── css/style.css           # Dark theme + responsive
│   ├── js/app.js               # Rendering + interaction
│   └── data/dashboard.json     # Pre-computed data
│
├── scripts/
│   ├── collect_data.py         # Data collection (6 steps)
│   ├── process_data.py         # CSV → JSON processing
│   └── auto_update.py          # CLI (morning/closing modes)
│
├── data/                       # Raw CSVs
│   ├── etf_master.csv          # 1,100+ ETF metadata
│   ├── etf_prices.csv          # ETF OHLCV
│   ├── etf_pdf_valid392.csv    # ETF holdings composition
│   ├── index.csv               # KOSPI / KOSDAQ
│   ├── stock_prices.csv        # Individual stocks
│   └── news.csv                # Accumulated news
│
└── .github/workflows/          # Automation
    └── morning_news.yml        # 08:00 KST news cron
```

## Quick Start

```bash
pip install -r requirements.txt

# Collect data
python scripts/collect_data.py

# Generate dashboard JSON
python scripts/process_data.py

# Local server
python server.py    # → http://localhost:8080
```

### KRX Login (required since Dec 2025)

KRX requires membership login. Set environment variables:

```bash
export KRX_ID=your_id
export KRX_PW=your_pw
```

Register at [data.krx.co.kr](http://data.krx.co.kr) (free).

## IS Score Formula

```
IS Score = ETF Flow (50%) + News Attention (30%) + Sentiment (20%)
```

- **ETF Flow**: trading value change(40%) + return momentum(30%) + volume(20%) + positive ratio(10%)
- **News Attention**: article count(70%) + unique sources(30%)
- **Sentiment**: positive ratio(60%) + momentum(30%) - negative risk(10%)

## Update Schedule

| Time (KST) | What | Where |
|-------------|------|-------|
| 08:00 | News crawl | GitHub Actions |
| 16:30 | Full pipeline (ETF + stocks + index + news) | Local PC → git push |

## Industries (21)

반도체 / 2차전지 / 바이오 / AI / 로봇 / 게임 / 자동차 / 친환경 / 원자력 / 방산 / 철강 / 에너지 / 화학 / 통신 / 금융 / 리츠 / 건설 / 음식료 / 뷰티 / 운송 / 농업

---

> This dashboard provides data-driven market insights, not financial advice.
