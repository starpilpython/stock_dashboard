"""
SFNI 데이터 수집 스크립트
기존 CSV 데이터에 최신 데이터를 추가(append)한다.

사전 요구사항:
  - pip install pykrx requests
  - 네이버 API 키: 코드 내장 (별도 설정 불필요)
  - KRX 로그인: 불필요 (pykrx 공개 데이터 사용)

사용법:
  py scripts/collect_data.py              # 최신 1영업일 업데이트
  py scripts/collect_data.py --days 5     # 최근 5영업일 업데이트
  py scripts/collect_data.py --full       # 전체 재수집 (60영업일)
"""

import os
import sys
import time
import argparse
import warnings
from datetime import datetime, timedelta
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr

import pandas as pd
import numpy as np

# ── 경로 설정 ──
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

# ── 산업 분류 키워드 (순서 중요: 위에서부터 먼저 매칭) ──
INDUSTRY_KEYWORDS = [
    ("반도체", ["반도체", "HBM", "파운드리", "메모리", "시스템반도체"]),
    ("2차전지", ["2차전지", "배터리", "리튬", "양극재", "음극재", "전고체"]),
    ("바이오/헬스", ["바이오", "헬스케어", "제약", "의료", "헬스", "게놈"]),
    ("AI/소프트웨어", ["AI", "인공지능", "소프트웨어", "클라우드", "빅데이터", "사이버보안", "디지털"]),
    ("로봇/자율주행", ["로봇", "자율주행", "휴머노이드", "드론"]),
    ("게임/엔터", ["게임", "엔터", "미디어", "콘텐츠", "K-POP", "웹툰"]),
    ("자동차/모빌리티", ["자동차", "모빌리티", "EV", "전기차"]),
    ("친환경/신재생", ["친환경", "신재생", "태양광", "풍력", "수소", "탄소", "ESG", "그린"]),
    ("원자력", ["원자력", "원전", "SMR", "우라늄"]),
    ("방산/우주항공", ["방산", "우주", "항공", "국방", "K-방산"]),
    ("철강/조선", ["철강", "조선", "해운"]),
    ("에너지/석유", ["에너지", "석유", "가스", "원유", "정유"]),
    ("화학/소재", ["화학", "소재", "신소재", "에너지화학", "케미칼", "철강금속"]),
    ("통신/5G", ["통신", "5G", "6G", "텔레콤"]),
    ("금융", ["금융", "은행", "보험", "증권", "핀테크"]),
    ("리츠/부동산", ["리츠", "부동산", "REITs"]),
    ("건설/인프라", ["건설", "인프라", "토목"]),
    ("음식료/식품", ["음식", "식품", "농산물", "F&B", "필수소비", "생활소비", "소비재"]),
    ("뷰티/화장품", ["뷰티", "화장품", "K-뷰티", "K뷰티", "화장"]),
    ("운송/물류", ["운송", "물류", "택배", "해운물류", "항공운송", "교통"]),
    ("농업", ["농업", "농산"]),
    ("글로벌/해외", ["미국", "중국", "일본", "글로벌", "해외", "S&P", "나스닥", "MSCI", "선진국", "신흥국", "유럽", "인도", "베트남"]),
    ("채권", ["채권", "국채", "회사채", "금리", "단기자금", "머니마켓", "CD", "CP"]),
    ("원자재", ["원자재", "금", "은", "구리", "곡물"]),
    ("고배당", ["고배당", "배당", "밸류업"]),
    ("레버리지/인버스", ["레버리지", "인버스", "2X", "곱버스"]),
    ("TDF/은퇴", ["TDF", "TRF", "은퇴", "라이프사이클"]),
    ("지수추종", ["KOSPI", "코스피", "KOSDAQ", "코스닥", "KRX", "200", "100", "50"]),
]


def classify_industry(etf_name):
    """ETF 이름에서 산업 분류"""
    for industry, keywords in INDUSTRY_KEYWORDS:
        for kw in keywords:
            if kw.lower() in etf_name.lower():
                return industry
    return "기타"


# ── 네이버 API 내장 키 ──
NAVER_CLIENT_ID = "9OA3EUfW54SRzrjscoPB"
NAVER_CLIENT_SECRET = "s1u4T_kxkr"


def check_credentials():
    """API 키 확인 (KRX 로그인 불필요, 네이버 API 내장)"""
    print("[OK] pykrx 공개 데이터 사용 (KRX 로그인 불필요)")
    print("[OK] 네이버 API 키 확인 (내장)")
    return True


def get_latest_business_date():
    """가장 최근 영업일 추정 (주말 제외)"""
    from pykrx import stock
    today = datetime.now()
    # 최근 10일 범위에서 실제 거래일 조회
    start = (today - timedelta(days=15)).strftime("%Y%m%d")
    end = today.strftime("%Y%m%d")
    try:
        dates = stock.get_previous_business_days(fromdate=start, todate=end)
        if len(dates) > 0:
            return dates[-1].strftime("%Y%m%d")
    except Exception:
        pass
    # fallback
    d = today
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d.strftime("%Y%m%d")


def get_business_days(n_days):
    """최근 n영업일의 날짜 리스트 반환 (주말/공휴일/장중 모두 대응)"""
    from pykrx import stock
    today = datetime.now()
    # 충분히 넓은 범위로 조회 (공휴일 연휴 대비)
    start = (today - timedelta(days=max(n_days * 3, 30))).strftime("%Y%m%d")
    end = today.strftime("%Y%m%d")
    try:
        dates = stock.get_previous_business_days(fromdate=start, todate=end)
        if len(dates) == 0:
            # 오늘 포함 범위에 영업일이 없으면 더 넓게 조회
            start = (today - timedelta(days=60)).strftime("%Y%m%d")
            dates = stock.get_previous_business_days(fromdate=start, todate=end)
        if len(dates) > 0:
            return [d.strftime("%Y%m%d") for d in dates[-n_days:]]
    except Exception:
        pass
    # fallback: 주말을 건너뛰고 가장 최근 평일 반환
    d = today
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return [d.strftime("%Y%m%d")]


def get_existing_dates(csv_path, date_col="date"):
    """기존 CSV에서 이미 수집된 날짜 목록"""
    if not os.path.exists(csv_path):
        return set()
    try:
        df = pd.read_csv(csv_path, encoding="utf-8-sig", usecols=[date_col])
        return set(df[date_col].astype(str).str[:10].unique())
    except Exception:
        return set()


# ═══════════════════════════════════════════
# 1. ETF 마스터 수집
# ═══════════════════════════════════════════
def collect_etf_master(ref_date):
    """ETF 마스터 목록 수집 (KRX 응답 없으면 기존 파일 사용)"""
    from pykrx import stock
    print(f"\n[1/6] ETF 마스터 수집 (기준일: {ref_date})...")

    path = os.path.join(DATA_DIR, "etf_master.csv")

    try:
        tickers = stock.get_etf_ticker_list(ref_date)
        if not tickers:
            raise ValueError("빈 티커 목록")

        rows = []
        for t in tickers:
            name = stock.get_etf_ticker_name(t)
            industry = classify_industry(name)
            rows.append({"ticker": t, "name": name, "industry": industry})

        df = pd.DataFrame(rows)
        df.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"  저장 완료: {len(df)}개 ETF → {path}")
        return df

    except Exception as e:
        print(f"  [!] KRX 응답 없음: {e}")
        if os.path.exists(path):
            print(f"  → 기존 etf_master.csv 사용")
            return pd.read_csv(path, encoding="utf-8-sig", dtype={"ticker": str})
        else:
            raise RuntimeError("etf_master.csv가 없고 KRX도 응답하지 않습니다.")


# ═══════════════════════════════════════════
# 2. ETF 가격 수집
# ═══════════════════════════════════════════
def collect_etf_prices(dates):
    """ETF OHLCV 날짜별 수집 (신규 날짜만)"""
    from pykrx import stock
    csv_path = os.path.join(DATA_DIR, "etf_prices.csv")
    existing = get_existing_dates(csv_path)

    new_dates = [d for d in dates if d[:4] + "-" + d[4:6] + "-" + d[6:] not in existing]
    if not new_dates:
        print("\n[2/6] ETF 가격: 이미 최신 상태")
        return

    print(f"\n[2/6] ETF 가격 수집 ({len(new_dates)}일)...")
    all_rows = []
    for i, date in enumerate(new_dates):
        print(f"  {i+1}/{len(new_dates)} {date}...", end=" ")
        try:
            df = stock.get_etf_ohlcv_by_ticker(date)
            if len(df) == 0:
                print("데이터 없음")
                continue
            df = df.reset_index()
            df.columns = ["ticker", "nav", "open", "high", "low", "close", "volume", "trading_value", "base_index"]
            df["date"] = f"{date[:4]}-{date[4:6]}-{date[6:]}"
            df["ticker"] = df["ticker"].astype(str)
            all_rows.append(df)
            print(f"{len(df)}개 ETF")
        except Exception as e:
            print(f"오류: {e}")
        time.sleep(1)

    if all_rows:
        new_df = pd.concat(all_rows, ignore_index=True)
        # 기존 데이터에 추가
        if os.path.exists(csv_path):
            old_df = pd.read_csv(csv_path, encoding="utf-8-sig", dtype={"ticker": str})
            combined = pd.concat([old_df, new_df], ignore_index=True)
            combined = combined.drop_duplicates(subset=["date", "ticker"], keep="last")
        else:
            combined = new_df
        combined = combined.sort_values(["date", "ticker"])
        combined.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"  저장 완료: {len(new_df)}행 추가 → 총 {len(combined)}행")


# ═══════════════════════════════════════════
# 3. ETF PDF (구성종목) 수집
# ═══════════════════════════════════════════
def collect_etf_pdf(dates, etf_master):
    """ETF PDF 구성종목 날짜별 수집"""
    from pykrx import stock
    csv_path = os.path.join(DATA_DIR, "etf_pdf_valid392.csv")
    existing = get_existing_dates(csv_path, date_col="base_date")

    new_dates = [d for d in dates if d[:4] + "-" + d[4:6] + "-" + d[6:] not in existing]
    if not new_dates:
        print("\n[3/6] ETF PDF: 이미 최신 상태")
        return

    # 정상 PDF ETF 목록 (기존 valid392 기준 또는 전체)
    valid_tickers = set(etf_master["ticker"].tolist())
    if os.path.exists(csv_path):
        old_pdf = pd.read_csv(csv_path, encoding="utf-8-sig", dtype={"etf_ticker": str}, nrows=1000)
        if "etf_ticker" in old_pdf.columns:
            valid_tickers = set(old_pdf["etf_ticker"].unique())

    print(f"\n[3/6] ETF PDF 수집 ({len(new_dates)}일, {len(valid_tickers)}개 ETF)...")

    for i, date in enumerate(new_dates):
        print(f"  {i+1}/{len(new_dates)} {date}...")
        date_rows = []
        count = 0
        for ticker in valid_tickers:
            try:
                # pykrx PDF 조회 시 stderr 억제
                with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                    pdf_df = stock.get_etf_portfolio_deposit_file(ticker, date)

                if pdf_df is None or len(pdf_df) == 0:
                    continue

                pdf_df = pdf_df.reset_index()
                # 컬럼명 표준화
                col_map = {}
                cols = pdf_df.columns.tolist()
                if len(cols) >= 1:
                    col_map[cols[0]] = "stock_ticker"
                if len(cols) >= 2:
                    col_map[cols[1]] = "stock_name"
                if len(cols) >= 3:
                    col_map[cols[2]] = "contracts"
                if len(cols) >= 4:
                    col_map[cols[3]] = "amount"
                if len(cols) >= 5:
                    col_map[cols[4]] = "market_cap"
                if len(cols) >= 6:
                    col_map[cols[5]] = "weight"

                pdf_df = pdf_df.rename(columns=col_map)
                pdf_df["etf_ticker"] = ticker
                pdf_df["base_date"] = f"{date[:4]}-{date[4:6]}-{date[6:]}"

                std_cols = ["etf_ticker", "base_date", "stock_ticker", "stock_name",
                           "contracts", "amount", "market_cap", "weight"]
                for c in std_cols:
                    if c not in pdf_df.columns:
                        pdf_df[c] = 0

                date_rows.append(pdf_df[std_cols])
                count += 1
            except Exception:
                continue

        if date_rows:
            new_df = pd.concat(date_rows, ignore_index=True)
            # 기존 파일에 병합
            if os.path.exists(csv_path):
                old_df = pd.read_csv(csv_path, encoding="utf-8-sig",
                                     dtype={"etf_ticker": str, "stock_ticker": str})
                combined = pd.concat([old_df, new_df], ignore_index=True)
                combined = combined.drop_duplicates(
                    subset=["etf_ticker", "base_date", "stock_ticker", "stock_name"],
                    keep="last"
                )
            else:
                combined = new_df
            combined.to_csv(csv_path, index=False, encoding="utf-8-sig")
            print(f"    → {count}개 ETF, {len(new_df)}행 추가")
        else:
            print(f"    → 데이터 없음")

        time.sleep(2)  # 세션 부하 방지


# ═══════════════════════════════════════════
# 4. 시장 지수 수집
# ═══════════════════════════════════════════
def collect_index(dates):
    """KOSPI, KOSDAQ 지수 수집"""
    from pykrx import stock
    csv_path = os.path.join(DATA_DIR, "index.csv")
    existing = get_existing_dates(csv_path)

    new_dates = [d for d in dates if d[:4] + "-" + d[4:6] + "-" + d[6:] not in existing]
    if not new_dates:
        print("\n[4/6] 시장 지수: 이미 최신 상태")
        return

    print(f"\n[4/6] 시장 지수 수집 ({len(new_dates)}일)...")
    all_rows = []
    for date in new_dates:
        for code, name in [("1001", "KOSPI"), ("2001", "KOSDAQ")]:
            try:
                df = stock.get_index_ohlcv(date, date, code)
                if len(df) > 0:
                    row = df.iloc[0]
                    all_rows.append({
                        "date": f"{date[:4]}-{date[4:6]}-{date[6:]}",
                        "index_code": code,
                        "open": row.get("시가", 0),
                        "high": row.get("고가", 0),
                        "low": row.get("저가", 0),
                        "close": row.get("종가", 0),
                        "volume": row.get("거래량", 0),
                    })
            except Exception:
                continue
        time.sleep(0.5)

    if all_rows:
        new_df = pd.DataFrame(all_rows)
        if os.path.exists(csv_path):
            old_df = pd.read_csv(csv_path, encoding="utf-8-sig")
            combined = pd.concat([old_df, new_df], ignore_index=True)
            combined = combined.drop_duplicates(subset=["date", "index_code"], keep="last")
        else:
            combined = new_df
        combined = combined.sort_values(["date", "index_code"])
        combined.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"  저장 완료: {len(all_rows)}행 추가")


# ═══════════════════════════════════════════
# 5. 개별 종목 가격 수집
# ═══════════════════════════════════════════
def collect_stock_prices(dates):
    """주요 종목 주가 수집"""
    from pykrx import stock
    csv_path = os.path.join(DATA_DIR, "stock_prices.csv")
    existing = get_existing_dates(csv_path)

    new_dates = [d for d in dates if d[:4] + "-" + d[4:6] + "-" + d[6:] not in existing]
    if not new_dates:
        print("\n[5/6] 종목 가격: 이미 최신 상태")
        return

    # stocks_master에서 종목 목록 가져오기
    master_path = os.path.join(DATA_DIR, "stocks_master.csv")
    if os.path.exists(master_path):
        sm = pd.read_csv(master_path, encoding="utf-8-sig", dtype={"ticker": str})
        tickers = sm["ticker"].tolist()
    else:
        print("\n[5/6] 종목 가격: stocks_master.csv 없음, 건너뜀")
        return

    print(f"\n[5/6] 종목 가격 수집 ({len(new_dates)}일)...")
    all_rows = []
    for i, date in enumerate(new_dates):
        print(f"  {i+1}/{len(new_dates)} {date}...", end=" ")
        try:
            # 날짜별 전체 시세 조회
            kospi = stock.get_market_ohlcv(date, market="KOSPI")
            kosdaq = stock.get_market_ohlcv(date, market="KOSDAQ")
            full = pd.concat([kospi, kosdaq])
            full = full.reset_index()
            full.columns = ["ticker", "open", "high", "low", "close", "volume", "trading_value", "change_rate", "market_cap"][:len(full.columns)]
            full["date"] = f"{date[:4]}-{date[4:6]}-{date[6:]}"
            full["ticker"] = full["ticker"].astype(str)
            # 관심 종목만 필터
            filtered = full[full["ticker"].isin(set(tickers))]
            all_rows.append(filtered[["date", "ticker", "open", "high", "low", "close", "volume", "change_rate"]])
            print(f"{len(filtered)}개 종목")
        except Exception as e:
            print(f"오류: {e}")
        time.sleep(1)

    if all_rows:
        new_df = pd.concat(all_rows, ignore_index=True)
        if os.path.exists(csv_path):
            old_df = pd.read_csv(csv_path, encoding="utf-8-sig", dtype={"ticker": str})
            combined = pd.concat([old_df, new_df], ignore_index=True)
            combined = combined.drop_duplicates(subset=["date", "ticker"], keep="last")
        else:
            combined = new_df
        combined = combined.sort_values(["date", "ticker"])
        combined.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"  저장 완료: {len(new_df)}행 추가 → 총 {len(combined)}행")


# ═══════════════════════════════════════════
# 6. 뉴스 수집
# ═══════════════════════════════════════════
def collect_news():
    """네이버 뉴스 API로 산업별 뉴스 수집"""
    import requests

    # 내장 키 우선, 환경변수 fallback
    client_id = NAVER_CLIENT_ID or os.environ.get("NAVER_CLIENT_ID")
    client_secret = NAVER_CLIENT_SECRET or os.environ.get("NAVER_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("\n[6/6] 뉴스 수집: API 키 없음, 건너뜀")
        return

    print(f"\n[6/6] 뉴스 수집...")

    # 산업별 검색 키워드 (회사명 제외, 산업/시장 키워드)
    industry_queries = {
        "반도체": ["반도체 주가", "반도체 산업", "HBM 시장", "파운드리 수주"],
        "2차전지": ["2차전지 주가", "배터리 산업", "리튬 시장", "전고체 배터리"],
        "바이오/헬스": ["바이오 주가", "제약 산업", "신약 개발", "헬스케어 시장"],
        "AI/소프트웨어": ["AI 주가", "인공지능 산업", "클라우드 시장", "AI 반도체"],
        "로봇/자율주행": ["로봇 주가", "자율주행 산업", "휴머노이드 로봇", "드론 시장"],
        "게임/엔터": ["게임 주가", "엔터테인먼트 산업", "콘텐츠 수출"],
        "자동차/모빌리티": ["자동차 주가", "전기차 산업", "모빌리티 시장"],
        "친환경/신재생": ["신재생에너지 주가", "태양광 산업", "풍력 시장", "수소 경제"],
        "원자력": ["원자력 주가", "원전 산업", "SMR 시장"],
        "방산/우주항공": ["방산 주가", "우주항공 산업", "K방산 수출"],
        "철강/조선": ["철강 주가", "조선 산업", "선박 수주"],
        "에너지/석유": ["에너지 주가", "석유 시장", "정유 산업"],
        "화학/소재": ["화학 주가", "소재 산업", "신소재 시장"],
        "통신/5G": ["통신 주가", "5G 산업", "6G 개발"],
        "금융": ["금융 주가", "은행 산업", "핀테크 시장"],
        "리츠/부동산": ["리츠 주가", "부동산 시장", "상업용 부동산"],
        "건설/인프라": ["건설 주가", "인프라 산업", "건설 수주"],
        "음식료/식품": ["식품 주가", "음식료 산업", "식품 수출"],
        "뷰티/화장품": ["화장품 주가", "뷰티 산업", "K뷰티 수출"],
        "운송/물류": ["운송 주가", "물류 산업", "해운 시장"],
        "농업": ["농업 주가", "농산물 시장"],
    }

    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }

    all_news = []
    seen_links = set()

    for industry, queries in industry_queries.items():
        print(f"  {industry}...", end=" ")
        count = 0
        for query in queries:
            try:
                url = "https://openapi.naver.com/v1/search/news.json"
                params = {
                    "query": query,
                    "display": 20,
                    "start": 1,
                    "sort": "date",
                }
                resp = requests.get(url, headers=headers, params=params, timeout=10)
                if resp.status_code != 200:
                    continue

                items = resp.json().get("items", [])
                for item in items:
                    olink = item.get("originallink", "")
                    if olink in seen_links:
                        continue
                    seen_links.add(olink)

                    # HTML 태그 제거
                    title = item.get("title", "").replace("<b>", "").replace("</b>", "")
                    desc = item.get("description", "").replace("<b>", "").replace("</b>", "")

                    all_news.append({
                        "industry": industry,
                        "keyword": query,
                        "title": title,
                        "description": desc,
                        "originallink": olink,
                        "link": item.get("link", ""),
                        "pubDate": item.get("pubDate", ""),
                        "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    })
                    count += 1

                time.sleep(0.15)  # API rate limit
            except Exception:
                continue
        print(f"{count}건")

    if all_news:
        new_df = pd.DataFrame(all_news)
        csv_path = os.path.join(DATA_DIR, "news.csv")
        history_dir = os.path.join(DATA_DIR, "news_history")
        os.makedirs(history_dir, exist_ok=True)

        # 날짜별 아카이브 저장 (과거 데이터 누적)
        today_str = datetime.now().strftime("%Y-%m-%d")
        history_path = os.path.join(history_dir, f"news_{today_str}.csv")
        if os.path.exists(history_path):
            old_hist = pd.read_csv(history_path, encoding="utf-8-sig")
            hist_combined = pd.concat([old_hist, new_df], ignore_index=True)
            hist_combined = hist_combined.drop_duplicates(subset=["originallink"], keep="first")
            hist_combined.to_csv(history_path, index=False, encoding="utf-8-sig")
        else:
            new_df.to_csv(history_path, index=False, encoding="utf-8-sig")
        print(f"  아카이브 저장: {history_path}")

        # 메인 news.csv에도 누적 (전체 히스토리)
        if os.path.exists(csv_path):
            old_df = pd.read_csv(csv_path, encoding="utf-8-sig")
            combined = pd.concat([new_df, old_df], ignore_index=True)
            combined = combined.drop_duplicates(subset=["originallink"], keep="first")
        else:
            combined = new_df

        combined.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"  저장 완료: {len(new_df)}건 수집 → 총 {len(combined)}건 (중복 제거 후)")


# ═══════════════════════════════════════════
# 메인
# ═══════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="SFNI 데이터 수집")
    parser.add_argument("--days", type=int, default=1, help="수집할 영업일 수 (기본: 1)")
    parser.add_argument("--full", action="store_true", help="전체 재수집 (60영업일)")
    parser.add_argument("--skip-pdf", action="store_true", help="PDF 수집 건너뛰기 (시간 절약)")
    parser.add_argument("--news-only", action="store_true", help="뉴스만 수집")
    args = parser.parse_args()

    print("=" * 60)
    print("SFNI 데이터 수집")
    print("=" * 60)

    check_credentials()

    # pykrx는 공개 데이터 접근 — 로그인 불필요
    # KRX 로그인 정보가 있으면 선택적으로 사용 (PDF 수집 등)
    krx_id = os.environ.get("KRX_ID")
    krx_pw = os.environ.get("KRX_PW")
    if krx_id and krx_pw:
        from pykrx import stock
        try:
            stock.set_login(krx_id, krx_pw)
            print("[OK] KRX 로그인 성공 (선택적)")
        except Exception:
            print("[INFO] KRX 로그인 생략 — 공개 데이터로 진행")

    if args.news_only:
        collect_news()
        print("\n뉴스 수집 완료!")
        return

    # 수집 날짜 결정
    n_days = 60 if args.full else args.days
    dates = get_business_days(n_days)
    print(f"\n수집 기간: {dates[0]} ~ {dates[-1]} ({len(dates)}영업일)")

    # 1. ETF 마스터
    etf_master = collect_etf_master(dates[-1])

    # 2. ETF 가격
    collect_etf_prices(dates)

    # 3. ETF PDF
    if not args.skip_pdf:
        collect_etf_pdf(dates, etf_master)
    else:
        print("\n[3/6] ETF PDF: 건너뜀 (--skip-pdf)")

    # 4. 시장 지수
    collect_index(dates)

    # 5. 종목 가격
    collect_stock_prices(dates)

    # 6. 뉴스
    collect_news()

    print("\n" + "=" * 60)
    print("수집 완료!")
    print("다음 명령으로 대시보드 데이터를 갱신하세요:")
    print("  py scripts/process_data.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
