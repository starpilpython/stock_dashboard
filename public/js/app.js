/**
 * SFNI Dashboard — Smart Flow & News Insight
 * 프론트엔드 메인 로직
 */

let DATA = null;
let selectedIndustry = null;
let selectedStockView = "list";

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
        <span class="market-value ${cls}">${fmt(ms[idx].close, 2)}</span>
        <span class="${cls}">${fmtSign(ms[idx].change, 2)}%</span>
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
  // 수익률 절대값 기준으로 상위 9개
  const sorted = [...DATA.heatmap].sort((a, b) => Math.abs(b.return_5d) - Math.abs(a.return_5d));
  const top9 = sorted.slice(0, 9);

  grid.innerHTML = top9.map(item => {
    const ret = item.return_5d;
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
}

// ── Panel B: IS Score 랭킹 ──
function renderRankings() {
  const list = document.getElementById("ranking-list");
  const top5 = DATA.rankings.slice(0, 5);

  const industryIcons = {
    "반도체": "🔬", "2차전지": "🔋", "바이오/헬스": "🧬", "AI/소프트웨어": "🤖",
    "로봇/자율주행": "🦾", "게임/엔터": "🎮", "자동차/모빌리티": "🚗",
    "친환경/신재생": "🌱", "원자력": "⚛️", "방산/우주항공": "🚀",
    "철강/조선": "🏗️", "에너지/석유": "⛽", "화학/소재": "🧪",
    "통신/5G": "📡", "금융": "🏦", "리츠/부동산": "🏢",
    "건설/인프라": "🏛️", "음식료/식품": "🍚", "뷰티/화장품": "💄",
    "운송/물류": "🚛", "농업": "🌾",
  };

  list.innerHTML = top5.map(r => {
    const icon = industryIcons[r.industry] || "📊";
    const barWidth = Math.max(r.is_score, 5);
    return `<div class="rank-row" onclick="selectIndustry('${r.industry}')">
      <div class="rank-num">${r.rank}</div>
      <div class="rank-icon" style="background:${r.color}22">${icon}</div>
      <div class="rank-info">
        <div class="rank-name">${r.industry}</div>
        <div class="rank-bar-wrap">
          <div class="rank-bar" style="width:${barWidth}%;background:${r.color}" data-width="${barWidth}"></div>
        </div>
      </div>
      <div class="rank-score">${fmt(r.is_score, 0)}</div>
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
  const top = DATA.rankings.slice(0, 10);
  tabs.innerHTML = top.map(r =>
    `<button class="tab-btn" data-industry="${r.industry}">${r.industry}</button>`
  ).join("");

  tabs.addEventListener("click", e => {
    if (e.target.classList.contains("tab-btn")) {
      selectIndustry(e.target.dataset.industry);
    }
  });
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
  renderVolumeDaily(industry);
  renderVolumeWeekly(industry);
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
    document.getElementById("stock-view-daily").style.display = view === "daily" ? "" : "none";
    document.getElementById("stock-view-weekly").style.display = view === "weekly" ? "" : "none";
  });
}

// ── Panel C: 감성 분석 ──
function renderSentiment(industry) {
  const ranking = DATA.rankings.find(r => r.industry === industry);
  if (!ranking) return;
  const stats = ranking.news_stats;
  const headlines = DATA.headlines[industry] || [];

  // 게이지 그리기
  drawGauge(stats.pos_ratio || 0);

  // 감성 카드
  const cards = document.getElementById("sentiment-cards");
  cards.innerHTML = `
    <div class="sent-card negative">
      <div class="sent-value">${fmt(stats.neg_ratio)}%</div>
      <div class="sent-label">부정 (${stats.negative || 0}건)</div>
    </div>
    <div class="sent-card neutral">
      <div class="sent-value">${fmt(stats.neu_ratio)}%</div>
      <div class="sent-label">중립 (${stats.neutral || 0}건)</div>
    </div>
    <div class="sent-card positive">
      <div class="sent-value">${fmt(stats.pos_ratio)}%</div>
      <div class="sent-label">긍정 (${stats.positive || 0}건)</div>
    </div>
  `;

  // 헤드라인
  const hlist = document.getElementById("headlines-list");
  hlist.innerHTML = headlines.slice(0, 5).map(h => {
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

    list.innerHTML = items.map(s => {
      const retClass = s.return_5d >= 0 ? "positive" : "negative";
      const retColor = s.return_5d >= 0 ? "var(--red)" : "var(--blue)";
      const badge = hiddenTickers.has(s.ticker) ? '<span class="hidden-badge">유망주</span>' : '';

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
        <div class="stock-return" style="color:${retColor}">${fmtSign(s.return_5d)}%</div>
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
function renderHiddenOpportunities() {
  const opps = DATA.hidden_opportunities || [];
  const section = document.getElementById("hidden-section");
  if (opps.length === 0) {
    section.style.display = "none";
    return;
  }
  section.style.display = "block";
  const list = document.getElementById("hidden-list");
  list.innerHTML = opps.map(o => `
    <div class="hidden-card">
      <div class="hc-header">
        <div>
          <div class="hc-name">${escapeHtml(o.name)}</div>
          <div class="hc-ticker">${o.ticker}</div>
        </div>
        <div class="hc-industry">${o.industry}</div>
      </div>
      <div class="hc-detail">
        ETF 비중 합계: <span>${fmt(o.weight)}%</span><br>
        최근 5일 수익률: <span style="color:${o.return_5d >= 0 ? 'var(--red)' : 'var(--blue)'}">${fmtSign(o.return_5d)}%</span><br>
        IS Score: <span>${fmt(o.is_score, 0)}</span>
      </div>
    </div>
  `).join("");
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
