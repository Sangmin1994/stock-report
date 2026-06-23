"""
patch28_ux_fixes.py
1) 탭 sticky (틀 고정) - 스크롤해도 탭바 고정
2) 상세 산업별 현황 컬럼 간격 여유롭게
3) 자산현황 + 포트폴리오 테이블에 전일 대비 증감률 컬럼 추가
   - run_portfolio_update()에 chg_1d 필드 추가
   - format_asset_overview_html / _port_table_unified에서 port_res lookup 사용
4) 뉴스 탭: 날짜 필터 완화 (3일) + 주요언론사 없으면 모두 표시
5) "뉴스에 팔아라" 철학 반영: 긍정 뉴스도 차익실현 권고
"""
import json, sys

NB_PATH = r"C:\Users\Sangmin\Desktop\Stock\scanner_portpolio_v4.ipynb"

with open(NB_PATH, 'r', encoding='utf-8') as f:
    nb = json.load(f)
src = ''.join(nb['cells'][0]['source'])

# ═══════════════════════════════════════════════════════════════════
# 1. 탭 sticky CSS
# ═══════════════════════════════════════════════════════════════════
OLD_TABS_CSS = '''.tabs { display: flex; gap: 4px; padding: 16px 32px 0;
        border-bottom: 1px solid var(--border); background: var(--surface); }'''

NEW_TABS_CSS = '''.tabs { display: flex; gap: 4px; padding: 16px 32px 0;
        border-bottom: 1px solid var(--border); background: var(--surface);
        position: sticky; top: 0; z-index: 100;
        box-shadow: 0 2px 12px rgba(0,0,0,.4); }'''

# ═══════════════════════════════════════════════════════════════════
# 2. 상세 산업별 현황 TH 패딩 & min-width 확장
# ═══════════════════════════════════════════════════════════════════
OLD_IND_TH = '''        TH = (f\'padding:9px 12px;font-size:10px;font-weight:600;letter-spacing:.6px;\'
              f\'text-transform:uppercase;color:{C_M};border-bottom:1px solid {BORDER};\'
              f\'background:{BG_H};text-align:left\')
        TH_R = TH + \';text-align:right\'
        TD = f\'padding:9px 12px;font-size:12px;border-bottom:1px solid {BORDER};color:{C_T}\'
        TD_R = TD + \';text-align:right\''''

NEW_IND_TH = '''        TH = (f\'padding:10px 18px;font-size:10px;font-weight:600;letter-spacing:.6px;\'
              f\'text-transform:uppercase;color:{C_M};border-bottom:1px solid {BORDER};\'
              f\'background:{BG_H};text-align:left;white-space:nowrap\')
        TH_R = TH + \';text-align:right\'
        TD = f\'padding:10px 18px;font-size:12px;border-bottom:1px solid {BORDER};color:{C_T}\'
        TD_R = TD + \';text-align:right;white-space:nowrap\''''

# ═══════════════════════════════════════════════════════════════════
# 3-A. run_portfolio_update: chg_1d 필드 추가
# ═══════════════════════════════════════════════════════════════════
OLD_CALC = '''            cur_price   = round(d_df["Close"].iloc[-1], 2)
            pnl_pct     = round((cur_price / buy_price - 1) * 100, 2)
            eval_amt    = round(cur_price * shares, 2)
            pnl_amt     = round(eval_amt - buy_price * shares, 2)'''

NEW_CALC = '''            cur_price   = round(d_df["Close"].iloc[-1], 2)
            prev_close  = d_df["Close"].iloc[-2] if len(d_df) >= 2 else cur_price
            chg_1d      = round((cur_price / prev_close - 1) * 100, 2) if prev_close else 0
            pnl_pct     = round((cur_price / buy_price - 1) * 100, 2)
            eval_amt    = round(cur_price * shares, 2)
            pnl_amt     = round(eval_amt - buy_price * shares, 2)'''

OLD_PORT_APPEND = '''                "status": status,
                "memo": memo,'''

NEW_PORT_APPEND = '''                "chg_1d": chg_1d,
                "status": status,
                "memo": memo,'''

# ═══════════════════════════════════════════════════════════════════
# 3-B. generate_html_report: port_res를 chg lookup으로 변환
# ═══════════════════════════════════════════════════════════════════
OLD_TODAY_STR = '''    today_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    sector_map = sector_map or {}'''

NEW_TODAY_STR = '''    today_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    sector_map = sector_map or {}
    # 포트폴리오 전일 대비 등락률 lookup {ticker: chg_1d}
    _chg_lookup = {r["ticker"]: r.get("chg_1d", None) for r in (port_res or [])}'''

# ═══════════════════════════════════════════════════════════════════
# 3-C. 자산현황 stock 헤더에 전일 컬럼 추가
# ═══════════════════════════════════════════════════════════════════
OLD_ASSET_HEADER = '''        header = (f\'<th style="{TH}">시장</th><th style="{TH}">종목명</th>\'
                  f\'<th style="{TH_R}">보유량</th>\'
                  f\'<th style="{TH_R}">평가금액</th>\'
                  f\'<th style="{TH_R}">손익</th>\'
                  f\'<th style="{TH_R}">손익률</th>\')
        stock_section = (
            _section_title("주식", C["purple"], _fmt_krw(stock))
            + _tbl_wrap(header, stock_rows)
        )'''

NEW_ASSET_HEADER = '''        header = (f\'<th style="{TH}">시장</th><th style="{TH}">종목명</th>\'
                  f\'<th style="{TH_R}">보유량</th>\'
                  f\'<th style="{TH_R}">평가금액</th>\'
                  f\'<th style="{TH_R}">전일대비</th>\'
                  f\'<th style="{TH_R}">손익</th>\'
                  f\'<th style="{TH_R}">손익률</th>\')
        stock_section = (
            _section_title("주식", C["purple"], _fmt_krw(stock))
            + _tbl_wrap(header, stock_rows)
        )'''

# ═══════════════════════════════════════════════════════════════════
# 3-D. 자산현황 stock_rows에 전일 등락 셀 추가
# ═══════════════════════════════════════════════════════════════════
OLD_ASSET_ROWS = '''        stock_rows += (
            f\'<tr>\'
            f\'<td style="{TD}">{badge}</td>\'
            f\'<td style="{TD};font-weight:600">{s["name"]}</td>\'
            f\'<td style="{TD_R}">{s["shares"]:,.0f}</td>\'
            f\'<td style="{TD_R};font-weight:600">{eval_disp}</td>\'
            f\'<td style="{TD_R}">{gain_html}</td>\'
            f\'<td style="{TD_R}">{pct_html}</td>\'
            f\'</tr>\'
        )'''

NEW_ASSET_ROWS = '''        # 전일 대비 등락
        _tk = s.get("ticker", s.get("name",""))
        _c1d = _chg_lookup.get(str(_tk).upper())
        if _c1d is not None:
            _cc = C["green"] if _c1d > 0 else (C["red"] if _c1d < 0 else C["muted"])
            _cs = "+" if _c1d > 0 else ""
            chg1d_html = f\'<span style="color:{_cc}">{_cs}{_c1d:.1f}%</span>\'
        else:
            chg1d_html = f\'<span style="color:{C[\"muted\"]}">—</span>\'
        stock_rows += (
            f\'<tr>\'
            f\'<td style="{TD}">{badge}</td>\'
            f\'<td style="{TD};font-weight:600">{s["name"]}</td>\'
            f\'<td style="{TD_R}">{s["shares"]:,.0f}</td>\'
            f\'<td style="{TD_R};font-weight:600">{eval_disp}</td>\'
            f\'<td style="{TD_R}">{chg1d_html}</td>\'
            f\'<td style="{TD_R}">{gain_html}</td>\'
            f\'<td style="{TD_R}">{pct_html}</td>\'
            f\'</tr>\'
        )'''

# ═══════════════════════════════════════════════════════════════════
# 3-E. 포트폴리오 탭 _port_table_unified: 전일 컬럼 추가
# ═══════════════════════════════════════════════════════════════════
OLD_PORT_TBL_HEADER = '''        h = """<div class="tbl-wrap"><table>
<thead><tr>
<th>시장</th><th>종목명</th><th>보유량</th>
<th>평가금액</th><th>손익</th><th>손익률</th>
</tr></thead><tbody>"""'''

NEW_PORT_TBL_HEADER = '''        h = """<div class="tbl-wrap"><table>
<thead><tr>
<th>시장</th><th>종목명</th><th>보유량</th>
<th>평가금액</th><th>전일대비</th><th>손익</th><th>손익률</th>
</tr></thead><tbody>"""'''

OLD_PORT_TBL_ROW = '''            h += f"""<tr>
<td>{badge}</td>
<td><b>{s.get(\'name\',\'\')}</b></td>
<td style="text-align:right">{s.get(\'shares\',0):,.0f}</td>
<td style="text-align:right;font-weight:600">{eval_disp}</td>
<td style="text-align:right">{gain_html}</td>
<td style="text-align:right">{pct_html}</td>
</tr>"""'''

NEW_PORT_TBL_ROW = '''            # 전일 대비
            _tk2 = s.get("ticker", s.get("name",""))
            _c2 = _chg_lookup.get(str(_tk2).upper())
            if _c2 is not None:
                _cc2 = "#15b98a" if _c2 > 0 else ("#f87171" if _c2 < 0 else "#64748b")
                _cs2 = "+" if _c2 > 0 else ""
                chg1d2 = f\'<span style="color:{_cc2}">{_cs2}{_c2:.1f}%</span>\'
            else:
                chg1d2 = \'<span style="color:#64748b">—</span>\'
            h += f"""<tr>
<td>{badge}</td>
<td><b>{s.get(\'name\',\'\')}</b></td>
<td style="text-align:right">{s.get(\'shares\',0):,.0f}</td>
<td style="text-align:right;font-weight:600">{eval_disp}</td>
<td style="text-align:right">{chg1d2}</td>
<td style="text-align:right">{gain_html}</td>
<td style="text-align:right">{pct_html}</td>
</tr>"""'''

# ═══════════════════════════════════════════════════════════════════
# 4. 뉴스 날짜 필터 완화 + "뉴스에 팔아라" 철학 반영
# ═══════════════════════════════════════════════════════════════════
OLD_DATES = '''    # 허용 날짜 범위: 전날 ~ 당일 (KST)
    allowed_dates = {target_date - timedelta(days=1), target_date}'''

NEW_DATES = '''    # 허용 날짜 범위: 최근 3일 (KST) — 주말/공휴일 고려
    allowed_dates = {target_date - timedelta(days=i) for i in range(3)}'''

OLD_SENTIMENT = '''    def _sentiment(news_list):
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
            return {"label": "⚖ 중립", "detail": "현 포지션 유지", "color": "#64748b"}'''

NEW_SENTIMENT = '''    def _sentiment(news_list):
        """
        "뉴스에 팔아라" 철학:
        - 호재 뉴스 = 이미 선반영 → 차익실현 타이밍
        - 악재 뉴스 = 추가 하락 위험 → 손절/비중축소
        - 중립 = 관망
        """
        score = 0
        for n in news_list:
            text = (n.get("title","") + " " + n.get("summary","")).lower()
            for kw in POSITIVE_KW:
                if kw in text: score += 1
            for kw in NEGATIVE_KW:
                if kw in text: score -= 1
        if score >= 3:
            return {"label": "📰 강한 호재", "detail": "뉴스에 팔아라 — 차익실현 적극 검토", "color": "#f5c842"}
        elif score == 2:
            return {"label": "📰 호재 뉴스", "detail": "뉴스에 팔아라 — 일부 차익실현 검토", "color": "#fb923c"}
        elif score == 1:
            return {"label": "🟡 약 긍정", "detail": "관망 / 목표가 근접 시 차익실현", "color": "#94a3b8"}
        elif score == -1:
            return {"label": "🟠 약 악재", "detail": "손절선 점검 / 비중 축소 검토", "color": "#fb923c"}
        elif score <= -2:
            return {"label": "📉 악재 뉴스", "detail": "손절 또는 비중 축소 — 추가 하락 대비", "color": "#f87171"}
        else:
            return {"label": "⚖ 중립", "detail": "현 포지션 유지 / 다음 뉴스 모니터링", "color": "#64748b"}'''

# 뉴스 날짜 필터 로직도 개선: pub_ts 없어도 포함 + 주요언론사 없으면 모두 허용
OLD_NEWS_LOOP = '''        for item in raw_news:
            # 날짜 필터 (KST 기준)
            pub_ts = item.get("providerPublishTime") or 0
            if pub_ts:
                pub_date = datetime.fromtimestamp(pub_ts, tz=KST).date()
                # 날짜 필터링
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
                en_news.append(news_obj)'''

NEW_NEWS_LOOP = '''        en_major, en_minor = [], []
        for item in raw_news:
            # 날짜 필터 (KST 기준) — pub_ts 없으면 통과
            pub_ts = item.get("providerPublishTime") or 0
            date_str = ""
            if pub_ts:
                try:
                    pub_date = datetime.fromtimestamp(pub_ts, tz=KST).date()
                    date_str = datetime.fromtimestamp(pub_ts, tz=KST).strftime("%m/%d %H:%M")
                    if pub_date not in allowed_dates:
                        continue
                except Exception:
                    pass

            title     = (item.get("title") or "").strip()
            publisher = (item.get("publisher") or
                         item.get("source") or "").strip()
            link      = item.get("link") or item.get("url") or ""
            summary   = (item.get("summary") or
                         item.get("description") or "")[:200]
            pub_lower = publisher.lower()

            if not title:
                continue

            news_obj = {
                "title":     title,
                "publisher": publisher,
                "link":      link,
                "summary":   summary,
                "date":      date_str,
            }

            is_korean   = any(kw in pub_lower for kw in KO_PUBLISHERS)
            is_major    = any(kw in pub_lower for kw in MAJOR_INTL)

            if is_korean and len(ko_news) < 5:
                ko_news.append(news_obj)
            elif not is_korean:
                if is_major:
                    en_major.append(news_obj)
                else:
                    news_obj["minor"] = True
                    en_minor.append(news_obj)

        # 주요 언론사 우선, 부족하면 기타로 채움
        en_news = (en_major + en_minor)[:5]'''

# ═══════════════════════════════════════════════════════════════════
# 패치 적용
# ═══════════════════════════════════════════════════════════════════
checks = [
    ("tabs_css",          OLD_TABS_CSS in src),
    ("ind_th",            OLD_IND_TH in src),
    ("calc",              OLD_CALC in src),
    ("port_append",       OLD_PORT_APPEND in src),
    ("today_str",         OLD_TODAY_STR in src),
    ("asset_header",      OLD_ASSET_HEADER in src),
    ("asset_rows",        OLD_ASSET_ROWS in src),
    ("port_tbl_header",   OLD_PORT_TBL_HEADER in src),
    ("port_tbl_row",      OLD_PORT_TBL_ROW in src),
    ("dates",             OLD_DATES in src),
    ("sentiment",         OLD_SENTIMENT in src),
    ("news_loop",         OLD_NEWS_LOOP in src),
]
all_ok = True
for name, found in checks:
    print(f"[{'OK' if found else 'MISS'}] {name}")
    if not found: all_ok = False

if not all_ok:
    sys.exit(1)

src = src.replace(OLD_TABS_CSS,        NEW_TABS_CSS,        1)
src = src.replace(OLD_IND_TH,          NEW_IND_TH,          1)
src = src.replace(OLD_CALC,            NEW_CALC,            1)
src = src.replace(OLD_PORT_APPEND,     NEW_PORT_APPEND,     1)
src = src.replace(OLD_TODAY_STR,       NEW_TODAY_STR,       1)
src = src.replace(OLD_ASSET_HEADER,    NEW_ASSET_HEADER,    1)
src = src.replace(OLD_ASSET_ROWS,      NEW_ASSET_ROWS,      1)
src = src.replace(OLD_PORT_TBL_HEADER, NEW_PORT_TBL_HEADER, 1)
src = src.replace(OLD_PORT_TBL_ROW,    NEW_PORT_TBL_ROW,    1)
src = src.replace(OLD_DATES,           NEW_DATES,           1)
src = src.replace(OLD_SENTIMENT,       NEW_SENTIMENT,       1)
src = src.replace(OLD_NEWS_LOOP,       NEW_NEWS_LOOP,       1)

nb['cells'][0]['source'] = [src]
with open(NB_PATH, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
print("patch28 done")
