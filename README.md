# SFNI Dashboard — Smart Flow & News Insight

ETF 수급 흐름과 뉴스 감성 분석을 결합하여 **산업별 투자 인사이트**를 제공하는 대시보드입니다.

![Dashboard Preview](https://img.shields.io/badge/status-live-brightgreen) ![Auto Update](https://img.shields.io/badge/update-08%3A00%20%7C%2016%3A30%20KST-blue)

---

## 주요 기능

### 산업 수익률 히트맵
- 21개 산업의 최근 5일 수익률을 한눈에 파악
- 색상 강도로 수익률 크기를 직관적으로 표현

### IS Score (Industry Signal Score) 랭킹
- ETF 수급 점수 (50%) + 뉴스 관심도 (30%) + 감성 점수 (20%)
- 산업별 투자 신호 강도를 종합 점수로 제공

### 뉴스 감성 분석
- 산업별 최신 뉴스를 긍정/중립/부정으로 분류
- 감성 게이지와 헤드라인으로 시장 분위기 파악

### 핵심 구성 종목 탐색
- 산업별 ETF에 가장 많이 편입된 종목 TOP 10
- 개별 종목의 5일 수익률, 거래량 추이 제공

### Potential Hidden Opportunities
- IS Score 상위 산업에서 아직 주가에 반영되지 않은 유망 종목 탐지

---

## 데이터 소스

| 데이터 | 소스 | API 키 |
|--------|------|--------|
| ETF 시세/마스터 | pykrx (KRX 공개 데이터) | 불필요 |
| 시장 지수 (KOSPI/KOSDAQ) | pykrx | 불필요 |
| 개별 종목 가격 | pykrx | 불필요 |
| 산업별 뉴스 | 네이버 검색 API | 내장 |

---

## 자동 업데이트 (하이브리드 방식)

KRX(한국거래소)는 해외 IP를 차단하므로, 뉴스와 ETF/주식 데이터를 분리하여 수집합니다.

| 시간 (KST) | 작업 | 실행 환경 | 내용 |
|-------------|------|-----------|------|
| **08:00** | 뉴스 수집 | GitHub Actions (자동) | 21개 산업 뉴스 크롤링 |
| **16:30** | 뉴스 수집 | GitHub Actions (자동) | 장 마감 뉴스 갱신 |
| **16:30** | ETF/주식/지수/구성종목 | 로컬 PC (스케줄러) | pykrx 전체 수집 → git push |

수집 완료 시 Vercel이 자동 재배포합니다.

---

## 프로젝트 구조

```
stock_dashboard/
├── public/                    # 프론트엔드 (Vercel 배포 대상)
│   ├── index.html
│   ├── css/style.css
│   ├── js/app.js
│   └── data/dashboard.json    # 전처리된 대시보드 데이터
│
├── scripts/                   # 백엔드 스크립트
│   ├── collect_data.py        # 데이터 수집 (pykrx + 네이버 API)
│   ├── process_data.py        # CSV → JSON 전처리
│   └── auto_update.py         # 자동 업데이트 (morning/closing)
│
├── data/                      # 수집된 원본 데이터
│   ├── etf_master.csv         # ETF 목록 (800+ 종목)
│   ├── etf_prices.csv         # ETF 일별 시세
│   ├── index.csv              # KOSPI/KOSDAQ 지수
│   ├── stock_prices.csv       # 개별 종목 시세
│   ├── stocks_master.csv      # 관심 종목 목록
│   ├── news.csv               # 뉴스 데이터 (누적)
│   └── news_history/          # 날짜별 뉴스 아카이브
│
├── .github/workflows/         # GitHub Actions
│   ├── morning_news.yml       # 08:00 뉴스 수집
│   └── closing_update.yml     # 16:30 전체 업데이트
│
├── server.py                  # 로컬 개발 서버
├── vercel.json                # Vercel 배포 설정
└── requirements.txt           # Python 패키지
```

---

## 로컬 실행

```bash
# 패키지 설치
pip install -r requirements.txt

# 데이터 수집 (API 키 불필요)
python scripts/collect_data.py

# JSON 생성
python scripts/process_data.py

# 로컬 서버 실행
python server.py
# → http://localhost:8080
```

### 수동 업데이트

```bash
# 뉴스만 수집
python scripts/auto_update.py --mode morning

# 전체 수집 (ETF + 주식 + 지수 + 뉴스)
python scripts/auto_update.py --mode closing
```

---

## 기술 스택

- **프론트엔드**: Vanilla HTML/CSS/JS
- **데이터 수집**: Python, pykrx, 네이버 검색 API
- **자동화**: GitHub Actions (cron)
- **배포**: Vercel (정적 호스팅)
- **데이터 저장**: CSV (GitHub repo 내 보관)

---

## IS Score 산정 기준

```
IS Score = ETF Flow Score × 50% + News Attention Score × 30% + Sentiment Score × 20%
```

| 구성 요소 | 가중치 | 세부 항목 |
|-----------|--------|-----------|
| ETF Flow Score | 50% | 거래대금 증가율(40%) + 수익률 모멘텀(30%) + 거래량 증가율(20%) + 긍정 ETF 비율(10%) |
| News Attention | 30% | 뉴스 보도량(70%) + 고유 언론사 수(30%) |
| Sentiment Score | 20% | 긍정 비율(60%) + 감성 모멘텀(30%) + 부정 리스크 조정(10%) |

---

## 분석 대상 산업 (21개)

반도체 · 2차전지 · 바이오/헬스 · AI/소프트웨어 · 로봇/자율주행 · 게임/엔터 · 자동차/모빌리티 · 친환경/신재생 · 원자력 · 방산/우주항공 · 철강/조선 · 에너지/석유 · 화학/소재 · 통신/5G · 금융 · 리츠/부동산 · 건설/인프라 · 음식료/식품 · 뷰티/화장품 · 운송/물류 · 농업

---

## 면책 조항

이 대시보드는 데이터 기반 시장 인사이트를 제공하며, 금융 투자 자문에 해당하지 않습니다. 사용자는 최종 투자 판단을 본인의 책임과 판단에 따라 내려야 합니다.
