/**
 * SFNI Dashboard — Smart Flow & News Insight
 * 프론트엔드 메인 로직
 */

let DATA = null;
let selectedIndustry = null;
let selectedStockView = "list";
let heatmapSort = "return";
let selectedPeriod = "1w";

let customPeriod = null; // { from, to } for custom date range
const PERIOD_LABELS = { "1w": "1주", "1m": "1개월", "3m": "3개월", "1y": "1년", "custom": "지정 기간" };

// ── 유틸 ──
function fmt(n, d = 1) {
  if (n == null || isNaN(n)) return "0";
  return Number(n).toFixed(d);
}
function fmtSign(n, d = 1) {
  const v = Number(n);
  return (v >= 0 ? "+" : "") + v.toFixed(d);
}
function fmtBillion(n) {
  if (n >= 10000) return Math.round(n / 10000).toLocaleString() + "조";
  return Math.round(n).toLocaleString() + "억";
}

// ── 데이터 로드 ──
async function loadData() {
  try {
    const resp = await fetch("data/dashboard.json");
    DATA = await resp.json();
    render();
  } catch (e) {
    document.body.innerHTML = '<p style="color:red;padding:40px;">데이터 로드 실패: ' + e.message + '</p>';
  }
}

// ── 렌더링 ──
function render() {
  renderMarketInfo();
  renderHeatmap();
  renderRankings();
  renderTabs();
  renderHiddenOpportunities();
  renderDisclaimer();
  initStockSubTabs();
  initPeriodSelector();
  initHiddenSearch();

  // 기본 선택: IS Score 1위 산업
  if (DATA.rankings.length > 0) {
    selectIndustry(DATA.rankings[0].industry);
  }
}

// ── 시장 요약 ──
function renderMarketInfo() {
  const ms = DATA.market_summary;
  const el = document.getElementById("market-info");
  let html = "";
  for (const idx of ["KOSPI", "KOSDAQ"]) {
    if (ms[idx]) {
      const cls = ms[idx].change >= 0 ? "positive" : "negative";
      html += `<div class="market-item">
        <span class="market-label">${idx}</span>
        <span class="market-values"><span class="market-value ${cls}">${fmt(ms[idx].close, 2)}</span> <span class="${cls}">${fmtSign(ms[idx].change, 2)}%</span></span>
      </div>`;
    }
  }
  html += `<div class="market-item">
    <span class="market-label">기준일</span>
    <span class="market-value">${ms.latest_date || ""}</span>
  </div>`;
  el.innerHTML = html;
}

// ── Panel A: 히트맵 ──
function renderHeatmap() {
  const grid = document.getElementById("heatmap-grid");

  const customReturns = selectedPeriod === "custom" ? getCustomIndustryReturns() : null;
  const retKey = "return_" + selectedPeriod;

  function getHeatmapReturn(item) {
    if (customReturns) return customReturns[item.industry] || 0;
    return item[retKey] || item.return_5d;
  }

  let sorted;
  if (heatmapSort === "tv") {
    sorted = [...DATA.heatmap].sort((a, b) => b.trading_value_billion - a.trading_value_billion);
  } else {
    sorted = [...DATA.heatmap].sort((a, b) => getHeatmapReturn(b) - getHeatmapReturn(a));
  }
  grid.innerHTML = sorted.map(item => {
    const ret = getHeatmapReturn(item);
    const intensity = Math.min(Math.abs(ret) / 5, 1); // 5% = max intensity
    let bgColor;
    if (ret >= 0) {
      bgColor = `rgba(255, 77, 109, ${0.1 + intensity * 0.5})`;
    } else {
      bgColor = `rgba(77, 139, 255, ${0.1 + intensity * 0.5})`;
    }
    const textColor = ret >= 0 ? "#ff4d6d" : "#4d8bff";
    const tv = item.trading_value_billion;
    return `<div class="heatmap-card" style="background:${bgColor}" onclick="selectIndustry('${item.industry}')">
      <div class="hm-name">${item.industry}</div>
      <div class="hm-return" style="color:${textColor}">${fmtSign(ret)}%</div>
      <div class="hm-tv">${fmtBillion(tv)}</div>
    </div>`;
  }).join("");

  // 정렬 버튼 이벤트 (한 번만 바인딩)
  const sortGroup = document.querySelector(".heatmap-sort-group");
  if (sortGroup && !sortGroup.dataset.bound) {
    sortGroup.dataset.bound = "1";
    sortGroup.addEventListener("click", e => {
      const btn = e.target.closest(".heatmap-sort-btn");
      if (!btn) return;
      heatmapSort = btn.dataset.sort;
      sortGroup.querySelectorAll(".heatmap-sort-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      renderHeatmap();
    });
  }
}

// ── Panel B: IS Score 랭킹 ──
function renderRankings() {
  const list = document.getElementById("ranking-list");
  const isScoreKey = selectedPeriod !== "custom" && selectedPeriod !== "1w"
    ? "is_score_" + selectedPeriod : "is_score";

  // 기간별 IS Score로 재정렬
  const sorted = [...DATA.rankings].sort((a, b) => (b[isScoreKey] || b.is_score) - (a[isScoreKey] || a.is_score));
  const top5 = sorted.slice(0, 5);

  const industryIcons = {
    "반도체": "🔬", "2차전지": "🔋", "바이오/헬스": "🧬", "AI/소프트웨어": "🤖",
    "로봇/자율주행": "🦾", "게임/엔터": "🎮", "자동차/모빌리티": "🚗",
    "친환경/신재생": "🌱", "원자력": "⚛️", "방산/우주항공": "🚀",
    "철강/조선": "🏗️", "에너지/석유": "⛽", "화학/소재": "🧪",
    "통신/5G": "📡", "금융": "🏦", "리츠/부동산": "🏢",
    "건설/인프라": "🏛️", "음식료/식품": "🍚", "뷰티/화장품": "💄",
    "운송/물류": "🚛", "농업": "🌾",
  };

  // 기간별 수익률 조회
  const customReturns = selectedPeriod === "custom" ? getCustomIndustryReturns() : null;
  const retKey = "return_" + selectedPeriod;

  function getRankReturn(industry) {
    if (customReturns) return customReturns[industry] || 0;
    const hm = DATA.heatmap.find(h => h.industry === industry);
    if (hm && hm[retKey] != null) return hm[retKey];
    const r = DATA.rankings.find(r => r.industry === industry);
    return r ? r.return_5d : 0;
  }

  list.innerHTML = top5.map((r, i) => {
    const icon = industryIcons[r.industry] || "📊";
    const score = r[isScoreKey] || r.is_score;
    const barWidth = Math.max(score, 5);
    const ret = getRankReturn(r.industry);
    const retColor = ret >= 0 ? "#ff4d6d" : "#4d8bff";
    return `<div class="rank-row" onclick="selectIndustry('${r.industry}')">
      <div class="rank-num">${i + 1}</div>
      <div class="rank-icon" style="background:${r.color}22">${icon}</div>
      <div class="rank-info">
        <div class="rank-name">${r.industry} <span class="rank-return" style="color:${retColor}">${fmtSign(ret)}%</span></div>
        <div class="rank-bar-wrap">
          <div class="rank-bar" style="width:${barWidth}%;background:${r.color}" data-width="${barWidth}"></div>
        </div>
      </div>
      <div class="rank-score">${fmt(score, 0)}</div>
    </div>`;
  }).join("");

  // 바 애니메이션
  requestAnimationFrame(() => {
    document.querySelectorAll(".rank-bar").forEach(bar => {
      bar.style.width = bar.dataset.width + "%";
    });
  });
}

// ── 산업 탭 ──
function renderTabs() {
  const tabs = document.getElementById("industry-tabs");
  // 전체 산업 탭 (IS Score 순) + "전체" 탭
  const all = DATA.rankings;
  tabs.innerHTML =
    `<button class="tab-btn" data-industry="__all__">전체</button>` +
    all.map(r =>
      `<button class="tab-btn" data-industry="${r.industry}">${r.industry}</button>`
    ).join("");

  tabs.addEventListener("click", e => {
    if (e.target.classList.contains("tab-btn")) {
      const ind = e.target.dataset.industry;
      if (ind === "__all__") {
        selectAll();
      } else {
        selectIndustry(ind);
      }
    }
  });
}

function selectAll() {
  selectedIndustry = "__all__";

  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.industry === "__all__");
  });

  document.getElementById("panel-c-label").textContent = "전체";
  document.getElementById("panel-d-label").textContent = "전체";

  renderSentimentAll();
  renderStocksAll();
  renderHiddenOpportunities();
}

function selectIndustry(industry) {
  selectedIndustry = industry;

  // 탭 활성화
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.industry === industry);
  });

  // 라벨 업데이트
  document.getElementById("panel-c-label").textContent = industry;
  document.getElementById("panel-d-label").textContent = industry;

  renderSentiment(industry);
  renderStocks(industry);
  renderEtfFlow(industry);
  renderVolumeDaily(industry);
  renderVolumeWeekly(industry);
  renderHiddenOpportunities();
}

// ── Panel D: 서브 탭 전환 ──
function initStockSubTabs() {
  document.querySelector(".stock-sub-tabs").addEventListener("click", e => {
    const btn = e.target.closest(".stock-sub-tab");
    if (!btn) return;
    const view = btn.dataset.view;
    selectedStockView = view;

    document.querySelectorAll(".stock-sub-tab").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");

    document.getElementById("stock-view-list").style.display = view === "list" ? "" : "none";
    document.getElementById("stock-view-etf-flow").style.display = view === "etf-flow" ? "" : "none";
    document.getElementById("stock-view-daily").style.display = view === "daily" ? "" : "none";
    document.getElementById("stock-view-weekly").style.display = view === "weekly" ? "" : "none";
  });
}

// ── 커스텀 기간 수익률 계산 ──
function findClosestDate(dates, target) {
  // target 이상인 가장 가까운 날짜 반환
  for (let i = 0; i < dates.length; i++) {
    if (dates[i] >= target) return dates[i];
  }
  return dates[dates.length - 1];
}

function calcCustomReturn(closeSeries, fromDate, toDate) {
  if (!closeSeries) return 0;
  const dates = Object.keys(closeSeries).sort();
  const from = findClosestDate(dates, fromDate);
  // toDate 이하인 가장 가까운 날짜
  let to = dates[0];
  for (let i = dates.length - 1; i >= 0; i--) {
    if (dates[i] <= toDate) { to = dates[i]; break; }
  }
  const fromVal = closeSeries[from];
  const toVal = closeSeries[to];
  if (!fromVal || !toVal || fromVal === 0) return 0;
  return Math.round((toVal - fromVal) / fromVal * 1000) / 10;
}

function getCustomIndustryReturns() {
  if (!customPeriod || !DATA.industry_close_series) return {};
  const result = {};
  for (const ind of Object.keys(DATA.industry_close_series)) {
    result[ind] = calcCustomReturn(DATA.industry_close_series[ind], customPeriod.from, customPeriod.to);
  }
  return result;
}

function getCustomStockReturn(ticker) {
  if (!customPeriod || !DATA.stock_close_series || !DATA.stock_close_series[ticker]) return null;
  return calcCustomReturn(DATA.stock_close_series[ticker], customPeriod.from, customPeriod.to);
}

// ── 기간 선택 ──
// 현재 기간의 날짜 범위 반환 (뉴스 필터용 — 오늘까지 포함)
function getPeriodDateRange() {
  if (selectedPeriod === "custom" && customPeriod) {
    return { from: customPeriod.from, to: customPeriod.to };
  }
  // to는 오늘 날짜 (뉴스가 ETF 데이터보다 최신일 수 있음)
  const today = new Date().toISOString().slice(0, 10);
  const to = today;
  const periodDays = { "1w": 7, "1m": 30, "3m": 90, "1y": 365 };
  const days = periodDays[selectedPeriod] || 7;
  const fromDate = new Date(to);
  fromDate.setDate(fromDate.getDate() - days);
  const from = fromDate.toISOString().slice(0, 10);
  return { from, to };
}

function applyPeriodChange() {
  renderHeatmap();
  renderRankings();
  if (selectedIndustry === "__all__") {
    renderSentimentAll();
    renderStocksAll();
  } else if (selectedIndustry) {
    renderSentiment(selectedIndustry);
    renderStocks(selectedIndustry);
  }
  renderHiddenOpportunities();
}

function initPeriodSelector() {
  const selector = document.getElementById("period-selector");
  const fromInput = document.getElementById("period-from");
  const toInput = document.getElementById("period-to");

  // 날짜 입력 범위 제한
  if (DATA.available_dates && DATA.available_dates.length > 0) {
    const minDate = DATA.available_dates[0];
    const maxDate = DATA.available_dates[DATA.available_dates.length - 1];
    fromInput.min = minDate;
    fromInput.max = maxDate;
    toInput.min = minDate;
    toInput.max = maxDate;
    toInput.value = maxDate;
  }

  // 프리셋 버튼 클릭
  selector.addEventListener("click", e => {
    const btn = e.target.closest(".period-btn:not(#period-apply)");
    if (!btn) return;
    selectedPeriod = btn.dataset.period;
    customPeriod = null;
    selector.querySelectorAll(".period-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    applyPeriodChange();
  });

  // 직접 지정 조회
  document.getElementById("period-apply").addEventListener("click", () => {
    const from = fromInput.value;
    const to = toInput.value;
    if (!from || !to) return;
    if (from > to) { fromInput.value = to; toInput.value = from; }
    customPeriod = { from: fromInput.value, to: toInput.value };
    selectedPeriod = "custom";
    selector.querySelectorAll(".period-btn").forEach(b => b.classList.remove("active"));
    document.getElementById("period-apply").classList.add("active");
    applyPeriodChange();
  });
}

// ── Panel C: 감성 분석 ──
function renderSentiment(industry) {
  const ranking = DATA.rankings.find(r => r.industry === industry);
  if (!ranking) return;

  // 기간 필터링
  const range = getPeriodDateRange();
  const allNews = (DATA.all_news && DATA.all_news[industry]) || [];
  let filtered;
  if (range && allNews.length > 0) {
    filtered = allNews.filter(n => n.date >= range.from && n.date <= range.to);
  } else {
    filtered = allNews.length > 0 ? allNews : (DATA.headlines[industry] || []);
  }

  // 기간별 감성 통계 계산
  const total = filtered.length;
  const pos = filtered.filter(n => n.sentiment === "긍정").length;
  const neg = filtered.filter(n => n.sentiment === "부정").length;
  const neu = total - pos - neg;
  const posRatio = total > 0 ? round1(pos / total * 100) : 0;
  const negRatio = total > 0 ? round1(neg / total * 100) : 0;
  const neuRatio = total > 0 ? round1(neu / total * 100) : 0;

  // 게이지 그리기
  drawGauge(posRatio);

  // 감성 카드
  const cards = document.getElementById("sentiment-cards");
  cards.innerHTML = `
    <div class="sent-card negative">
      <div class="sent-value">${fmt(negRatio)}%</div>
      <div class="sent-label">부정 (${neg}건)</div>
    </div>
    <div class="sent-card neutral">
      <div class="sent-value">${fmt(neuRatio)}%</div>
      <div class="sent-label">중립 (${neu}건)</div>
    </div>
    <div class="sent-card positive">
      <div class="sent-value">${fmt(posRatio)}%</div>
      <div class="sent-label">긍정 (${pos}건)</div>
    </div>
  `;

  // 헤드라인 (기간 내 최신 5개)
  const hlist = document.getElementById("headlines-list");
  hlist.innerHTML = filtered.slice(0, 5).map(h => {
    let badgeCls = "neutral";
    let badgeText = "중립";
    if (h.sentiment === "긍정") { badgeCls = "positive"; badgeText = "긍정"; }
    if (h.sentiment === "부정") { badgeCls = "negative"; badgeText = "부정"; }
    const link = h.link || "#";
    return `<div class="headline-row">
      <span class="sent-badge ${badgeCls}">${badgeText}</span>
      <a href="${link}" target="_blank" rel="noopener">${escapeHtml(h.title)}</a>
    </div>`;
  }).join("");
}

function round1(n) { return Math.round(n * 10) / 10; }

// ── Panel C: 전체 산업 감성 분석 ──
function renderSentimentAll() {
  const range = getPeriodDateRange();
  let allFiltered = [];
  for (const ind of Object.keys(DATA.all_news || {})) {
    const news = DATA.all_news[ind] || [];
    if (range) {
      allFiltered = allFiltered.concat(news.filter(n => n.date >= range.from && n.date <= range.to));
    } else {
      allFiltered = allFiltered.concat(news);
    }
  }

  const total = allFiltered.length;
  const pos = allFiltered.filter(n => n.sentiment === "긍정").length;
  const neg = allFiltered.filter(n => n.sentiment === "부정").length;
  const neu = total - pos - neg;
  const posRatio = total > 0 ? round1(pos / total * 100) : 0;
  const negRatio = total > 0 ? round1(neg / total * 100) : 0;
  const neuRatio = total > 0 ? round1(neu / total * 100) : 0;

  drawGauge(posRatio);

  const cards = document.getElementById("sentiment-cards");
  cards.innerHTML = `
    <div class="sent-card negative">
      <div class="sent-value">${fmt(negRatio)}%</div>
      <div class="sent-label">부정 (${neg}건)</div>
    </div>
    <div class="sent-card neutral">
      <div class="sent-value">${fmt(neuRatio)}%</div>
      <div class="sent-label">중립 (${neu}건)</div>
    </div>
    <div class="sent-card positive">
      <div class="sent-value">${fmt(posRatio)}%</div>
      <div class="sent-label">긍정 (${pos}건)</div>
    </div>
  `;

  // 전체 헤드라인 최신 5개
  allFiltered.sort((a, b) => b.date.localeCompare(a.date));
  const hlist = document.getElementById("headlines-list");
  hlist.innerHTML = allFiltered.slice(0, 5).map(h => {
    let badgeCls = "neutral", badgeText = "중립";
    if (h.sentiment === "긍정") { badgeCls = "positive"; badgeText = "긍정"; }
    if (h.sentiment === "부정") { badgeCls = "negative"; badgeText = "부정"; }
    return `<div class="headline-row">
      <span class="sent-badge ${badgeCls}">${badgeText}</span>
      <a href="${h.link || '#'}" target="_blank" rel="noopener">${escapeHtml(h.title)}</a>
    </div>`;
  }).join("");
}

// ── Panel D: 전체 산업 종목 (비중 TOP) ──
function renderStocksAll() {
  const list = document.getElementById("stock-list");
  const retKey = "return_" + selectedPeriod;
  const periodLabel = PERIOD_LABELS[selectedPeriod] || "1주";
  const isCustom = selectedPeriod === "custom";

  // 모든 산업의 종목을 합쳐서 비중 순 정렬
  let allStocks = [];
  for (const ind of Object.keys(DATA.industry_stocks)) {
    for (const s of DATA.industry_stocks[ind]) {
      allStocks.push({ ...s, industry: ind });
    }
  }
  // 중복 제거 (같은 티커는 비중 높은 것만)
  const seen = new Map();
  for (const s of allStocks) {
    if (!seen.has(s.ticker) || seen.get(s.ticker).weight < s.weight) {
      seen.set(s.ticker, s);
    }
  }
  allStocks = [...seen.values()].sort((a, b) => b.weight - a.weight).slice(0, 20);

  let headerLabel = isCustom && customPeriod
    ? customPeriod.from.slice(5) + "~" + customPeriod.to.slice(5)
    : periodLabel;

  list.innerHTML = `<div class="stock-row stock-header">
      <div class="stock-ticker">코드</div>
      <div class="stock-name-wrap"><span class="stock-name">종목명</span></div>
      <div class="stock-weight">ETF 비중</div>
      <div class="mini-bars">산업</div>
      <div class="stock-return">${headerLabel} 수익률</div>
    </div>` + allStocks.map(s => {
    let ret;
    if (isCustom) {
      const cr = getCustomStockReturn(s.ticker);
      ret = cr != null ? cr : s.return_5d;
    } else {
      ret = s[retKey] != null ? s[retKey] : s.return_5d;
    }
    const retColor = ret >= 0 ? "var(--red)" : "var(--blue)";
    return `<div class="stock-row">
      <div class="stock-ticker">${s.ticker}</div>
      <div class="stock-name-wrap"><span class="stock-name">${escapeHtml(s.name)}</span></div>
      <div class="stock-weight">${fmt(s.weight)}%</div>
      <div class="mini-bars" style="font-size:10px;color:var(--text-dim)">${s.industry}</div>
      <div class="stock-return" style="color:${retColor}">${fmtSign(ret)}%</div>
    </div>`;
  }).join("");

  // 검색 필터 초기화
  const input = document.getElementById("stock-search-input");
  input.value = "";
  input.oninput = () => {
    const q = input.value.trim().toLowerCase();
    const filtered = allStocks.filter(s => s.name.toLowerCase().includes(q) || s.ticker.includes(q));
    // 간단히 재렌더
    const rows = list.querySelectorAll(".stock-row:not(.stock-header)");
    rows.forEach((row, i) => {
      if (i < allStocks.length) {
        const s = allStocks[i];
        row.style.display = (!q || s.name.toLowerCase().includes(q) || s.ticker.includes(q)) ? "" : "none";
      }
    });
  };
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text || "";
  return div.innerHTML;
}

function drawGauge(posRatio) {
  const svg = document.getElementById("sentiment-gauge");
  const angle = (posRatio / 100) * 180; // 0~180도
  const cx = 150, cy = 150, r = 120;

  // arc path 생성
  function arcPath(startDeg, endDeg, radius) {
    const s = (startDeg - 180) * Math.PI / 180;
    const e = (endDeg - 180) * Math.PI / 180;
    const x1 = cx + radius * Math.cos(s);
    const y1 = cy + radius * Math.sin(s);
    const x2 = cx + radius * Math.cos(e);
    const y2 = cy + radius * Math.sin(e);
    const large = endDeg - startDeg > 180 ? 1 : 0;
    return `M ${x1} ${y1} A ${radius} ${radius} 0 ${large} 1 ${x2} ${y2}`;
  }

  // 바늘 위치
  const needleAngle = (angle - 180) * Math.PI / 180;
  const nx = cx + (r - 15) * Math.cos(needleAngle);
  const ny = cy + (r - 15) * Math.sin(needleAngle);

  svg.innerHTML = `
    <!-- 배경 아크 -->
    <defs>
      <linearGradient id="gaugeGrad" x1="0%" y1="0%" x2="100%" y2="0%">
        <stop offset="0%" stop-color="#ff4d6d"/>
        <stop offset="50%" stop-color="#888"/>
        <stop offset="100%" stop-color="#00c896"/>
      </linearGradient>
    </defs>
    <path d="${arcPath(0, 180, r)}" fill="none" stroke="#333" stroke-width="20" stroke-linecap="round"/>
    <path d="${arcPath(0, 180, r)}" fill="none" stroke="url(#gaugeGrad)" stroke-width="16" stroke-linecap="round" opacity="0.4"/>
    <path d="${arcPath(0, angle, r)}" fill="none" stroke="url(#gaugeGrad)" stroke-width="16" stroke-linecap="round"/>

    <!-- 바늘 -->
    <line x1="${cx}" y1="${cy}" x2="${nx}" y2="${ny}" stroke="#fff" stroke-width="2.5" stroke-linecap="round"/>
    <circle cx="${cx}" cy="${cy}" r="6" fill="#fff"/>

    <!-- 중앙 텍스트 -->
    <text x="${cx}" y="${cy - 20}" text-anchor="middle" fill="#fff" font-size="32" font-weight="700" font-family="inherit">${fmt(posRatio, 0)}%</text>
    <text x="${cx}" y="${cy - 2}" text-anchor="middle" fill="#888" font-size="12" font-family="inherit">긍정 비율</text>

    <!-- 라벨 -->
    <text x="20" y="${cy + 18}" fill="#ff4d6d" font-size="11" font-family="inherit">← 부정</text>
    <text x="230" y="${cy + 18}" fill="#00c896" font-size="11" font-family="inherit">긍정 →</text>
  `;
}

// ── Panel D: 종목 탐색 ──
function renderStocks(industry) {
  const stocks = DATA.industry_stocks[industry] || [];
  const hiddenTickers = new Set((DATA.hidden_opportunities || []).map(h => h.ticker));
  const list = document.getElementById("stock-list");

  function renderList(items) {
    if (items.length === 0) {
      list.innerHTML = '<div style="color:var(--text-dim);text-align:center;padding:30px;">해당 산업의 구성종목 데이터가 없습니다.</div>';
      return;
    }

    const retKey = "return_" + selectedPeriod;
    let periodLabel = PERIOD_LABELS[selectedPeriod] || "1주";
    if (selectedPeriod === "custom" && customPeriod) {
      periodLabel = customPeriod.from.slice(5) + "~" + customPeriod.to.slice(5);
    }

    list.innerHTML = `<div class="stock-row stock-header">
        <div class="stock-ticker">코드</div>
        <div class="stock-name-wrap"><span class="stock-name">종목명</span></div>
        <div class="stock-weight">ETF 비중</div>
        <div class="mini-bars">거래량</div>
        <div class="stock-return">${periodLabel} 수익률</div>
      </div>` + items.map(s => {
      let ret;
      if (selectedPeriod === "custom") {
        const cr = getCustomStockReturn(s.ticker);
        ret = cr != null ? cr : s.return_5d;
      } else {
        ret = s[retKey] != null ? s[retKey] : s.return_5d;
      }
      const retColor = ret >= 0 ? "var(--red)" : "var(--blue)";
      const badges = [];
      if (hiddenTickers.has(s.ticker)) badges.push('<span class="hidden-badge">유망주</span>');
      if (s.is_accumulating) badges.push('<span class="acc-badge">매집</span>');
      const badge = badges.join("");

      // 미니바 차트
      const vols = s.recent_volumes || [];
      const maxVol = Math.max(...vols, 1);
      const barsHtml = vols.map(v => {
        const h = Math.max((v / maxVol) * 24, 3);
        return `<div class="mini-bar" style="height:${h}px;background:${retColor}"></div>`;
      }).join("");

      return `<div class="stock-row">
        <div class="stock-ticker">${s.ticker}</div>
        <div class="stock-name-wrap">
          <span class="stock-name">${escapeHtml(s.name)}</span>
          ${badge}
        </div>
        <div class="stock-weight">${fmt(s.weight)}%</div>
        <div class="mini-bars">${barsHtml}</div>
        <div class="stock-return" style="color:${retColor}">${fmtSign(ret)}%</div>
      </div>`;
    }).join("");
  }

  renderList(stocks);

  // 검색 필터
  const input = document.getElementById("stock-search-input");
  input.value = "";
  input.oninput = () => {
    const q = input.value.trim().toLowerCase();
    if (!q) {
      renderList(stocks);
      return;
    }
    const filtered = stocks.filter(s =>
      s.name.toLowerCase().includes(q) || s.ticker.includes(q)
    );
    renderList(filtered);
  };
}

// ── Panel D: ETF 매집 신호 ──
function renderEtfFlow(industry) {
  const stocks = DATA.industry_stocks[industry] || [];
  const container = document.getElementById("etf-flow-table");

  if (stocks.length === 0) {
    container.innerHTML = '<div style="color:var(--text-dim);text-align:center;padding:30px;">데이터가 없습니다.</div>';
    return;
  }

  // 종목별 카드 형태
  let html = '<div class="etf-flow-list">';
  stocks.forEach(s => {
    const wChg1w = s.weight_change_1w || 0;
    const wChg2w = s.weight_change_2w || 0;
    const etfChg = s.etf_count_change || 0;
    const isAcc = s.is_accumulating;

    const chg1wColor = wChg1w > 0 ? "var(--red)" : wChg1w < 0 ? "var(--blue)" : "var(--text-dim)";
    const chg2wColor = wChg2w > 0 ? "var(--red)" : wChg2w < 0 ? "var(--blue)" : "var(--text-dim)";
    const etfChgColor = etfChg > 0 ? "var(--red)" : etfChg < 0 ? "var(--blue)" : "var(--text-dim)";
    const badge = isAcc ? '<span class="acc-badge">매집 중</span>' : '';

    // 미니 비중 추이 차트
    const flow = s.etf_flow || [];
    let sparkHtml = "";
    if (flow.length >= 2) {
      const weights = flow.map(f => f.weight);
      const minW = Math.min(...weights);
      const maxW = Math.max(...weights);
      const range = maxW - minW || 1;
      const w = 120, h = 32;
      const points = weights.map((v, i) => {
        const x = (i / (weights.length - 1)) * w;
        const y = h - ((v - minW) / range) * (h - 4) - 2;
        return `${x},${y}`;
      }).join(" ");
      const lineColor = weights[weights.length - 1] >= weights[0] ? "var(--red)" : "var(--blue)";
      sparkHtml = `<svg width="${w}" height="${h}" class="etf-spark"><polyline points="${points}" fill="none" stroke="${lineColor}" stroke-width="1.5"/></svg>`;
    }

    html += `<div class="etf-flow-card${isAcc ? ' accumulating' : ''}">
      <div class="efc-top">
        <div>
          <span class="efc-ticker">${s.ticker}</span>
          <span class="efc-name">${escapeHtml(s.name)}</span>
          ${badge}
        </div>
        ${sparkHtml}
      </div>
      <div class="efc-stats">
        <div class="efc-stat">
          <div class="efc-stat-label">현재 비중</div>
          <div class="efc-stat-value">${fmt(s.weight_now || s.weight)}%</div>
        </div>
        <div class="efc-stat">
          <div class="efc-stat-label">1주 변화</div>
          <div class="efc-stat-value" style="color:${chg1wColor}">${wChg1w > 0 ? '▲' : wChg1w < 0 ? '▼' : ''}${Math.abs(wChg1w).toFixed(1)}%p</div>
        </div>
        <div class="efc-stat">
          <div class="efc-stat-label">2주 변화</div>
          <div class="efc-stat-value" style="color:${chg2wColor}">${wChg2w > 0 ? '▲' : wChg2w < 0 ? '▼' : ''}${Math.abs(wChg2w).toFixed(1)}%p</div>
        </div>
        <div class="efc-stat">
          <div class="efc-stat-label">편입 ETF</div>
          <div class="efc-stat-value">${s.etf_count_now || 0}개 <span style="color:${etfChgColor};font-size:11px">(${etfChg > 0 ? '+' : ''}${etfChg})</span></div>
        </div>
      </div>
    </div>`;
  });
  html += '</div>';
  container.innerHTML = html;
}

// ── Panel D: 일별 수량 증감 ──
function renderVolumeDaily(industry) {
  const stocks = DATA.industry_stocks[industry] || [];
  const container = document.getElementById("volume-daily-table");

  if (stocks.length === 0 || !stocks[0].volume_daily || stocks[0].volume_daily.length === 0) {
    container.innerHTML = '<div style="color:var(--text-dim);text-align:center;padding:30px;">일별 수량 데이터가 없습니다.</div>';
    return;
  }

  // 날짜 컬럼 추출 (첫 종목 기준)
  const dates = stocks[0].volume_daily.map(d => d.date.slice(5)); // MM-DD

  let html = `<table class="volume-table">
    <thead><tr>
      <th class="vol-th-name">종목</th>
      ${dates.map(d => `<th>${d}</th>`).join("")}
    </tr></thead><tbody>`;

  stocks.forEach(s => {
    const daily = s.volume_daily || [];
    html += `<tr>
      <td class="vol-td-name"><span class="vol-ticker">${s.ticker}</span> ${escapeHtml(s.name)}</td>
      ${daily.map(d => {
        const color = d.change_pct > 0 ? "var(--red)" : d.change_pct < 0 ? "var(--blue)" : "var(--text-dim)";
        const arrow = d.change_pct > 0 ? "▲" : d.change_pct < 0 ? "▼" : "";
        return `<td>
          <div class="vol-cell-num">${(d.volume / 1000).toFixed(0)}K</div>
          <div class="vol-cell-chg" style="color:${color}">${arrow}${Math.abs(d.change_pct)}%</div>
        </td>`;
      }).join("")}
    </tr>`;
  });

  html += "</tbody></table>";
  container.innerHTML = html;
}

// ── Panel D: 주별 수량 증감 ──
function renderVolumeWeekly(industry) {
  const stocks = DATA.industry_stocks[industry] || [];
  const container = document.getElementById("volume-weekly-table");

  if (stocks.length === 0 || !stocks[0].volume_weekly || stocks[0].volume_weekly.length === 0) {
    container.innerHTML = '<div style="color:var(--text-dim);text-align:center;padding:30px;">주별 수량 데이터가 없습니다.</div>';
    return;
  }

  const weeks = stocks[0].volume_weekly.map(w => w.week_label);

  let html = `<table class="volume-table">
    <thead><tr>
      <th class="vol-th-name">종목</th>
      ${weeks.map(w => `<th>${w}</th>`).join("")}
    </tr></thead><tbody>`;

  stocks.forEach(s => {
    const weekly = s.volume_weekly || [];
    html += `<tr>
      <td class="vol-td-name"><span class="vol-ticker">${s.ticker}</span> ${escapeHtml(s.name)}</td>
      ${weekly.map((w, i) => {
        const color = w.change_pct > 0 ? "var(--red)" : w.change_pct < 0 ? "var(--blue)" : "var(--text-dim)";
        const arrow = w.change_pct > 0 ? "▲" : w.change_pct < 0 ? "▼" : "";
        const chgText = i === 0 ? "-" : `${arrow}${Math.abs(w.change_pct)}%`;
        const chgColor = i === 0 ? "var(--text-dim)" : color;
        return `<td>
          <div class="vol-cell-num">${(w.avg_volume / 1000).toFixed(0)}K</div>
          <div class="vol-cell-chg" style="color:${chgColor}">${chgText}</div>
        </td>`;
      }).join("")}
    </tr>`;
  });

  html += "</tbody></table>";
  container.innerHTML = html;
}

// ── Hidden Opportunities ──
function renderHiddenOpportunities(searchQuery) {
  const section = document.getElementById("hidden-section");
  const isScoreKey = selectedPeriod !== "custom" && selectedPeriod !== "1w"
    ? "is_score_" + selectedPeriod : "is_score";
  const retKey = "return_" + selectedPeriod;
  const isCustom = selectedPeriod === "custom";
  const periodLabel = PERIOD_LABELS[selectedPeriod] || "1주";

  // 각 종목의 기간별 수익률 계산
  function getStockReturn(stock) {
    if (isCustom) {
      const cr = getCustomStockReturn(stock.ticker);
      return cr != null ? cr : stock.return_5d;
    }
    return stock[retKey] != null ? stock[retKey] : stock.return_5d;
  }

  function getIsScore(industry) {
    const r = DATA.rankings.find(r => r.industry === industry);
    return r ? (r[isScoreKey] || r.is_score) : 0;
  }

  const q = (searchQuery || "").trim().toLowerCase();
  let opps;

  // 탐색 대상 산업 결정
  let targetIndustries;
  if (selectedIndustry && selectedIndustry !== "__all__") {
    // 특정 산업 선택 → 해당 산업만
    targetIndustries = [selectedIndustry];
  } else {
    // 전체 또는 미선택 → IS Score TOP 5
    const sortedRankings = [...DATA.rankings].sort((a, b) => (b[isScoreKey] || b.is_score) - (a[isScoreKey] || a.is_score));
    targetIndustries = sortedRankings.slice(0, 5).map(r => r.industry);
  }

  if (q) {
    // 검색 모드: 대상 산업 내에서 종목 검색
    const candidates = [];
    const seenTickers = new Set();
    const searchScope = q.length >= 2 ? Object.keys(DATA.industry_stocks) : targetIndustries;
    for (const ind of searchScope) {
      const stocks = DATA.industry_stocks[ind] || [];
      for (const s of stocks) {
        if (seenTickers.has(s.ticker)) continue;
        if (!s.name.toLowerCase().includes(q) && !s.ticker.includes(q)) continue;
        seenTickers.add(s.ticker);
        const ret = getStockReturn(s);
        candidates.push({
          ...s,
          industry: ind,
          period_return: ret,
          is_score: getIsScore(ind),
        });
      }
    }
    candidates.sort((a, b) => b.weight - a.weight);
    opps = candidates.slice(0, 10);
  } else {
    // 기본 모드: 대상 산업에서 저반응 종목 탐지
    const candidates = [];
    const seenTickers = new Set();
    for (const ind of targetIndustries) {
      const stocks = DATA.industry_stocks[ind] || [];
      for (const s of stocks) {
        if (seenTickers.has(s.ticker)) continue;
        const ret = getStockReturn(s);
        if (s.weight > 5 && ret > -5 && ret < 5) {
          seenTickers.add(s.ticker);
          candidates.push({
            ...s,
            industry: ind,
            period_return: ret,
            is_score: getIsScore(ind),
          });
        }
      }
    }
    candidates.sort((a, b) => b.weight - a.weight);
    opps = candidates.slice(0, 5);
  }

  section.style.display = "block";
  if (opps.length === 0) {
    document.getElementById("hidden-list").innerHTML = q
      ? '<div style="color:var(--text-dim);text-align:center;padding:20px;">검색 결과가 없습니다.</div>'
      : '<div style="color:var(--text-dim);text-align:center;padding:20px;">해당 기간에 조건에 맞는 종목이 없습니다.</div>';
    return;
  }

  const label = isCustom && customPeriod
    ? customPeriod.from.slice(5) + "~" + customPeriod.to.slice(5)
    : periodLabel;

  // 산업별 뉴스 감성 계산 (기간 내)
  const range = getPeriodDateRange();
  function getIndustrySentiment(industry) {
    const news = (DATA.all_news && DATA.all_news[industry]) || [];
    const filtered = range ? news.filter(n => n.date >= range.from && n.date <= range.to) : news;
    const total = filtered.length;
    if (total === 0) return { posRatio: 0, negRatio: 0, total: 0, label: "-" };
    const pos = filtered.filter(n => n.sentiment === "긍정").length;
    const neg = filtered.filter(n => n.sentiment === "부정").length;
    const posRatio = round1(pos / total * 100);
    const negRatio = round1(neg / total * 100);
    let sentLabel = "중립";
    if (posRatio > 30) sentLabel = "긍정";
    else if (negRatio > 20) sentLabel = "부정";
    return { posRatio, negRatio, total, label: sentLabel };
  }

  const list = document.getElementById("hidden-list");
  list.innerHTML = opps.map(o => {
    const ret = o.period_return;
    const retColor = ret >= 0 ? "var(--red)" : "var(--blue)";
    const sent = getIndustrySentiment(o.industry);
    const sentColor = sent.label === "긍정" ? "var(--green, #10b981)" : sent.label === "부정" ? "var(--red)" : "var(--text-dim)";
    return `<div class="hidden-card" onclick="selectIndustry('${o.industry}')" style="cursor:pointer">
      <div class="hc-header">
        <div>
          <div class="hc-name">${escapeHtml(o.name)}</div>
          <div class="hc-ticker">${o.ticker}</div>
        </div>
        <div class="hc-industry">${o.industry}</div>
      </div>
      <div class="hc-detail">
        ETF 비중 합계: <span>${fmt(o.weight)}%</span><br>
        ${label} 수익률: <span style="color:${retColor}">${fmtSign(ret)}%</span><br>
        IS Score: <span>${fmt(o.is_score, 0)}</span>
      </div>
      <div class="hc-sentiment">
        <span class="hc-sent-badge" style="color:${sentColor}">뉴스 감성: ${sent.label}</span>
        <span class="hc-sent-detail">긍정 ${sent.posRatio}% · 부정 ${sent.negRatio}% (${sent.total}건)</span>
      </div>
    </div>`;
  }).join("");
}

function initHiddenSearch() {
  const input = document.getElementById("hidden-search-input");
  if (!input) return;
  input.oninput = () => {
    renderHiddenOpportunities(input.value);
  };
}

// ── Disclaimer ──
function renderDisclaimer() {
  document.getElementById("disclaimer").textContent = DATA.disclaimer;
}

// ══════════════════════════════════════════
// 데이터 업데이트 모달
// ══════════════════════════════════════════

let pollTimer = null;

function openUpdateModal() {
  const overlay = document.getElementById("modal-overlay");
  overlay.classList.add("show");

  // 설정 화면 표시
  document.getElementById("modal-settings").style.display = "";
  document.getElementById("modal-progress").style.display = "none";
  document.getElementById("modal-done").style.display = "none";
}

function closeUpdateModal() {
  document.getElementById("modal-overlay").classList.remove("show");
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
}

function startUpdate() {
  const options = {
    days: parseInt(document.getElementById("opt-days").value) || 1,
    skip_pdf: document.getElementById("opt-skip-pdf").checked,
  };

  // 진행 화면으로 전환
  document.getElementById("modal-settings").style.display = "none";
  document.getElementById("modal-progress").style.display = "";
  document.getElementById("progress-log").innerHTML = "";
  document.getElementById("progress-message").textContent = "서버에 요청 중...";

  // 업데이트 버튼 상태
  document.getElementById("update-btn").classList.add("running");

  // API 호출 (API 키 불필요)
  fetch("/api/update", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ options }),
  })
  .then(r => r.json())
  .then(res => {
    if (res.status === "busy") {
      document.getElementById("progress-message").textContent = res.message;
    } else {
      // 폴링 시작
      startPolling();
    }
  })
  .catch(err => {
    showDone(false, "서버 연결 실패: " + err.message + "\n\npy server.py 로 서버를 실행했는지 확인하세요.");
  });
}

function startPolling() {
  let lastLogCount = 0;
  pollTimer = setInterval(() => {
    fetch("/api/status")
      .then(r => r.json())
      .then(status => {
        document.getElementById("progress-message").textContent = status.message || "처리 중...";

        // 로그 업데이트 (새로운 항목만 추가)
        const log = document.getElementById("progress-log");
        const progress = status.progress || [];
        for (let i = lastLogCount; i < progress.length; i++) {
          const line = document.createElement("div");
          const text = progress[i];
          if (text.includes("오류") || text.includes("실패")) {
            line.className = "log-err";
          } else if (text.includes("완료") || text.includes("성공")) {
            line.className = "log-ok";
          }
          line.textContent = text;
          log.appendChild(line);
          log.scrollTop = log.scrollHeight;
        }
        lastLogCount = progress.length;

        // 완료 체크
        if (!status.running) {
          clearInterval(pollTimer);
          pollTimer = null;
          const success = !status.message.includes("오류");
          showDone(success, status.message);
        }
      })
      .catch(() => {});
  }, 1500);
}

function showDone(success, message) {
  document.getElementById("modal-progress").style.display = "none";
  document.getElementById("modal-done").style.display = "";

  const icon = document.getElementById("done-icon");
  icon.textContent = success ? "\u2713" : "\u2717";
  icon.className = "done-icon " + (success ? "success" : "error");

  document.getElementById("done-message").textContent = message;
  document.getElementById("update-btn").classList.remove("running");
}

function finishUpdate() {
  closeUpdateModal();
  // 대시보드 데이터 새로고침
  loadData();
}

// ESC 키로 모달 닫기
document.addEventListener("keydown", e => {
  if (e.key === "Escape") closeUpdateModal();
});

// ── 시작 ──
document.addEventListener("DOMContentLoaded", () => {
  loadData();

  // Vercel 배포 환경에서는 업데이트 버튼 숨기기 (로컬 서버 전용 기능)
  const isLocal = location.hostname === "localhost" || location.hostname === "127.0.0.1";
  if (!isLocal) {
    const btn = document.getElementById("update-btn");
    if (btn) btn.style.display = "none";
  }
});
