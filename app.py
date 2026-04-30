import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

# ── Streamlit Cloud Secrets → 환경변수 설정 ──
if hasattr(st, "secrets"):
    for key, val in st.secrets.items():
        if isinstance(val, str):
            os.environ[key] = val

# ── 페이지 설정 ──────────────────────────────
st.set_page_config(
    page_title="주식 분석 대시보드",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ──────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #0f1117; color: #e2e8f0; }
    .main .block-container { padding: 1.5rem 2rem; }
    [data-testid="stSidebar"] {
        background-color: #1a1d27;
        border-right: 1px solid #2d3748;
    }
    .stButton > button {
        background: linear-gradient(135deg, #2563eb, #1d4ed8);
        color: white; border: none; border-radius: 8px;
        font-weight: 600; padding: 0.6rem 1.5rem; transition: all 0.2s;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #1d4ed8, #1e40af);
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(37,99,235,0.4);
    }
    .stTabs [data-baseweb="tab-list"] {
        background-color: #1a1d27; border-radius: 10px; padding: 4px;
    }
    .stTabs [data-baseweb="tab"] { color: #94a3b8; font-weight: 600; }
    .stTabs [aria-selected="true"] {
        background-color: #2563eb !important;
        color: white !important; border-radius: 8px;
    }
    /* HTML 테이블 공통 스타일 */
    .dash-table {
        width: 100%; border-collapse: collapse;
        font-size: 13px; font-family: Arial, sans-serif;
        margin-bottom: 8px;
    }
    .dash-table th {
        padding: 10px 14px; font-weight: 700; font-size: 12px;
        border-bottom: 2px solid #2d3748; white-space: nowrap;
    }
    .dash-table td {
        padding: 9px 14px; border-bottom: 1px solid #1e2130;
        font-size: 13px;
    }
    .dash-table tr:hover td { background-color: #1e2a3a !important; }
    .section-title {
        font-size: 1.05rem; font-weight: 700; color: #93c5fd;
        border-left: 4px solid #2563eb; padding-left: 10px;
        margin: 1.2rem 0 0.6rem 0;
    }
    .footnote {
        font-size: 11px; color: #64748b;
        line-height: 1.8; margin-top: 6px;
    }
    [data-testid="metric-container"] {
        background: #1e2130; border: 1px solid #2d3748;
        border-radius: 10px; padding: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ── 함수 import ──────────────────────────────
try:
    from scanner_portpolio_v3 import (
        analyze_sectors, run_market_scan, run_portfolio_update,
        prepare_df, generate_chart_base64,
        SECTOR_STRATEGY, DEFAULT_STRATEGY,
        TICKER_SECTOR, SECTOR_EXCEPTIONS_LABEL,
    )
    LOADED = True
except Exception as e:
    LOADED = False
    LOAD_ERR = str(e)

def load_sector_map():
    # 현재 파일 기준 절대 경로로 찾기
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cache_path = os.path.join(base_dir, "sector_map_cache.json")
    if os.path.exists(cache_path):
        with open(cache_path, "r") as f:
            return json.load(f)
    # TICKER_SECTOR 폴백
    try:
        from scanner_portpolio_v3 import TICKER_SECTOR
        return TICKER_SECTOR
    except:
        return {}

# ── 사이드바 ─────────────────────────────────
with st.sidebar:
    st.markdown("## 📈 주식 분석")
    st.markdown("---")
    st.markdown("### 📅 오늘 스캔")
    today_csv = f"scan_result_{datetime.now().strftime('%Y%m%d')}.csv"
    if os.path.exists(today_csv):
        st.success(f"완료 ✅")
    else:
        st.warning("미실행")
    st.markdown("---")
    st.markdown("<small style='color:#64748b'>투자 판단은 본인 책임</small>",
                unsafe_allow_html=True)

# ── 타이틀 ───────────────────────────────────
c1, c2 = st.columns([3, 1])
with c1:
    st.markdown("# 📈 주식 분석 대시보드")
with c2:
    st.markdown(
        f"<p style='text-align:right;color:#64748b;margin-top:1.2rem'>"
        f"{datetime.now().strftime('%Y-%m-%d %H:%M')}</p>",
        unsafe_allow_html=True)
st.markdown("---")

if not LOADED:
    st.error(f"함수 로드 실패: {LOAD_ERR}")
    st.stop()

# ── 탭 ───────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 섹터 현황", "🔍 매수 시그널", "💼 포트폴리오", "📈 차트 조회"
])

# ════════════════════════
#  TAB 1 — 섹터 현황
# ════════════════════════
with tab1:
    st.markdown('<div class="section-title">섹터별 현황 (SPDR ETF 11개)</div>',
                unsafe_allow_html=True)

    if st.button("🔄 섹터 분석 실행", key="btn_sector"):
        with st.spinner("분석 중..."):
            st.session_state["sector_data"] = analyze_sectors()
        st.success("완료!")

    if "sector_data" in st.session_state:
        sd = st.session_state["sector_data"]

        # 메일과 동일한 HTML 테이블
        rows_html = ""
        for etf, d in sd.items():
            if   "강세" in d["status"]: bg="#0d2318"; sc="#6ee7b7"
            elif "약세" in d["status"]: bg="#2d1515"; sc="#fca5a5"
            elif "중립" in d["status"]: bg="#2a1f0a"; sc="#fcd34d"
            else:                       bg="#1a1d27"; sc="#94a3b8"
            sc2 = "#6ee7b7" if d["score"]>=2 else "#fca5a5" if d["score"]<=-1 else "#fcd34d"
            r1w = "#6ee7b7" if d["ret_1w"]>0 else "#fca5a5"
            r1c = "#6ee7b7" if d["ret_1m"]>0 else "#fca5a5"
            r3c = "#6ee7b7" if d["ret_3m"]>0 else "#fca5a5"
            r6m = "#6ee7b7" if d["ret_6m"]>0 else "#fca5a5"
            trend_colors = {
                "완전상승":"#6ee7b7","상승추세":"#6ee7b7","장기강세":"#fcd34d",
                "단기반등":"#fcd34d","혼조":"#fcd34d","반등시도":"#fca5a5",
                "약세전환":"#fca5a5","완전약세":"#fca5a5",
            }
            tc = trend_colors.get(d["trend_type"], "#94a3b8")
            strat = SECTOR_STRATEGY.get(etf, DEFAULT_STRATEGY)

            rows_html += f"""
<tr style="background:{bg}">
  <td style="font-weight:700;color:#60a5fa">{etf}</td>
  <td>{d["label"].split("(")[0].strip()}</td>
  <td style="text-align:center;color:{sc2};font-weight:700">{d["score"]:+d}</td>
  <td style="text-align:center">{d["rsi"]:.1f}</td>
  <td style="text-align:center;color:{r1w};font-weight:600">{d["ret_1w"]:+.1f}%</td>
  <td style="text-align:center;color:{r1c};font-weight:600">{d["ret_1m"]:+.1f}%</td>
  <td style="text-align:center;color:{r3c};font-weight:600">{d["ret_3m"]:+.1f}%</td>
  <td style="text-align:center;color:{r6m};font-weight:600">{d["ret_6m"]:+.1f}%</td>
  <td style="text-align:center;color:{tc};font-weight:700">{d["trend_type"]}</td>
  <td style="text-align:center;color:#c4b5fd;font-weight:700">{strat}</td>
  <td style="text-align:center;color:{sc};font-weight:700">{d["status"]}</td>
</tr>"""

        html = f"""
<table class="dash-table">
<thead><tr style="background:#1e3a5f;color:#93c5fd">
  <th>ETF</th><th>섹터</th><th>주봉점수</th><th>RSI</th>
  <th>1주</th><th>1달</th><th>분기</th><th>반기</th>
  <th>추세유형</th><th>전략</th><th>상태</th>
</tr></thead>
<tbody>{rows_html}</tbody>
</table>
<p class="footnote">
  ※ 전략A — 신호 3개+ (주봉 무관) | 에너지·소재·산업재·유틸리티·부동산<br>
  ※ 전략C — 주봉+2 + 신호 3개+ | 기술·커뮤니케이션·임의소비재·헬스케어·필수소비재<br>
  ※ 전략D — 주봉+2 + 구름대 + 신호 3개+ | 금융
</p>"""
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.info("버튼을 눌러 섹터 분석을 실행하세요.")

# ════════════════════════
#  TAB 2 — 매수 시그널
# ════════════════════════
with tab2:
    st.markdown('<div class="section-title">전종목 매수 시그널 스캔</div>',
                unsafe_allow_html=True)

    cb1, cb2 = st.columns([2, 3])
    with cb1:
        run_scan = st.button("🚀 전종목 스캔 실행", key="btn_scan")
    with cb2:
        st.caption("⏱ S&P500+나스닥100 약 516종목 (5~10분 소요)")

    if run_scan:
        if "sector_data" not in st.session_state:
            with st.spinner("섹터 분석 중..."):
                st.session_state["sector_data"] = analyze_sectors()
        with st.spinner("스캔 중..."):
            _sector_map = load_sector_map()
            from scanner_portpolio_v3 import ADJ_THRESHOLD, SCAN_BUY_THRESHOLD
            st.write(f"sector_map 종목 수: {len(_sector_map)}")
            st.write(f"sector_data 키 수: {len(st.session_state.get('sector_data', {}))}")
            st.write(f"ADJ_THRESHOLD: {ADJ_THRESHOLD}")
            st.write(f"SCAN_BUY_THRESHOLD: {SCAN_BUY_THRESHOLD}")
            st.session_state["scan_res"] = run_market_scan(
                st.session_state["sector_data"], _sector_map)
        st.success(f"✅ {len(st.session_state['scan_res'])}종목 신호 발생!")

    if "scan_res" not in st.session_state and os.path.exists(today_csv):
        df_csv = pd.read_csv(today_csv, encoding="utf-8-sig")
        st.session_state["scan_res"] = df_csv.to_dict("records")
        st.info(f"오늘 저장된 결과 로드 ({len(df_csv)}종목)")

    if "scan_res" in st.session_state:
        scan_res = st.session_state["scan_res"]

        # 필터
        f1, f2, f3 = st.columns(3)
        with f1:
            fs = st.selectbox("섹터", ["전체","🟢 강세","🟡 중립","🔴 약세","⚪ 관망"])
        with f2:
            fst = st.selectbox("전략", ["전체","A","C","D"])
        with f3:
            ff = st.selectbox("펀더멘털", ["전체","✅ 양호","⚠ 주의","🔴 위험"])

        filtered = [r for r in scan_res
                    if (fs=="전체" or fs in r.get("sector",""))
                    and (fst=="전체" or r.get("strategy","C")==fst)
                    and (ff=="전체" or ff in str(r.get("fund_judge","")))]

        rows_html = ""
        for i, r in enumerate(filtered):
            bg    = "#0d1f17" if i%2==0 else "#1a1d27"
            sec   = r.get("sector","미분류")
            sec_c = "#6ee7b7" if "강세" in sec else "#fca5a5" if "약세" in sec \
                    else "#fcd34d" if "중립" in sec else "#94a3b8"
            rr_c  = "#6ee7b7" if r.get("rr",0)>=2 else "#fca5a5"
            sp    = r.get("stop_pct", round((r["stop"]/r["price"]-1)*100,1))
            tp    = r.get("target_pct", round((r["target"]/r["price"]-1)*100,1))
            fj    = r.get("fund_judge","")
            fj_c  = "#6ee7b7" if "✅" in fj else "#fcd34d" if "⚠" in fj \
                    else "#fca5a5" if "🔴" in fj else "#94a3b8"
            buy_d = r.get("buy_detail", r.get("details",""))
            sell_d= r.get("sell_detail","없음")

            rows_html += f"""
<tr style="background:{bg}">
  <td style="font-weight:700;color:#60a5fa;font-size:14px">{r.get("ticker","")}</td>
  <td style="text-align:right">${r.get("price",0):.2f}</td>
  <td style="text-align:center">
    <span style="background:#064e3b;color:#6ee7b7;padding:2px 8px;border-radius:10px;font-weight:700">{r.get("signals",0)}개</span></td>
  <td style="text-align:center">
    <span style="background:#7f1d1d;color:#fca5a5;padding:2px 8px;border-radius:10px;font-weight:700">{r.get("sell_cnt",0)}개</span></td>
  <td style="text-align:center">
    <span style="background:#1e3a8a;color:#93c5fd;padding:2px 8px;border-radius:10px;font-weight:700">{r.get("adj_sig",0)}개</span></td>
  <td style="text-align:center;color:{'#6ee7b7' if r.get('weekly',0)>=2 else '#fcd34d'};font-weight:600">{r.get("weekly",0):+d}</td>
  <td style="text-align:center;color:#c4b5fd;font-weight:700">[{r.get("strategy","C")}]</td>
  <td style="text-align:center;color:{sec_c};font-weight:600;font-size:12px">{sec}</td>
  <td style="text-align:center;color:#fca5a5;font-weight:600">${r.get("stop",0):.2f}<br><small>{sp:+.1f}%</small></td>
  <td style="text-align:center;color:#6ee7b7;font-weight:600">${r.get("target",0):.2f}<br><small>{tp:+.1f}%</small></td>
  <td style="color:#86efac;font-size:12px;max-width:180px;word-break:break-word">{buy_d}</td>
  <td style="color:#fca5a5;font-size:12px;max-width:140px;word-break:break-word">{sell_d}</td>
  <td style="color:{fj_c};font-weight:700;font-size:12px">{fj}</td>
</tr>"""

        html = f"""
<table class="dash-table" style="table-layout:fixed">
<thead><tr style="background:#064e3b;color:#86efac">
  <th>종목</th><th style="text-align:right">현재가</th>
  <th style="text-align:center">매수</th><th style="text-align:center">매도</th>
  <th style="text-align:center">보정</th><th style="text-align:center">주봉</th>
  <th style="text-align:center">전략</th><th style="text-align:center">섹터</th>
  <th style="text-align:center">손절가(%)</th><th style="text-align:center">목표가(%)</th>
  <th style="width:180px">매수 근거</th><th style="width:140px">매도 근거</th>
  <th style="text-align:center">펀더멘털</th>
</tr></thead>
<tbody>{rows_html}</tbody>
</table>
<p style="color:#64748b;font-size:12px;margin-top:4px">총 {len(filtered)}종목</p>"""
        st.markdown(html, unsafe_allow_html=True)

# ════════════════════════
#  TAB 3 — 포트폴리오
# ════════════════════════
with tab3:
    st.markdown('<div class="section-title">포트폴리오 현황</div>',
                unsafe_allow_html=True)

    pb1, pb2 = st.columns([2, 3])
    with pb1:
        run_port = st.button("🔄 포트폴리오 업데이트", key="btn_port")
    with pb2:
        st.caption("Google Sheets 연동")

    if run_port:
        if "sector_data" not in st.session_state:
            with st.spinner("섹터 분석 중..."):
                st.session_state["sector_data"] = analyze_sectors()
        with st.spinner("업데이트 중..."):
            st.session_state["port_res"] = run_portfolio_update(
                load_sector_map(), st.session_state.get("sector_data"))
        st.success("✅ 완료!")

    if "port_res" in st.session_state:
        port_res = st.session_state["port_res"]
        if port_res:
            # 요약 메트릭
            total_eval = sum(r["eval_amt"] for r in port_res)
            total_pnl  = sum(r["pnl_amt"]  for r in port_res)
            total_cost = total_eval - total_pnl
            total_pct  = (total_pnl/total_cost*100) if total_cost>0 else 0
            손절 = sum(1 for r in port_res if "손절" in r["status"])

            m1,m2,m3,m4 = st.columns(4)
            m1.metric("총 평가금액", f"${total_eval:,.0f}")
            m2.metric("총 손익", f"${total_pnl:+,.0f}", f"{total_pct:+.2f}%")
            m3.metric("보유 종목", f"{len(port_res)}개")
            m4.metric("⚠ 손절 고려", f"{손절}개", delta_color="inverse")

            st.markdown("---")

            rows_html = ""
            for i, r in enumerate(port_res):
                bg = "#1a1425" if i%2==0 else "#1a1d27"
                pc = "#6ee7b7" if r["pnl_pct"]>=0 else "#fca5a5"
                tp = r.get("target_progress",0)
                tp_c = "#6ee7b7" if tp>=50 else "#94a3b8"

                def status_color(s):
                    if "손절" in s:    return "#fca5a5"
                    if "장기보유" in s: return "#6ee7b7"
                    if "익절" in s:    return "#fcd34d"
                    if "재진입" in s:  return "#c4b5fd"
                    if "추가매수" in s: return "#93c5fd"
                    return "#94a3b8"

                sc = status_color(r["status"])
                rows_html += f"""
<tr style="background:{bg}">
  <td style="font-weight:700;color:#c4b5fd;font-size:14px">{r["ticker"]}</td>
  <td style="text-align:right">${r["buy_price"]:.2f}</td>
  <td style="text-align:right">${r["cur_price"]:.2f}</td>
  <td style="text-align:center;color:{pc};font-weight:700">{r["pnl_pct"]:+.2f}%</td>
  <td style="text-align:right;color:{pc}">${r["pnl_amt"]:+,.0f}</td>
  <td style="text-align:center">{r["hold_days"]}일</td>
  <td style="text-align:center;font-size:12px">{r.get("sector","미분류")}</td>
  <td style="text-align:center;color:#fca5a5;font-weight:600">${r["stop"]:.2f}<br><small>{r["stop_dist"]:+.1f}%</small></td>
  <td style="text-align:center;color:#6ee7b7;font-weight:600">${r["target"]:.2f}<br><small>{r["target_dist"]:+.1f}%</small></td>
  <td style="text-align:center;color:{tp_c};font-weight:600">{tp:.1f}%</td>
  <td style="text-align:center">{r["signals"]}개</td>
  <td style="font-size:12px;color:#64748b">{r.get("memo","")}</td>
  <td style="color:{sc};font-weight:700;font-size:12px">{r["status"]}</td>
</tr>"""

            html = f"""
<table class="dash-table">
<thead><tr style="background:#2d1b69;color:#c4b5fd">
  <th>종목</th><th style="text-align:right">매수가</th>
  <th style="text-align:right">현재가</th><th style="text-align:center">수익률</th>
  <th style="text-align:right">평가손익</th><th style="text-align:center">보유일</th>
  <th style="text-align:center">섹터</th>
  <th style="text-align:center">손절가(%)</th><th style="text-align:center">목표가(%)</th>
  <th style="text-align:center">목표진행률</th><th style="text-align:center">신호</th>
  <th>메모</th><th>상태</th>
</tr></thead>
<tbody>{rows_html}</tbody>
</table>"""
            st.markdown(html, unsafe_allow_html=True)

            # 펀더멘털 섹션
            st.markdown('<div class="section-title" style="margin-top:1.5rem">🔬 펀더멘털 체크리스트 — 내 포트폴리오</div>',
                        unsafe_allow_html=True)
            fund_rows = ""
            for i, r in enumerate(port_res):
                bg    = "#0c1929" if i%2==0 else "#1a1d27"
                judge = r.get("fund_judge","")
                jc    = "#6ee7b7" if "✅" in judge else "#fcd34d" if "⚠" in judge \
                        else "#fca5a5" if "🔴" in judge else "#94a3b8"
                etf_c = TICKER_SECTOR.get(r["ticker"].upper(),"")
                exc   = SECTOR_EXCEPTIONS_LABEL.get(etf_c,"해당없음")
                fund_rows += f"""
<tr style="background:{bg}">
  <td style="font-weight:700;color:#c4b5fd">{r["ticker"]}</td>
  <td style="text-align:center;color:{jc};font-weight:700">{judge}({r.get("fund_cnt",0)}/8)</td>
  <td style="color:#fca5a5;font-size:12px">{r.get("fund_risks","없음")}</td>
  <td style="color:#64748b;font-size:12px">{exc}</td>
</tr>"""
            st.markdown(f"""
<table class="dash-table">
<thead><tr style="background:#164e63;color:#67e8f9">
  <th>종목</th><th style="text-align:center">판정</th>
  <th>위험 항목</th><th>섹터 예외</th>
</tr></thead><tbody>{fund_rows}</tbody></table>
<p class="footnote">
  ✅ 양호(0개) | ⚠ 주의(1~2개) | 🔴 위험(3개 이상)
</p>""", unsafe_allow_html=True)
    else:
        st.info("버튼을 눌러 포트폴리오를 업데이트하세요.")

# ════════════════════════
#  TAB 4 — 차트 조회
# ════════════════════════
with tab4:
    st.markdown('<div class="section-title">종목 차트 조회 (일봉 180일)</div>',
                unsafe_allow_html=True)

    ci1, ci2 = st.columns([3, 1])
    with ci1:
        ticker_input = st.text_input("종목 티커", placeholder="예: NVDA, AAPL")
    with ci2:
        st.markdown("<br>", unsafe_allow_html=True)
        show_chart = st.button("📊 차트", key="btn_chart")

    if show_chart and ticker_input:
        with st.spinner(f"{ticker_input.upper()} 차트 생성 중..."):
            try:
                import base64, matplotlib
                matplotlib.use("Agg")
                d_df, _ = prepare_df(ticker_input.strip().upper())
                if d_df is not None:
                    img_b64 = generate_chart_base64(ticker_input.upper(), d_df)
                    if img_b64:
                        st.image(base64.b64decode(img_b64),
                                 caption=f"{ticker_input.upper()} — 일봉 180일",
                                 use_column_width=True)
                else:
                    st.error("데이터를 가져올 수 없어요.")
            except Exception as e:
                st.error(f"오류: {e}")

    if "scan_res" in st.session_state and st.session_state["scan_res"]:
        st.markdown("---")
        st.markdown("**매수 시그널 종목에서 선택**")
        tickers = [r.get("ticker","") for r in st.session_state["scan_res"]]
        sel = st.selectbox("종목 선택", tickers, key="chart_sel")
        if st.button("선택 종목 차트", key="btn_chart_sel"):
            with st.spinner(f"{sel} 차트 생성 중..."):
                try:
                    import base64, matplotlib
                    matplotlib.use("Agg")
                    d_df, _ = prepare_df(sel)
                    if d_df is not None:
                        img_b64 = generate_chart_base64(sel, d_df)
                        if img_b64:
                            st.image(base64.b64decode(img_b64),
                                     caption=f"{sel} — 일봉 180일",
                                     use_column_width=True)
                except Exception as e:
                    st.error(f"오류: {e}")