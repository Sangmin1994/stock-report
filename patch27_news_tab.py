"""
patch27_news_tab.py
- run_news_scan(): yfinance.news 기반 종목별 뉴스 수집
  · 날짜 필터: KST 기준 스캔 당일 + 전날
  · 국내 뉴스 5개 / 주요 해외 언론사 뉴스 5개
  · 키워드 기반 액션 추천
- daily_job(): news_res 수집 + generate_html_report 전달
- generate_html_report(): 뉴스 탭 추가
"""
import json, sys

NB_PATH = r"C:\Users\Sangmin\Desktop\Stock\scanner_portpolio_v4.ipynb"

with open(NB_PATH, 'r', encoding='utf-8') as f:
    nb = json.load(f)
src = ''.join(nb['cells'][0]['source'])

# ═══════════════════════════════════════════════════════════════════
# 1. run_news_scan 함수 추가 (daily_job 정의 바로 앞에 삽입)
# ═══════════════════════════════════════════════════════════════════
OLD_DAILY_JOB_DEF = '''def daily_job():
    import json, os
    print("  ✅ PATCH v3 로드 확인 — 산업별 현황 + 404억제 활성")'''

NEW_DAILY_JOB_DEF = '''# ════════════════════════════════════════════════════════
#  8-C. 뉴스 스캔
# ════════════════════════════════════════════════════════
def run_news_scan(unified_portfolio, scan_date=None):
    """포트폴리오 종목별 뉴스 수집 (yfinance.news + 날짜/언론사 필터)"""
    import yfinance as yf
    from datetime import datetime, timedelta, timezone

    KST = timezone(timedelta(hours=9))
    today_kst = datetime.now(KST).date()

    if scan_date is None:
        target_date = today_kst
    else:
        try:
            target_date = datetime.strptime(str(scan_date), "%Y-%m-%d").date()
        except Exception:
            target_date = today_kst

    # 허용 날짜 범위: 전날 ~ 당일 (KST)
    allowed_dates = {target_date - timedelta(days=1), target_date}

    # 주요 해외 언론사 (소문자 포함 키워드 매칭)
    MAJOR_INTL = {
        "bloomberg", "cnbc", "reuters", "wall street journal", "wsj",
        "new york times", "nytimes", "axios", "financial times",
        "ft.com", "barron", "marketwatch", "fortune", "business insider",
        "associated press", "ap news", "the guardian",
    }

    # 국내 언론사 키워드 (yfinance가 가져오는 한국 뉴스 퍼블리셔)
    KO_PUBLISHERS = {
        "연합뉴스", "한국경제", "매일경제", "조선비즈", "서울경제",
        "머니투데이", "이데일리", "헤럴드경제", "파이낸셜뉴스",
        "뉴스1", "아시아경제", "edaily", "hankyung", "yonhap",
        "maeil", "joins", "kbs", "mbc", "yna.co.kr",
    }

    POSITIVE_KW = {
        "beat", "beats", "record", "surge", "rally", "upgrade", "buy",
        "strong", "better", "exceed", "growth", "profit", "revenue beat",
        "outperform", "positive", "breakthrough", "partnership", "contract",
        "호실적", "상승", "매수", "상향", "호조", "성장", "흑자", "수주",
        "협력", "계약", "신고가", "돌파", "강세",
    }
    NEGATIVE_KW = {
        "miss", "misses", "decline", "fall", "drop", "downgrade", "sell",
        "below", "weak", "loss", "layoff", "investigation", "warning",
        "recall", "lawsuit", "fine", "penalty", "shortfall", "cut",
        "실적부진", "하락", "매도", "하향", "적자", "손실", "리콜",
        "조사", "제재", "감원", "경고", "약세", "급락",
    }

    def _sentiment(news_list):
        score = 0
        for n in news_list:
            text = (n.get("title","") + " " + n.get("summary","")).lower()
            for kw in POSITIVE_KW:
                if kw in text: score += 1
            for kw in NEGATIVE_KW:
                if kw in text: score -= 1
        if score >= 2:
            return {"label": "📈 긍정적", "detail": "매수/보유 검토", "color": "#15b98a"}
        elif score <= -2:
            return {"label": "📉 부정적", "detail": "매도/손절 검토", "color": "#f87171"}
        elif score == 1:
            return {"label": "🟡 약 긍정", "detail": "관망하며 모니터링", "color": "#f5c842"}
        elif score == -1:
            return {"label": "🟠 약 부정", "detail": "리스크 주의", "color": "#fb923c"}
        else:
            return {"label": "⚖ 중립", "detail": "현 포지션 유지", "color": "#64748b"}

    results = {}
    stocks = unified_portfolio.get("stocks", []) if unified_portfolio else []

    for stock in stocks:
        ticker = stock.get("ticker", "").strip()
        name   = stock.get("name", ticker)
        market = stock.get("market", "")
        if not ticker:
            continue

        # yfinance 티커 형식
        if market in ("국내", "국내ETF"):
            yf_ticker = ticker if ticker.endswith(".KS") or ticker.endswith(".KQ") \
                        else ticker + ".KS"
        else:
            yf_ticker = ticker

        ko_news, en_news = [], []
        try:
            raw_news = yf.Ticker(yf_ticker).news or []
        except Exception as e:
            print(f"  [{ticker}] 뉴스 오류: {e}")
            raw_news = []

        for item in raw_news:
            # 날짜 필터 (KST 기준)
            pub_ts = item.get("providerPublishTime") or 0
            if pub_ts:
                pub_date = datetime.fromtimestamp(pub_ts, tz=KST).date()
                if pub_date not in allowed_dates:
                    continue

            title     = item.get("title", "")
            publisher = item.get("publisher", "") or ""
            link      = item.get("link", "")
            summary   = item.get("summary", "") or item.get("description", "") or ""
            pub_lower = publisher.lower()

            news_obj = {
                "title":     title,
                "publisher": publisher,
                "link":      link,
                "summary":   summary[:200] if summary else "",
                "date":      datetime.fromtimestamp(pub_ts, tz=KST).strftime("%m/%d %H:%M") if pub_ts else "",
            }

            # 국내 뉴스 판별
            is_korean = any(kw in pub_lower for kw in KO_PUBLISHERS)
            # 주요 해외 언론사 판별
            is_major_intl = any(kw in pub_lower for kw in MAJOR_INTL)

            if is_korean and len(ko_news) < 5:
                ko_news.append(news_obj)
            elif not is_korean and is_major_intl and len(en_news) < 5:
                en_news.append(news_obj)
            # 주요 언론사 아니어도 해외 뉴스 5개 미만이면 보조로 추가
            elif not is_korean and not is_major_intl and len(en_news) < 5:
                news_obj["minor"] = True
                en_news.append(news_obj)

        # 한국 종목인데 국내 뉴스 없으면 en_news를 ko로 전환
        if market in ("국내", "국내ETF") and not ko_news and en_news:
            ko_news, en_news = en_news, []

        action = _sentiment(ko_news + en_news)
        results[ticker] = {
            "name":    name,
            "market":  market,
            "ko_news": ko_news[:5],
            "en_news": en_news[:5],
            "action":  action,
        }
        print(f"  [{ticker}] 국내:{len(ko_news)} 해외:{len(en_news)} → {action['label']}")

    print(f"  뉴스 스캔 완료: {len(results)}종목")
    return results


def daily_job():
    import json, os
    print("  ✅ PATCH v3 로드 확인 — 산업별 현황 + 404억제 활성")'''

# ═══════════════════════════════════════════════════════════════════
# 2. daily_job에 news_res 수집 + html 호출에 전달
# ═══════════════════════════════════════════════════════════════════
OLD_HTML_CALL = '''    # ── HTML 리포트 생성 ──
    generate_html_report(scan_res, port_res, sector_data, vc_res, earn_res,
                          sector_map=sector_map, unified_portfolio=unified_portfolio)'''

NEW_HTML_CALL = '''    # ── 뉴스 스캔 ──
    print("\n  [뉴스 스캔] 포트폴리오 종목별 뉴스 수집 중...")
    try:
        news_res = run_news_scan(unified_portfolio)
    except Exception as _e:
        print(f"  ⚠ 뉴스 스캔 실패: {_e}")
        news_res = {}

    # ── HTML 리포트 생성 ──
    generate_html_report(scan_res, port_res, sector_data, vc_res, earn_res,
                          sector_map=sector_map, unified_portfolio=unified_portfolio,
                          news_res=news_res)'''

# ═══════════════════════════════════════════════════════════════════
# 3. generate_html_report 파라미터에 news_res 추가
# ═══════════════════════════════════════════════════════════════════
OLD_FUNC_SIG = '''def generate_html_report(scan_res, port_res, sector_data, vc_res, earn_res,
                          sector_map=None, unified_portfolio=None):
    """samsung-bonus.pages.dev 스타일 다크 네온 HTML 리포트 생성"""'''

NEW_FUNC_SIG = '''def generate_html_report(scan_res, port_res, sector_data, vc_res, earn_res,
                          sector_map=None, unified_portfolio=None, news_res=None):
    """samsung-bonus.pages.dev 스타일 다크 네온 HTML 리포트 생성"""'''

# ═══════════════════════════════════════════════════════════════════
# 4. 탭 버튼에 뉴스 탭 추가
# ═══════════════════════════════════════════════════════════════════
OLD_TAB_BTNS = '''  <button class="tab-btn" data-tab="vc" onclick="switchTab('vc')">포트폴리오 벨류체인 현황</button>
</div>'''

NEW_TAB_BTNS = '''  <button class="tab-btn" data-tab="vc" onclick="switchTab('vc')">포트폴리오 벨류체인 현황</button>
  <button class="tab-btn" data-tab="news" onclick="switchTab('news')">📰 뉴스</button>
</div>'''

# ═══════════════════════════════════════════════════════════════════
# 5. VC 탭 다음에 뉴스 탭 HTML 블록 추가
# ═══════════════════════════════════════════════════════════════════
OLD_AFTER_VC_TAB = '''<!-- TAB: 벨류체인 -->
<div id="tab-vc" class="tab-content">
  <div class="section">
    <div class="section-title">벨류체인 투자 현황</div>
    {vc_html}
  </div>
</div>

<script>{JS}</script>'''

NEW_AFTER_VC_TAB = '''<!-- TAB: 벨류체인 -->
<div id="tab-vc" class="tab-content">
  <div class="section">
    <div class="section-title">벨류체인 투자 현황</div>
    {vc_html}
  </div>
</div>

<!-- TAB: 뉴스 -->
<div id="tab-news" class="tab-content">
  <div class="section">
    <div class="section-title">포트폴리오 종목별 뉴스</div>
    {news_html}
  </div>
</div>

<script>{JS}</script>'''

# ═══════════════════════════════════════════════════════════════════
# 6. vc_html 생성 코드 뒤에 news_html 생성 코드 추가
# ═══════════════════════════════════════════════════════════════════
OLD_AFTER_VC_CODE = '''    vc_html = _vc_html(vc_res or [])'''

NEW_AFTER_VC_CODE = '''    vc_html = _vc_html(vc_res or [])

    # ── 뉴스 탭 렌더링 ────────────────────────────────────────────
    def _news_tab_html(nr):
        BORDER = "#1e2535"; BG_H = "#0a0e17"; PANEL = "#0d1119"; CARD = "#111620"
        C_G = "#15b98a"; C_R = "#f87171"; C_M = "#64748b"; C_T = "#e2e8f0"
        C_B = "#4d9eff"; C_Y = "#f5c842"; C_P = "#a78bfa"

        if not nr:
            return f\'<div style="padding:40px;text-align:center;color:{C_M}">뉴스 데이터 없음</div>\'

        def _badge(market):
            if market == "국내ETF":
                return (f\'<span style="background:rgba(77,158,255,.15);color:{C_B};\'
                        f\'padding:2px 8px;border-radius:4px;font-size:10px;font-weight:700">국내ETF</span>\')
            elif market == "국내":
                return (f\'<span style="background:rgba(167,139,250,.15);color:{C_P};\'
                        f\'padding:2px 8px;border-radius:4px;font-size:10px;font-weight:700">국내</span>\')
            else:
                return (f\'<span style="background:rgba(245,200,66,.15);color:{C_Y};\'
                        f\'padding:2px 8px;border-radius:4px;font-size:10px;font-weight:700">미국</span>\')

        def _news_list(items, section_label, accent):
            if not items:
                return (f\'<div style="padding:12px 16px;color:{C_M};font-size:12px">\'
                        f\'{section_label} 뉴스 없음 (날짜 범위 내)</div>\')
            html = (f\'<div style="font-size:11px;font-weight:700;letter-spacing:.5px;\'
                    f\'text-transform:uppercase;color:{C_M};padding:10px 16px 6px">\'
                    f\'{section_label}</div>\')
            for i, n in enumerate(items):
                title     = n.get("title","")
                publisher = n.get("publisher","")
                date_str  = n.get("date","")
                link      = n.get("link","")
                summary   = n.get("summary","")
                is_minor  = n.get("minor", False)
                pub_color = C_M if is_minor else accent

                title_html = (
                    f\'<a href="{link}" target="_blank" rel="noopener" \'
                    f\'style="color:{C_T};text-decoration:none;font-weight:500;\'
                    f\'font-size:13px;line-height:1.4;display:block">\'
                    f\'{title}</a>\'
                ) if link else f\'<span style="color:{C_T};font-size:13px">{title}</span>\'

                summary_html = (
                    f\'<div style="color:{C_M};font-size:11px;margin-top:4px;line-height:1.5">\'
                    f\'{summary}</div>\'
                ) if summary else ""

                is_last = (i == len(items) - 1)
                border_b = "" if is_last else f"border-bottom:1px solid {BORDER};"

                html += (
                    f\'<div style="padding:12px 16px;{border_b}">\'
                    f\'{title_html}\'
                    f\'{summary_html}\'
                    f\'<div style="margin-top:5px">\'
                    f\'<span style="font-size:10px;color:{pub_color}">{publisher}</span>\'
                    f\'<span style="font-size:10px;color:{C_M}"> · {date_str}</span>\'
                    f\'</div></div>\'
                )
            return html

        html = ""
        for ticker, info in nr.items():
            name    = info.get("name", ticker)
            market  = info.get("market", "")
            ko_news = info.get("ko_news", [])
            en_news = info.get("en_news", [])
            action  = info.get("action", {})
            a_label  = action.get("label", "—")
            a_detail = action.get("detail", "")
            a_color  = action.get("color", C_M)

            has_news = bool(ko_news or en_news)

            html += (
                f\'<div style="margin-bottom:20px;border-radius:10px;\'
                f\'border:1px solid {BORDER};overflow:hidden">\'

                # 헤더
                f\'<div style="display:flex;align-items:center;justify-content:space-between;\'
                f\'padding:12px 16px;background:{BG_H};border-bottom:1px solid {BORDER}">\'
                f\'<div style="display:flex;align-items:center;gap:10px">\'
                f\'<span style="font-weight:700;font-size:15px;color:{C_T}">{ticker}</span>\'
                f\'<span style="font-size:12px;color:{C_M}">{name}</span>\'
                f\'{"&nbsp;" + _badge(market)}\'>\'
                f\'</div>\'
                f\'<div style="text-align:right">\'
                f\'<span style="font-size:13px;font-weight:700;color:{a_color}">{a_label}</span>\'
                f\'<br><span style="font-size:11px;color:{C_M}">{a_detail}</span>\'
                f\'</div></div>\'
            )

            if not has_news:
                html += (f\'<div style="padding:16px;color:{C_M};font-size:12px">\'
                         f\'뉴스 없음 (날짜 범위 내 결과 없음)</div>\')
            else:
                html += f\'<div style="display:grid;grid-template-columns:1fr 1fr;\'
                if market in ("국내", "국내ETF"):
                    # 국내 종목: 국내 뉴스 전체 + 해외 있으면 오른쪽
                    html += f\'min(100%,100%)">\'
                    html += f\'<div style="border-right:1px solid {BORDER}">\'
                    html += _news_list(ko_news, "🇰🇷 국내 뉴스", C_B)
                    html += f\'</div><div>\'
                    html += _news_list(en_news, "🌐 해외 뉴스", C_Y)
                    html += f\'</div>\'
                else:
                    # 미국 종목: 해외 왼쪽 / 국내(있으면) 오른쪽
                    html += f\'min(100%,100%)">\'
                    html += f\'<div style="border-right:1px solid {BORDER}">\'
                    html += _news_list(en_news, "🌐 해외 주요 뉴스", C_Y)
                    html += f\'</div><div>\'
                    html += _news_list(ko_news, "🇰🇷 국내 뉴스", C_B)
                    html += f\'</div>\'
                html += f\'</div>\'  # grid

            html += f\'</div>\'  # card

        return html

    news_html = _news_tab_html(news_res or {})'''

# ═══════════════════════════════════════════════════════════════════
# 패치 적용
# ═══════════════════════════════════════════════════════════════════
checks = [
    ("daily_job def",     OLD_DAILY_JOB_DEF in src),
    ("html_call",         OLD_HTML_CALL in src),
    ("func_sig",          OLD_FUNC_SIG in src),
    ("tab_btns",          OLD_TAB_BTNS in src),
    ("after_vc_tab",      OLD_AFTER_VC_TAB in src),
    ("after_vc_code",     OLD_AFTER_VC_CODE in src),
]
all_ok = True
for name, found in checks:
    print(f"[{'OK' if found else 'MISS'}] {name}")
    if not found: all_ok = False

if not all_ok:
    sys.exit(1)

src = src.replace(OLD_DAILY_JOB_DEF, NEW_DAILY_JOB_DEF, 1)
src = src.replace(OLD_HTML_CALL,     NEW_HTML_CALL,     1)
src = src.replace(OLD_FUNC_SIG,      NEW_FUNC_SIG,      1)
src = src.replace(OLD_TAB_BTNS,      NEW_TAB_BTNS,      1)
src = src.replace(OLD_AFTER_VC_TAB,  NEW_AFTER_VC_TAB,  1)
src = src.replace(OLD_AFTER_VC_CODE, NEW_AFTER_VC_CODE, 1)

nb['cells'][0]['source'] = [src]
with open(NB_PATH, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
print("patch27 done")
