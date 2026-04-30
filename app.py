import streamlit as st
import pandas as pd
import json
import os

# Streamlit Cloud Secrets → 환경변수로 설정
if hasattr(st, "secrets"):
    for key, val in st.secrets.items():
        os.environ[key] = str(val)
from datetime import datetime

# ── 페이지 설정 ──────────────────────────────
st.set_page_config(
    page_title="주식 분석 대시보드",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS 스타일 ───────────────────────────────
st.markdown("""
<style>
    /* 전체 배경 */
    .stApp { background-color: #0f1117; color: #e2e8f0; }
    .main .block-container { padding: 1.5rem 2rem; }

    /* 사이드바 */
    [data-testid="stSidebar"] {
        background-color: #1a1d27;
        border-right: 1px solid #2d3748;
    }

    /* 메트릭 카드 */
    [data-testid="metric-container"] {
        background: #1e2130;
        border: 1px solid #2d3748;
        border-radius: 10px;
        padding: 1rem;
    }

    /* 버튼 */
    .stButton > button {
        background: linear-gradient(135deg, #2563eb, #1d4ed8);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        padding: 0.6rem 1.5rem;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #1d4ed8, #1e40af);
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(37,99,235,0.4);
    }

    /* 테이블 헤더 */
    thead tr th {
        background-color: #1e2130 !important;
        color: #93c5fd !important;
        font-weight: 600 !important;
    }

    /* 섹션 헤더 */
    .section-header {
        font-size: 1.1rem;
        font-weight: 700;
        color: #93c5fd;
        border-left: 4px solid #2563eb;
        padding-left: 10px;
        margin: 1.5rem 0 0.8rem 0;
    }

    /* 상태 뱃지 */
    .badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
    }
    .badge-green  { background: #064e3b; color: #6ee7b7; }
    .badge-red    { background: #7f1d1d; color: #fca5a5; }
    .badge-yellow { background: #78350f; color: #fcd34d; }
    .badge-blue   { background: #1e3a5f; color: #93c5fd; }
    .badge-gray   { background: #374151; color: #d1d5db; }

    /* 탭 */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #1a1d27;
        border-radius: 10px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        color: #94a3b8;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2563eb !important;
        color: white !important;
        border-radius: 8px;
    }

    /* 입력 필드 */
    .stTextInput input, .stNumberInput input, .stSelectbox select {
        background-color: #1e2130 !important;
        color: #e2e8f0 !important;
        border: 1px solid #2d3748 !important;
        border-radius: 8px !important;
    }

    /* 데이터프레임 */
    [data-testid="stDataFrame"] {
        border: 1px solid #2d3748;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# ── 핵심 함수 import ─────────────────────────
try:
    from scanner_portpolio_v3 import (
        analyze_sectors, run_market_scan, run_portfolio_update,
        prepare_df, generate_chart_base64,
        print_sector_summary, SECTOR_ETFS,
    )
    FUNCTIONS_LOADED = True
except Exception as e:
    FUNCTIONS_LOADED = False
    IMPORT_ERROR = str(e)

# ── 섹터 맵 로드 ─────────────────────────────
def load_sector_map():
    if os.path.exists("sector_map_cache.json"):
        with open("sector_map_cache.json", "r") as f:
            return json.load(f)
    return {}

# ── 사이드바 ─────────────────────────────────
with st.sidebar:
    st.markdown("## 📈 주식 분석")
    st.markdown("---")

    st.markdown("### ⚙️ 설정")
    scan_threshold = st.slider("매수신호 최소 개수", 2, 5, 3)
    weekly_min     = st.slider("주봉 최소 점수",     0, 3, 2)

    st.markdown("---")
    st.markdown("### 📅 마지막 스캔")
    if os.path.exists(f"scan_result_{datetime.now().strftime('%Y%m%d')}.csv"):
        st.success(f"오늘 {datetime.now().strftime('%H:%M')} 완료")
    else:
        st.warning("오늘 스캔 없음")

    st.markdown("---")
    st.markdown(
        "<small style='color:#64748b'>자동 생성 | 투자 판단은 본인 책임</small>",
        unsafe_allow_html=True)

# ── 메인 타이틀 ──────────────────────────────
col_title, col_time = st.columns([3, 1])
with col_title:
    st.markdown("# 📈 주식 분석 대시보드")
with col_time:
    st.markdown(
        f"<p style='text-align:right;color:#64748b;margin-top:1.2rem'>"
        f"{datetime.now().strftime('%Y-%m-%d %H:%M')}</p>",
        unsafe_allow_html=True)

st.markdown("---")

# ── 함수 로드 실패 시 경고 ───────────────────
if not FUNCTIONS_LOADED:
    st.error(f"⚠ 함수 로드 실패: {IMPORT_ERROR}")
    st.info("scanner_portpolio_v3.py 파일이 같은 폴더에 있는지 확인해주세요.")
    st.stop()

# ── 탭 구성 ──────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 섹터 현황",
    "🔍 매수 시그널",
    "💼 포트폴리오",
    "📈 차트 조회",
])

# ════════════════════════════════════════════
#  TAB 1 — 섹터 현황
# ════════════════════════════════════════════
with tab1:
    st.markdown('<div class="section-header">섹터별 현황 (SPDR ETF 11개)</div>',
                unsafe_allow_html=True)

    if st.button("🔄 섹터 분석 실행", key="btn_sector"):
        with st.spinner("섹터 분석 중..."):
            sector_data = analyze_sectors()
            st.session_state["sector_data"] = sector_data
        st.success("섹터 분석 완료!")

    if "sector_data" in st.session_state:
        sd = st.session_state["sector_data"]
        rows = []
        for etf, d in sd.items():
            rows.append({
                "ETF":    etf,
                "섹터":   d["label"].split("(")[0].strip(),
                "주봉점수": f"{d['score']:+d}",
                "RSI":    f"{d['rsi']:.1f}",
                "1주":    f"{'▲' if d['bull_1w'] else '▼'}{abs(d['ret_1w']):.1f}%",
                "1달":    f"{'▲' if d['bull_1m'] else '▼'}{abs(d['ret_1m']):.1f}%",
                "분기":   f"{'▲' if d['bull_3m'] else '▼'}{abs(d['ret_3m']):.1f}%",
                "반기":   f"{'▲' if d['bull_6m'] else '▼'}{abs(d['ret_6m']):.1f}%",
                "추세유형": d["trend_type"],
                "상태":   d["status"],
            })
        df_sector = pd.DataFrame(rows)

        def color_status(val):
            if "강세" in str(val):
                return "color: #6ee7b7; font-weight: bold"
            elif "약세" in str(val):
                return "color: #fca5a5; font-weight: bold"
            elif "중립" in str(val):
                return "color: #fcd34d; font-weight: bold"
            return "color: #94a3b8"

        def color_trend(val):
            if val in ["완전상승", "상승추세"]:
                return "color: #6ee7b7"
            elif val in ["완전약세", "약세전환"]:
                return "color: #fca5a5"
            elif val in ["단기반등", "장기강세", "혼조"]:
                return "color: #fcd34d"
            return "color: #94a3b8"

        styled = df_sector.style\
            .applymap(color_status, subset=["상태"])\
            .applymap(color_trend,  subset=["추세유형"])\
            .set_properties(**{
                "background-color": "#1e2130",
                "color": "#e2e8f0",
                "border": "1px solid #2d3748",
            })
        st.dataframe(styled, use_container_width=True, height=420)
    else:
        st.info("위 버튼을 눌러 섹터 분석을 실행하세요.")

# ════════════════════════════════════════════
#  TAB 2 — 매수 시그널
# ════════════════════════════════════════════
with tab2:
    st.markdown('<div class="section-header">전종목 매수 시그널 스캔</div>',
                unsafe_allow_html=True)

    col_btn, col_info = st.columns([2, 3])
    with col_btn:
        run_scan = st.button("🚀 전종목 스캔 실행", key="btn_scan")
    with col_info:
        st.caption("⏱ S&P500 + 나스닥100 약 516종목 스캔 (5~10분 소요)")

    if run_scan:
        if "sector_data" not in st.session_state:
            with st.spinner("섹터 분석 중..."):
                st.session_state["sector_data"] = analyze_sectors()
        sector_map = load_sector_map()
        with st.spinner("전종목 스캔 중... 잠시 기다려주세요"):
            scan_res = run_market_scan(
                st.session_state["sector_data"], sector_map)
            st.session_state["scan_res"] = scan_res
        st.success(f"✅ 스캔 완료 — {len(scan_res)}종목 신호 발생!")

    # 오늘 CSV 있으면 자동 로드
    today_csv = f"scan_result_{datetime.now().strftime('%Y%m%d')}.csv"
    if "scan_res" not in st.session_state and os.path.exists(today_csv):
        df_csv = pd.read_csv(today_csv, encoding="utf-8-sig")
        st.session_state["scan_res"] = df_csv.to_dict("records")
        st.info(f"오늘 저장된 스캔 결과 자동 로드 ({len(df_csv)}종목)")

    if "scan_res" in st.session_state:
        scan_res = st.session_state["scan_res"]

        # 필터
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            filter_sector = st.selectbox(
                "섹터 필터",
                ["전체", "🟢 강세", "🟡 중립", "🔴 약세", "⚪ 관망"])
        with col_f2:
            filter_strategy = st.selectbox(
                "전략 필터", ["전체", "A", "C", "D"])
        with col_f3:
            filter_fund = st.selectbox(
                "펀더멘털", ["전체", "✅ 양호", "⚠ 주의", "🔴 위험"])

        rows = []
        for r in scan_res:
            sec    = r.get("sector", "미분류")
            strat  = r.get("strategy", "C")
            fund_j = r.get("fund_judge", "")

            if filter_sector   != "전체" and filter_sector not in sec:
                continue
            if filter_strategy != "전체" and strat != filter_strategy:
                continue
            if filter_fund     != "전체" and filter_fund not in str(fund_j):
                continue

            rows.append({
                "종목":     r.get("ticker", ""),
                "전략":     f"[{strat}]",
                "현재가":   f"${r.get('price', 0):.2f}",
                "매수신호": f"{r.get('signals', 0)}개",
                "보정":     f"{r.get('adj_sig', 0)}개",
                "주봉":     f"{r.get('weekly', 0):+d}",
                "섹터":     sec,
                "추세":     r.get("trend_type", ""),
                "손절가":   f"${r.get('stop', 0):.2f} ({r.get('stop_pct', 0):+.1f}%)",
                "목표가":   f"${r.get('target', 0):.2f} ({r.get('target_pct', 0):+.1f}%)",
                "R/R":     f"1:{r.get('rr', 0):.1f}",
                "펀더멘털": fund_j,
                "매수근거": r.get("buy_detail", r.get("details", "")),
            })

        if rows:
            df_scan = pd.DataFrame(rows)

            def color_sector(val):
                if "강세" in str(val): return "color: #6ee7b7"
                if "약세" in str(val): return "color: #fca5a5"
                if "중립" in str(val): return "color: #fcd34d"
                return "color: #94a3b8"

            def color_fund(val):
                if "✅" in str(val): return "color: #6ee7b7; font-weight:bold"
                if "⚠"  in str(val): return "color: #fcd34d; font-weight:bold"
                if "🔴" in str(val): return "color: #fca5a5; font-weight:bold"
                return "color: #94a3b8"

            styled_scan = df_scan.style\
                .applymap(color_sector, subset=["섹터"])\
                .applymap(color_fund,   subset=["펀더멘털"])\
                .set_properties(**{
                    "background-color": "#1e2130",
                    "color": "#e2e8f0",
                    "border": "1px solid #2d3748",
                })
            st.dataframe(styled_scan, use_container_width=True,
                         height=500)
            st.caption(f"총 {len(rows)}종목 표시 중")
        else:
            st.warning("필터 조건에 맞는 종목이 없어요.")

# ════════════════════════════════════════════
#  TAB 3 — 포트폴리오
# ════════════════════════════════════════════
with tab3:
    st.markdown('<div class="section-header">포트폴리오 현황</div>',
                unsafe_allow_html=True)

    col_pb1, col_pb2 = st.columns(2)
    with col_pb1:
        run_port = st.button("🔄 포트폴리오 업데이트", key="btn_port")
    with col_pb2:
        st.caption("Google Sheets에서 실시간 로드")

    if run_port:
        if "sector_data" not in st.session_state:
            with st.spinner("섹터 분석 중..."):
                st.session_state["sector_data"] = analyze_sectors()
        sector_map = load_sector_map()
        with st.spinner("포트폴리오 업데이트 중..."):
            port_res = run_portfolio_update(
                sector_map, st.session_state.get("sector_data"))
            st.session_state["port_res"] = port_res
        st.success("✅ 업데이트 완료!")

    if "port_res" in st.session_state:
        port_res = st.session_state["port_res"]

        if port_res:
            # 요약 메트릭
            total_eval = sum(r["eval_amt"] for r in port_res)
            total_pnl  = sum(r["pnl_amt"]  for r in port_res)
            total_cost = total_eval - total_pnl
            total_pct  = (total_pnl / total_cost * 100) if total_cost > 0 else 0

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("총 평가금액",
                      f"${total_eval:,.0f}")
            c2.metric("총 손익",
                      f"${total_pnl:+,.0f}",
                      f"{total_pct:+.2f}%")
            c3.metric("보유 종목 수", f"{len(port_res)}개")
            손절_count = sum(1 for r in port_res if "손절" in r["status"])
            c4.metric("⚠ 손절 고려",
                      f"{손절_count}개",
                      delta_color="inverse")

            st.markdown("---")

            rows = []
            for r in port_res:
                rows.append({
                    "종목":      r["ticker"],
                    "매수가":    f"${r['buy_price']:.2f}",
                    "현재가":    f"${r['cur_price']:.2f}",
                    "수익률":    f"{r['pnl_pct']:+.2f}%",
                    "평가손익":  f"${r['pnl_amt']:+,.0f}",
                    "보유일":    f"{r['hold_days']}일",
                    "목표진행률": f"{r.get('target_progress', 0):.1f}%",
                    "신호":      f"{r['signals']}개",
                    "메모":      r.get("memo", ""),
                    "상태":      r["status"],
                })
            df_port = pd.DataFrame(rows)

            def color_pnl(val):
                try:
                    v = float(str(val).replace("%","").replace("$","").replace("+","").replace(",",""))
                    if v > 0: return "color: #6ee7b7; font-weight: bold"
                    if v < 0: return "color: #fca5a5; font-weight: bold"
                except:
                    pass
                return ""

            def color_port_status(val):
                if "손절" in str(val):   return "color: #fca5a5; font-weight:bold"
                if "장기보유" in str(val): return "color: #6ee7b7; font-weight:bold"
                if "익절" in str(val):   return "color: #fcd34d; font-weight:bold"
                if "재진입" in str(val): return "color: #c4b5fd; font-weight:bold"
                if "추가매수" in str(val): return "color: #93c5fd; font-weight:bold"
                return "color: #94a3b8"

            styled_port = df_port.style\
                .applymap(color_pnl,         subset=["수익률", "평가손익"])\
                .applymap(color_port_status, subset=["상태"])\
                .set_properties(**{
                    "background-color": "#1e2130",
                    "color": "#e2e8f0",
                    "border": "1px solid #2d3748",
                })
            st.dataframe(styled_port, use_container_width=True,
                         height=380)
    else:
        st.info("위 버튼을 눌러 포트폴리오를 업데이트하세요.")

# ════════════════════════════════════════════
#  TAB 4 — 차트 조회
# ════════════════════════════════════════════
with tab4:
    st.markdown('<div class="section-header">종목 차트 조회</div>',
                unsafe_allow_html=True)

    col_input, col_btn_chart = st.columns([3, 1])
    with col_input:
        ticker_input = st.text_input(
            "종목 티커 입력",
            placeholder="예: NVDA, AAPL, TSLA",
            key="chart_ticker")
    with col_btn_chart:
        st.markdown("<br>", unsafe_allow_html=True)
        show_chart = st.button("📊 차트 보기", key="btn_chart")

    if show_chart and ticker_input:
        ticker = ticker_input.strip().upper()
        with st.spinner(f"{ticker} 차트 로딩 중..."):
            try:
                d_df, _ = prepare_df(ticker)
                if d_df is not None:
                    import io, base64
                    import matplotlib
                    matplotlib.use("Agg")
                    img_b64 = generate_chart_base64(ticker, d_df)
                    if img_b64:
                        img_bytes = base64.b64decode(img_b64)
                        st.image(img_bytes,
                                 caption=f"{ticker} — 일봉 180일",
                                 use_column_width=True)
                    else:
                        st.error("차트 생성 실패")
                else:
                    st.error(f"{ticker} 데이터를 가져올 수 없어요.")
            except Exception as e:
                st.error(f"오류: {e}")

    # 스캔 결과에서 종목 선택
    if "scan_res" in st.session_state and st.session_state["scan_res"]:
        st.markdown("---")
        st.markdown("**매수 시그널 종목 차트 바로 보기**")
        tickers = [r.get("ticker","") for r in st.session_state["scan_res"]]
        selected = st.selectbox("종목 선택", tickers, key="chart_select")
        if st.button("선택 종목 차트", key="btn_chart_select"):
            with st.spinner(f"{selected} 차트 로딩 중..."):
                try:
                    d_df, _ = prepare_df(selected)
                    if d_df is not None:
                        import io, base64
                        import matplotlib
                        matplotlib.use("Agg")
                        img_b64 = generate_chart_base64(selected, d_df)
                        if img_b64:
                            img_bytes = base64.b64decode(img_b64)
                            st.image(img_bytes,
                                     caption=f"{selected} — 일봉 180일",
                                     use_column_width=True)
                except Exception as e:
                    st.error(f"오류: {e}")