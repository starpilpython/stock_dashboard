"""
SFNI 대시보드 데이터 전처리 스크립트
CSV 데이터를 분석하여 프론트엔드용 JSON 파일을 생성한다.
"""

import pandas as pd
import numpy as np
import json
import os
from datetime import datetime
from email.utils import parsedate_to_datetime

# ── 경로 설정 ──
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUT_DIR = os.path.join(BASE_DIR, "public", "data")
os.makedirs(OUT_DIR, exist_ok=True)

# ── 산업 색상 매핑 ──
INDUSTRY_COLORS = {
    "반도체": "#F59E0B",
    "2차전지": "#10B981",
    "바이오/헬스": "#EC4899",
    "AI/소프트웨어": "#8B5CF6",
    "로봇/자율주행": "#3B82F6",
    "게임/엔터": "#F97316",
    "자동차/모빌리티": "#EAB308",
    "친환경/신재생": "#22C55E",
    "원자력": "#06B6D4",
    "방산/우주항공": "#6366F1",
    "철강/조선": "#78716C",
    "에너지/석유": "#D97706",
    "화학/소재": "#14B8A6",
    "통신/5G": "#0EA5E9",
    "금융": "#A855F7",
    "리츠/부동산": "#F43F5E",
    "건설/인프라": "#84CC16",
    "음식료/식품": "#FB923C",
    "뷰티/화장품": "#E879F9",
    "운송/물류": "#64748B",
    "농업": "#4ADE80",
}

# 대시보드에 표시할 주요 산업 (투자 테마 산업만)
TARGET_INDUSTRIES = [
    "반도체", "2차전지", "바이오/헬스", "AI/소프트웨어", "로봇/자율주행",
    "게임/엔터", "자동차/모빌리티", "친환경/신재생", "원자력",
    "방산/우주항공", "철강/조선", "에너지/석유", "화학/소재",
    "통신/5G", "금융", "리츠/부동산", "건설/인프라",
    "음식료/식품", "뷰티/화장품", "운송/물류", "농업",
]


def load_data():
    """CSV 데이터 로드"""
    print("Loading CSV data...")

    etf_master = pd.read_csv(
        os.path.join(DATA_DIR, "etf_master.csv"),
        encoding="utf-8-sig",
        dtype={"ticker": str},
    )

    etf_prices = pd.read_csv(
        os.path.join(DATA_DIR, "etf_prices.csv"),
        encoding="utf-8-sig",
        dtype={"ticker": str},
        parse_dates=["date"],
    )

    # ETF PDF (구성종목) — 파일이 없으면 빈 DataFrame
    etf_pdf_path = os.path.join(DATA_DIR, "etf_pdf_valid392.csv")
    if os.path.exists(etf_pdf_path):
        etf_pdf = pd.read_csv(
            etf_pdf_path,
            encoding="utf-8-sig",
            dtype={"etf_ticker": str, "stock_ticker": str},
        )
    else:
        print("  [!] etf_pdf_valid392.csv 없음 — 구성종목 분석 건너뜀")
        etf_pdf = pd.DataFrame(columns=[
            "etf_ticker", "base_date", "stock_ticker", "stock_name",
            "contracts", "amount", "market_cap", "weight"
        ])

    news = pd.read_csv(
        os.path.join(DATA_DIR, "news.csv"),
        encoding="utf-8-sig",
    )

    index_df = pd.read_csv(
        os.path.join(DATA_DIR, "index.csv"),
        encoding="utf-8-sig",
        parse_dates=["date"],
    )

    stock_prices = pd.read_csv(
        os.path.join(DATA_DIR, "stock_prices.csv"),
        encoding="utf-8-sig",
        dtype={"ticker": str},
        parse_dates=["date"],
    )

    stocks_master = pd.read_csv(
        os.path.join(DATA_DIR, "stocks_master.csv"),
        encoding="utf-8-sig",
        dtype={"ticker": str},
    )

    print(f"  etf_master: {len(etf_master)} rows")
    print(f"  etf_prices: {len(etf_prices)} rows")
    print(f"  etf_pdf: {len(etf_pdf)} rows")
    print(f"  news: {len(news)} rows")
    print(f"  stock_prices: {len(stock_prices)} rows")

    return etf_master, etf_prices, etf_pdf, news, index_df, stock_prices, stocks_master


def parse_news_dates(news):
    """뉴스 pubDate를 파싱하여 date 컬럼 생성"""
    dates = []
    for d in news["pubDate"]:
        try:
            parsed = parsedate_to_datetime(d)
            dates.append(parsed.strftime("%Y-%m-%d"))
        except Exception:
            dates.append(None)
    news["date"] = dates
    news = news.dropna(subset=["date"])
    return news


def _compute_industry_returns(prices, dates, period_days):
    """산업별 수익률 계산 (지정 기간)"""
    n = min(period_days, len(dates))
    latest_date = dates[-1]
    base_date = dates[-n] if n > 0 else dates[0]

    industry_returns = {}
    for ind in TARGET_INDUSTRIES:
        ind_data = prices[prices["industry"] == ind]
        if len(ind_data) == 0:
            industry_returns[ind] = 0
            continue
        latest_close = ind_data[ind_data["date"] == latest_date].groupby("ticker")["close"].last()
        base_close = ind_data[ind_data["date"] == base_date].groupby("ticker")["close"].last()
        common = latest_close.index.intersection(base_close.index)
        if len(common) > 0:
            ret = ((latest_close[common] - base_close[common]) / base_close[common] * 100).mean()
            industry_returns[ind] = ret
        else:
            industry_returns[ind] = 0
    return pd.Series(industry_returns)


def compute_etf_flow_scores(etf_prices, etf_master):
    """산업별 ETF Flow Score 계산"""
    print("Computing ETF Flow Scores...")

    # etf_prices에 산업 매핑
    prices = etf_prices.merge(
        etf_master[["ticker", "industry"]], on="ticker", how="left"
    )
    prices = prices[prices["industry"].isin(TARGET_INDUSTRIES)]

    dates = sorted(prices["date"].unique())

    # 최근 날짜 기준
    latest_dates = dates[-5:]  # 최근 5영업일
    prev_dates = dates[-10:-5] if len(dates) >= 10 else dates[:5]  # 직전 5영업일

    # 산업별 거래대금 합산
    recent = prices[prices["date"].isin(latest_dates)]
    prev = prices[prices["date"].isin(prev_dates)]

    recent_tv = recent.groupby("industry")["trading_value"].sum()
    prev_tv = prev.groupby("industry")["trading_value"].sum()

    # 거래대금 증가율
    tv_change = ((recent_tv - prev_tv) / prev_tv * 100).fillna(0)

    # 산업별 수익률 계산 (최근 5일)
    returns_series = _compute_industry_returns(prices, dates, 5)

    # 거래량 증가율
    recent_vol = recent.groupby("industry")["volume"].sum()
    prev_vol = prev.groupby("industry")["volume"].sum()
    vol_change = ((recent_vol - prev_vol) / prev_vol * 100).fillna(0)

    # 긍정적 흐름 ETF 수 (수익률 양수인 ETF 비율)
    positive_etf_ratio = {}
    for ind in TARGET_INDUSTRIES:
        ind_data = prices[prices["industry"] == ind]
        latest = ind_data[ind_data["date"] == dates[-1]]
        first = ind_data[ind_data["date"] == dates[-5]] if len(dates) >= 5 else ind_data[ind_data["date"] == dates[0]]
        if len(latest) == 0 or len(first) == 0:
            positive_etf_ratio[ind] = 50
            continue
        merged = latest[["ticker", "close"]].merge(first[["ticker", "close"]], on="ticker", suffixes=("_now", "_prev"))
        if len(merged) > 0:
            pos_ratio = (merged["close_now"] > merged["close_prev"]).mean() * 100
            positive_etf_ratio[ind] = pos_ratio
        else:
            positive_etf_ratio[ind] = 50

    pos_ratio_series = pd.Series(positive_etf_ratio)

    # Min-Max 정규화 함수
    def normalize(s):
        if s.max() == s.min():
            return pd.Series(50, index=s.index)
        return ((s - s.min()) / (s.max() - s.min()) * 100)

    # ETF Flow Score = 40% 거래대금증가율 + 30% 수익률모멘텀 + 20% 거래량증가율 + 10% 긍정ETF비율
    tv_norm = normalize(tv_change.reindex(TARGET_INDUSTRIES, fill_value=0))
    ret_norm = normalize(returns_series.reindex(TARGET_INDUSTRIES, fill_value=0))
    vol_norm = normalize(vol_change.reindex(TARGET_INDUSTRIES, fill_value=0))
    pos_norm = normalize(pos_ratio_series.reindex(TARGET_INDUSTRIES, fill_value=50))

    flow_score = tv_norm * 0.4 + ret_norm * 0.3 + vol_norm * 0.2 + pos_norm * 0.1

    # 원본 데이터도 함께 반환
    raw_data = pd.DataFrame({
        "trading_value_change": tv_change.reindex(TARGET_INDUSTRIES, fill_value=0),
        "return_5d": returns_series.reindex(TARGET_INDUSTRIES, fill_value=0),
        "volume_change": vol_change.reindex(TARGET_INDUSTRIES, fill_value=0),
        "positive_etf_ratio": pos_ratio_series.reindex(TARGET_INDUSTRIES, fill_value=50),
    })

    # 산업별 거래대금 (최근 5일 합계, 억 원 단위)
    recent_tv_total = recent_tv.reindex(TARGET_INDUSTRIES, fill_value=0) / 1e8

    # ── 기간별 수익률 (1주/1개월/3개월) ──
    period_returns = {}
    for label, days in [("1w", 5), ("1m", 20), ("3m", 60)]:
        period_returns[label] = _compute_industry_returns(prices, dates, days)

    return flow_score, raw_data, recent_tv_total, period_returns, prices, dates


def compute_news_scores(news):
    """산업별 뉴스 관심도 점수 및 감성 점수 계산"""
    print("Computing News Scores...")

    news = parse_news_dates(news)
    news = news[news["industry"].isin(TARGET_INDUSTRIES)]

    # ── 간단한 감성 분석 (키워드 기반) ──
    positive_keywords = [
        "상승", "급등", "호재", "성장", "개선", "증가", "확대", "수혜",
        "호조", "최고", "돌파", "강세", "기대", "유망", "수주", "투자",
        "상향", "흑자", "반등", "회복", "기록", "신고가", "순매수",
        "서프라이즈", "좋은", "긍정", "매수", "추천", "낙관",
    ]
    negative_keywords = [
        "하락", "급락", "악재", "감소", "위축", "부진", "손실",
        "적자", "위기", "우려", "리스크", "규제", "제재", "하향",
        "약세", "폭락", "매도", "경고", "둔화", "축소", "침체",
        "불안", "비관", "충격",
    ]

    def classify_sentiment(row):
        text = str(row.get("title", "")) + " " + str(row.get("description", ""))
        pos_count = sum(1 for kw in positive_keywords if kw in text)
        neg_count = sum(1 for kw in negative_keywords if kw in text)
        if pos_count > neg_count + 1:
            return "긍정"
        elif neg_count > pos_count + 1:
            return "부정"
        else:
            return "중립"

    news["sentiment"] = news.apply(classify_sentiment, axis=1)

    # 산업별 뉴스 통계
    industry_news = {}
    for ind in TARGET_INDUSTRIES:
        ind_news = news[news["industry"] == ind]
        total = len(ind_news)
        if total == 0:
            industry_news[ind] = {
                "total": 0, "positive": 0, "neutral": 0, "negative": 0,
                "pos_ratio": 0, "neg_ratio": 0, "neu_ratio": 0,
            }
            continue

        pos = len(ind_news[ind_news["sentiment"] == "긍정"])
        neg = len(ind_news[ind_news["sentiment"] == "부정"])
        neu = len(ind_news[ind_news["sentiment"] == "중립"])

        industry_news[ind] = {
            "total": total,
            "positive": pos,
            "neutral": neu,
            "negative": neg,
            "pos_ratio": round(pos / total * 100, 1),
            "neg_ratio": round(neg / total * 100, 1),
            "neu_ratio": round(neu / total * 100, 1),
        }

    # News Attention Score (50% 뉴스량 + 30% 키워드빈도 + 20% 고유언론사)
    news_counts = pd.Series({ind: industry_news[ind]["total"] for ind in TARGET_INDUSTRIES})

    # 고유 언론사 수 (originallink 도메인 기반)
    unique_sources = {}
    for ind in TARGET_INDUSTRIES:
        ind_news = news[news["industry"] == ind]
        if len(ind_news) == 0:
            unique_sources[ind] = 0
            continue
        domains = ind_news["originallink"].dropna().apply(
            lambda x: x.split("/")[2] if len(x.split("/")) > 2 else ""
        )
        unique_sources[ind] = domains.nunique()

    sources_series = pd.Series(unique_sources)

    def normalize(s):
        if s.max() == s.min():
            return pd.Series(50, index=s.index)
        return ((s - s.min()) / (s.max() - s.min()) * 100)

    news_norm = normalize(news_counts)
    sources_norm = normalize(sources_series)

    attention_score = news_norm * 0.7 + sources_norm * 0.3

    # Sentiment Score (60% 긍정비율 + 30% 감성모멘텀(없으므로 50) + 10% 부정리스크조정)
    pos_ratios = pd.Series({ind: industry_news[ind]["pos_ratio"] for ind in TARGET_INDUSTRIES})
    neg_ratios = pd.Series({ind: industry_news[ind]["neg_ratio"] for ind in TARGET_INDUSTRIES})

    pos_norm = normalize(pos_ratios)
    # 부정리스크: 부정비율이 높을수록 점수가 낮아야 함
    neg_adjust = normalize(100 - neg_ratios)
    momentum_placeholder = pd.Series(50, index=pd.Index(TARGET_INDUSTRIES))

    sentiment_score = pos_norm * 0.6 + momentum_placeholder * 0.3 + neg_adjust * 0.1

    # 헤드라인 추출 (산업별 최신 5개)
    headlines = {}
    for ind in TARGET_INDUSTRIES:
        ind_news = news[news["industry"] == ind].head(5)
        h_list = []
        for _, row in ind_news.iterrows():
            h_list.append({
                "title": row["title"],
                "sentiment": row["sentiment"],
                "date": row["date"],
                "link": row.get("link", ""),
            })
        headlines[ind] = h_list

    return attention_score, sentiment_score, industry_news, headlines


def compute_is_scores(flow_score, attention_score, sentiment_score):
    """Industry Signal Score 계산"""
    print("Computing IS Scores...")
    is_score = flow_score * 0.5 + attention_score * 0.3 + sentiment_score * 0.2
    return is_score


def get_representative_etfs(etf_master, etf_prices):
    """산업별 대표 ETF (거래대금 최대) 선정"""
    prices = etf_prices.merge(etf_master[["ticker", "name", "industry"]], on="ticker", how="left")
    prices = prices[prices["industry"].isin(TARGET_INDUSTRIES)]

    latest_date = prices["date"].max()
    latest = prices[prices["date"] == latest_date]
    rep_etfs = latest.sort_values("trading_value", ascending=False).groupby("industry").first().reset_index()

    result = {}
    for _, row in rep_etfs.iterrows():
        result[row["industry"]] = {
            "ticker": row["ticker"],
            "name": row["name"],
            "trading_value": int(row["trading_value"]),
        }
    return result


def get_industry_stocks(etf_pdf, etf_master, stocks_master, stock_prices, available_dates=None):
    """산업별 핵심 구성종목 추출"""
    print("Computing Industry Stocks...")

    # etf_pdf에 산업 매핑
    pdf = etf_pdf.merge(
        etf_master[["ticker", "industry"]].rename(columns={"ticker": "etf_ticker"}),
        on="etf_ticker",
        how="left",
    )
    pdf = pdf[pdf["industry"].isin(TARGET_INDUSTRIES)]

    # 날짜 목록 (ETF 매집 신호 계산용)
    all_dates = sorted(pdf["base_date"].unique())
    latest_date = all_dates[-1]
    pdf_latest = pdf[pdf["base_date"] == latest_date]

    # 1주 전, 2주 전 기준일 (약 5영업일, 10영업일 전)
    date_1w_ago = all_dates[-5] if len(all_dates) >= 5 else all_dates[0]
    date_2w_ago = all_dates[-10] if len(all_dates) >= 10 else all_dates[0]

    # 산업별 종목 비중 합산
    industry_stocks = {}
    for ind in TARGET_INDUSTRIES:
        ind_pdf = pdf_latest[pdf_latest["industry"] == ind]
        if len(ind_pdf) == 0:
            industry_stocks[ind] = []
            continue

        # stock_ticker별 비중 합산 (여러 ETF에 걸쳐)
        stock_weights = (
            ind_pdf.groupby(["stock_ticker", "stock_name"])["weight"]
            .sum()
            .reset_index()
            .sort_values("weight", ascending=False)
        )

        # 순수 주식 종목만 필터 (6자리 숫자 티커)
        stock_weights = stock_weights[
            stock_weights["stock_ticker"].str.match(r"^\d{6}$", na=False)
        ]

        top_stocks = stock_weights.head(10)

        stocks_list = []
        for _, row in top_stocks.iterrows():
            ticker = row["stock_ticker"]
            name = row["stock_name"]

            # 주가 데이터 조회
            sp = stock_prices[stock_prices["ticker"] == ticker].sort_values("date")
            return_5d = 0
            recent_volumes = []
            if len(sp) >= 2:
                if len(sp) >= 5:
                    return_5d = round(
                        (sp["close"].iloc[-1] - sp["close"].iloc[-5])
                        / sp["close"].iloc[-5] * 100, 1
                    )
                    recent_volumes = sp["volume"].tail(5).tolist()
                else:
                    return_5d = round(
                        (sp["close"].iloc[-1] - sp["close"].iloc[0])
                        / sp["close"].iloc[0] * 100, 1
                    )
                    recent_volumes = sp["volume"].tail(5).tolist()

            # 기간별 수익률 (1주/1개월/3개월)
            period_stock_returns = {}
            for plabel, pdays in [("1w", 5), ("1m", 20), ("3m", 60)]:
                if len(sp) >= pdays:
                    r = round(
                        (sp["close"].iloc[-1] - sp["close"].iloc[-pdays])
                        / sp["close"].iloc[-pdays] * 100, 1
                    )
                elif len(sp) >= 2:
                    r = round(
                        (sp["close"].iloc[-1] - sp["close"].iloc[0])
                        / sp["close"].iloc[0] * 100, 1
                    )
                else:
                    r = 0
                period_stock_returns[plabel] = r

            # 일별 수량 증감 (최근 10일)
            volume_daily = []
            if len(sp) >= 2:
                sp_tail = sp.tail(10)
                for i in range(len(sp_tail)):
                    row_sp = sp_tail.iloc[i]
                    vol = int(row_sp["volume"])
                    if i == 0:
                        # 첫 날은 이전 데이터와 비교
                        idx = sp.index.get_loc(sp_tail.index[0])
                        if idx > 0:
                            prev_vol = int(sp.iloc[idx - 1]["volume"])
                            chg = round((vol - prev_vol) / max(prev_vol, 1) * 100, 1)
                        else:
                            chg = 0
                    else:
                        prev_vol = int(sp_tail.iloc[i - 1]["volume"])
                        chg = round((vol - prev_vol) / max(prev_vol, 1) * 100, 1)
                    volume_daily.append({
                        "date": str(row_sp["date"])[:10],
                        "volume": vol,
                        "change_pct": chg,
                    })

            # 주별 수량 증감 (최근 4주)
            volume_weekly = []
            if len(sp) >= 10:
                sp_recent = sp.tail(20).copy()
                sp_recent["date"] = pd.to_datetime(sp_recent["date"])
                sp_recent["week"] = sp_recent["date"].dt.isocalendar().week.astype(int)
                sp_recent["year"] = sp_recent["date"].dt.isocalendar().year.astype(int)
                weekly = sp_recent.groupby(["year", "week"]).agg(
                    avg_volume=("volume", "mean"),
                    start_date=("date", "min"),
                    end_date=("date", "max"),
                ).reset_index().sort_values(["year", "week"]).tail(4)
                for i, (_, wrow) in enumerate(weekly.iterrows()):
                    avg_vol = int(wrow["avg_volume"])
                    if i == 0:
                        chg = 0
                    else:
                        prev_avg = int(weekly.iloc[i - 1]["avg_volume"])
                        chg = round((avg_vol - prev_avg) / max(prev_avg, 1) * 100, 1)
                    volume_weekly.append({
                        "week_label": wrow["start_date"].strftime("%m/%d") + "~" + wrow["end_date"].strftime("%m/%d"),
                        "avg_volume": avg_vol,
                        "change_pct": chg,
                    })

            # ETF 매집 신호: 비중 변화 + 편입 ETF 수 변화
            ind_pdf_all = pdf[(pdf["industry"] == ind) & (pdf["stock_ticker"] == ticker)]
            etf_flow = []
            weight_now = 0
            weight_1w = 0
            weight_2w = 0
            etf_count_now = 0
            etf_count_1w = 0
            if len(ind_pdf_all) > 0:
                # 날짜별 비중 합계 & ETF 수
                daily_agg = ind_pdf_all.groupby("base_date").agg(
                    total_weight=("weight", "sum"),
                    etf_count=("etf_ticker", "nunique"),
                ).sort_index()

                weight_now = round(float(daily_agg.loc[latest_date, "total_weight"]), 2) if latest_date in daily_agg.index else 0
                weight_1w = round(float(daily_agg.loc[date_1w_ago, "total_weight"]), 2) if date_1w_ago in daily_agg.index else 0
                weight_2w = round(float(daily_agg.loc[date_2w_ago, "total_weight"]), 2) if date_2w_ago in daily_agg.index else 0
                etf_count_now = int(daily_agg.loc[latest_date, "etf_count"]) if latest_date in daily_agg.index else 0
                etf_count_1w = int(daily_agg.loc[date_1w_ago, "etf_count"]) if date_1w_ago in daily_agg.index else 0

                # 최근 10일 추이 데이터
                for d in all_dates[-10:]:
                    if d in daily_agg.index:
                        etf_flow.append({
                            "date": str(d)[:10],
                            "weight": round(float(daily_agg.loc[d, "total_weight"]), 2),
                            "etf_count": int(daily_agg.loc[d, "etf_count"]),
                        })

            weight_change_1w = round(weight_now - weight_1w, 2)
            weight_change_2w = round(weight_now - weight_2w, 2)
            etf_count_change = etf_count_now - etf_count_1w
            is_accumulating = weight_change_1w > 0 and etf_count_change >= 0

            stocks_list.append({
                "ticker": ticker,
                "name": name,
                "weight": round(row["weight"], 2),
                "return_5d": return_5d,
                "return_1w": period_stock_returns["1w"],
                "return_1m": period_stock_returns["1m"],
                "return_3m": period_stock_returns["3m"],
                "recent_volumes": [int(v) for v in recent_volumes],
                "volume_daily": volume_daily,
                "volume_weekly": volume_weekly,
                "etf_flow": etf_flow,
                "weight_now": weight_now,
                "weight_1w_ago": weight_1w,
                "weight_change_1w": weight_change_1w,
                "weight_change_2w": weight_change_2w,
                "etf_count_now": etf_count_now,
                "etf_count_change": etf_count_change,
                "is_accumulating": is_accumulating,
            })

        industry_stocks[ind] = stocks_list

    return industry_stocks


def get_market_summary(index_df, etf_prices):
    """시장 요약 정보"""
    print("Computing Market Summary...")

    # KOSPI (1001), KOSDAQ (2001)
    summary = {}
    for code, name in [("1001", "KOSPI"), ("2001", "KOSDAQ")]:
        idx = index_df[index_df["index_code"] == int(code) if index_df["index_code"].dtype != object else index_df["index_code"] == code]
        if len(idx) == 0:
            # string으로 시도
            idx = index_df[index_df["index_code"].astype(str) == code]
        if len(idx) >= 2:
            idx = idx.sort_values("date")
            last = idx.iloc[-1]
            prev = idx.iloc[-2]
            change = round((last["close"] - prev["close"]) / prev["close"] * 100, 2)
            summary[name] = {
                "close": round(float(last["close"]), 2),
                "change": change,
                "date": str(last["date"])[:10],
            }
        elif len(idx) == 1:
            last = idx.iloc[-1]
            summary[name] = {
                "close": round(float(last["close"]), 2),
                "change": 0,
                "date": str(last["date"])[:10],
            }

    # 전체 ETF 거래대금 합계 (최근일)
    latest_date = etf_prices["date"].max()
    total_tv = etf_prices[etf_prices["date"] == latest_date]["trading_value"].sum()
    summary["total_trading_value"] = int(total_tv)
    summary["latest_date"] = str(latest_date)[:10]

    return summary


def detect_hidden_opportunities(industry_stocks, is_scores, flow_score):
    """숨겨진 기회 종목 탐지"""
    print("Detecting Hidden Opportunities...")

    # IS Score 상위 5개 산업의 종목 중 주가 반응이 낮은 종목
    top_industries = is_scores.sort_values(ascending=False).head(5).index.tolist()

    candidates = []
    for ind in top_industries:
        stocks = industry_stocks.get(ind, [])
        for stock in stocks:
            # 조건: IS Score 상위 산업 + 주가 반응 낮음 + 비중 높음
            if stock["weight"] > 5 and -2 < stock["return_5d"] < 3:
                candidates.append({
                    **stock,
                    "industry": ind,
                    "is_score": round(float(is_scores[ind]), 1),
                    "signal": "Potential Hidden Opportunity",
                })

    # 상위 5개만
    candidates = sorted(candidates, key=lambda x: x["weight"], reverse=True)[:5]
    return candidates


def build_heatmap_data(flow_score, raw_etf_data, recent_tv, period_returns):
    """히트맵 데이터 구성 (기간별 수익률 포함)"""
    heatmap = []
    for ind in TARGET_INDUSTRIES:
        ret = raw_etf_data.loc[ind, "return_5d"] if ind in raw_etf_data.index else 0
        tv = recent_tv.get(ind, 0)
        entry = {
            "industry": ind,
            "return_5d": round(float(ret), 2),
            "trading_value_billion": round(float(tv), 0),
            "color": INDUSTRY_COLORS.get(ind, "#6B7280"),
        }
        for label in ["1w", "1m", "3m"]:
            entry[f"return_{label}"] = round(float(period_returns[label].get(ind, 0)), 2)
        heatmap.append(entry)
    return heatmap


def main():
    print("=" * 60)
    print("SFNI Dashboard Data Processing")
    print("=" * 60)

    # 1. 데이터 로드
    etf_master, etf_prices, etf_pdf, news, index_df, stock_prices, stocks_master = load_data()

    # 2. ETF Flow Score
    flow_score, raw_etf_data, recent_tv, period_returns, etf_prices_merged, etf_dates = compute_etf_flow_scores(etf_prices, etf_master)

    # 3. News Attention & Sentiment Score
    attention_score, sentiment_score, industry_news_stats, headlines = compute_news_scores(news)

    # 4. IS Score
    is_scores = compute_is_scores(flow_score, attention_score, sentiment_score)

    # 5. 대표 ETF
    rep_etfs = get_representative_etfs(etf_master, etf_prices)

    # 6. 산업별 구성종목
    industry_stocks = get_industry_stocks(etf_pdf, etf_master, stocks_master, stock_prices)

    # 7. 시장 요약
    market_summary = get_market_summary(index_df, etf_prices)

    # 8. 숨겨진 기회
    hidden_opps = detect_hidden_opportunities(industry_stocks, is_scores, flow_score)

    # 9. 히트맵 데이터
    heatmap_data = build_heatmap_data(flow_score, raw_etf_data, recent_tv, period_returns)

    # ── 최종 JSON 구성 ──
    print("\nBuilding JSON output...")

    # 산업 랭킹 (IS Score 기준 정렬)
    rankings = []
    for ind in is_scores.sort_values(ascending=False).index:
        rep = rep_etfs.get(ind, {"ticker": "-", "name": "-", "trading_value": 0})
        ns = industry_news_stats.get(ind, {})

        # IS Score 등급
        score_val = round(float(is_scores[ind]), 1)
        if score_val >= 85:
            grade = "강한 신호"
        elif score_val >= 70:
            grade = "양호한 신호"
        elif score_val >= 50:
            grade = "보통"
        else:
            grade = "약한 신호"

        rankings.append({
            "rank": len(rankings) + 1,
            "industry": ind,
            "is_score": score_val,
            "etf_flow_score": round(float(flow_score.get(ind, 0)), 1),
            "news_attention_score": round(float(attention_score.get(ind, 0)), 1),
            "sentiment_score": round(float(sentiment_score.get(ind, 0)), 1),
            "grade": grade,
            "representative_etf": rep,
            "color": INDUSTRY_COLORS.get(ind, "#6B7280"),
            "news_stats": ns,
            "trading_value_change": round(float(raw_etf_data.loc[ind, "trading_value_change"]) if ind in raw_etf_data.index else 0, 1),
            "return_5d": round(float(raw_etf_data.loc[ind, "return_5d"]) if ind in raw_etf_data.index else 0, 2),
        })

    # 전체 데이터
    dashboard_data = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "market_summary": market_summary,
        "rankings": rankings,
        "heatmap": heatmap_data,
        "headlines": headlines,
        "industry_stocks": industry_stocks,
        "hidden_opportunities": hidden_opps,
        "disclaimer": "이 대시보드는 데이터 기반 시장 인사이트를 제공하며, 금융 투자 자문에 해당하지 않습니다. 사용자는 최종 투자 판단을 본인의 책임과 판단에 따라 내려야 합니다.",
    }

    # JSON 저장
    output_path = os.path.join(OUT_DIR, "dashboard.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dashboard_data, f, ensure_ascii=False, indent=2)

    print(f"\nOutput saved to: {output_path}")
    print(f"Total industries: {len(rankings)}")
    print(f"Top 5 IS Score:")
    for r in rankings[:5]:
        print(f"  #{r['rank']} {r['industry']}: {r['is_score']} ({r['grade']})")
    print(f"Hidden opportunities: {len(hidden_opps)}")
    print("\nDone!")


if __name__ == "__main__":
    main()
