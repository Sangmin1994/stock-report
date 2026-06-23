"""
patch26_industry_earn_fix.py
1) 상세 산업별 현황: RSI + 1w/1m/3m/6m 수익률 컬럼 추가
   (각 산업의 대표 종목 ETF 코드로 sector_data에서 조회)
2) 분기 실적: 모든 종목이 공통 분기 컬럼을 공유하는 단일 테이블로 재편
"""
import json, sys

NB_PATH = r"C:\Users\Sangmin\Desktop\Stock\scanner_portpolio_v4.ipynb"

with open(NB_PATH, 'r', encoding='utf-8') as f:
    nb = json.load(f)
src = ''.join(nb['cells'][0]['source'])

# ═══════════════════════════════════════════════════════════════════
# 1. _industry_table 교체 (RSI + 수익률 컬럼 포함)
# ═══════════════════════════════════════════════════════════════════
OLD_IND = '''    # ── 상세 산업별 현황 ──────────────────────────────────────────
    def _industry_table(scan_r, port_r):
        from collections import defaultdict
        BORDER = "#1e2535"; BG_H = "#0a0e17"; C_M = "#64748b"; C_T = "#e2e8f0"
        C_B = "#4d9eff"; C_G = "#15b98a"; C_Y = "#f5c842"
        TH = (f\'padding:9px 14px;font-size:11px;font-weight:600;letter-spacing:.7px;\'
              f\'text-transform:uppercase;color:{C_M};border-bottom:1px solid {BORDER};\'
              f\'background:{BG_H};text-align:left\')
        TD = f\'padding:9px 14px;font-size:13px;border-bottom:1px solid {BORDER};color:{C_T}\'
        TD_R = TD + \';text-align:right\'

        ind_scan = defaultdict(list)
        for r in (scan_r or []):
            ind_scan[r.get("industry","") or "미분류"].append(r["ticker"])
        ind_port = defaultdict(list)
        for r in (port_r or []):
            ind_port[r.get("industry","") or "미분류"].append(r["ticker"])

        all_inds = sorted(set(list(ind_scan.keys()) + list(ind_port.keys())))
        if not all_inds:
            return f\'<div style="padding:24px;text-align:center;color:{C_M}">산업 데이터 없음</div>\'

        rows = ""
        for ind in all_inds:
            sc = ind_scan.get(ind, [])
            pc = ind_port.get(ind, [])
            all_t = sorted(set(sc + pc))
            sc_html = (f\'<span style="color:{C_B}">{len(sc)}종목</span>\' if sc
                       else f\'<span style="color:{C_M}">—</span>\')
            pc_html = (f\'<span style="color:{C_G}">{len(pc)}종목</span>\' if pc
                       else f\'<span style="color:{C_M}">—</span>\')
            tickers_html = " ".join(
                f\'<span style="background:rgba(77,158,255,.12);color:{C_B};\'
                f\'padding:1px 6px;border-radius:3px;font-size:11px">{t}</span>\'
                for t in all_t
            )
            rows += (f\'<tr>\'
                     f\'<td style="{TD}">{ind}</td>\'
                     f\'<td style="{TD_R}">{sc_html}</td>\'
                     f\'<td style="{TD_R}">{pc_html}</td>\'
                     f\'<td style="{TD}">{tickers_html}</td>\'
                     f\'</tr>\')
        return (
            f\'<div style="overflow-x:auto;border-radius:8px;border:1px solid {BORDER}">\'
            f\'<table style="width:100%;border-collapse:collapse">\'
            f\'<thead><tr>\'
            f\'<th style="{TH}">세부 산업</th>\'
            f\'<th style="{TH}" style="text-align:right">매수신호</th>\'
            f\'<th style="{TH}" style="text-align:right">보유중</th>\'
            f\'<th style="{TH}">종목</th>\'
            f\'</tr></thead><tbody>{rows}</tbody></table></div>\'
        )
    industry_html = _industry_table(scan_res, port_res)'''

NEW_IND = '''    # ── 상세 산업별 현황 (RSI + 수익률 포함) ─────────────────────
    def _industry_table(scan_r, port_r, s_map, s_data):
        from collections import defaultdict
        BORDER = "#1e2535"; BG_H = "#0a0e17"; C_M = "#64748b"; C_T = "#e2e8f0"
        C_B = "#4d9eff"; C_G = "#15b98a"; C_Y = "#f5c842"; C_R = "#f87171"
        TH = (f\'padding:9px 12px;font-size:10px;font-weight:600;letter-spacing:.6px;\'
              f\'text-transform:uppercase;color:{C_M};border-bottom:1px solid {BORDER};\'
              f\'background:{BG_H};text-align:left\')
        TH_R = TH + \';text-align:right\'
        TD = f\'padding:9px 12px;font-size:12px;border-bottom:1px solid {BORDER};color:{C_T}\'
        TD_R = TD + \';text-align:right\'

        def _chg(v):
            if v is None:
                return f\'<span style="color:{C_M}">—</span>\'
            try:
                v = float(v)
                c = C_G if v > 0 else (C_R if v < 0 else C_M)
                s = "+" if v > 0 else ""
                return f\'<span style="color:{c}">{s}{v:.1f}%</span>\'
            except:
                return f\'<span style="color:{C_M}">—</span>\'

        # 종목 → ETF 코드 매핑 (신포맷 sector_map에서)
        def _etf_for_tickers(tickers):
            for tk in tickers:
                val = (s_map or {}).get(str(tk).upper(), {})
                if isinstance(val, dict):
                    etf = val.get("sector", "")
                    if etf and etf in (s_data or {}):
                        return etf
            return None

        ind_scan = defaultdict(list)
        for r in (scan_r or []):
            ind_scan[r.get("industry","") or "미분류"].append(r["ticker"])
        ind_port = defaultdict(list)
        for r in (port_r or []):
            ind_port[r.get("industry","") or "미분류"].append(r["ticker"])

        all_inds = sorted(set(list(ind_scan.keys()) + list(ind_port.keys())))
        if not all_inds:
            return f\'<div style="padding:24px;text-align:center;color:{C_M}">산업 데이터 없음</div>\'

        rows = ""
        for ind in all_inds:
            sc = ind_scan.get(ind, [])
            pc = ind_port.get(ind, [])
            all_t = sorted(set(sc + pc))

            sc_html = (f\'<span style="color:{C_B}">{len(sc)}종목</span>\' if sc
                       else f\'<span style="color:{C_M}">—</span>\')
            pc_html = (f\'<span style="color:{C_G}">{len(pc)}종목</span>\' if pc
                       else f\'<span style="color:{C_M}">—</span>\')
            tickers_html = " ".join(
                f\'<span style="background:rgba(77,158,255,.12);color:{C_B};\'
                f\'padding:1px 5px;border-radius:3px;font-size:11px">{t}</span>\'
                for t in all_t
            )

            # 섹터 ETF 데이터 조회
            etf = _etf_for_tickers(all_t)
            if etf and s_data and etf in s_data:
                sd = s_data[etf]
                rsi_v = sd.get("rsi") or 0
                rsi_c = C_G if rsi_v < 40 else (C_R if rsi_v > 70 else C_T)
                rsi_html = f\'<span style="color:{rsi_c}">{rsi_v:.0f}</span>\'
                w1  = _chg(sd.get("ret_1w"))
                m1  = _chg(sd.get("ret_1m"))
                m3  = _chg(sd.get("ret_3m"))
                m6  = _chg(sd.get("ret_6m"))
                etf_label = f\'<span style="color:{C_M};font-size:10px">{etf}</span>\'
            else:
                rsi_html = f\'<span style="color:{C_M}">—</span>\'
                w1 = m1 = m3 = m6 = f\'<span style="color:{C_M}">—</span>\'
                etf_label = f\'<span style="color:{C_M};font-size:10px">—</span>\'

            rows += (
                f\'<tr>\'
                f\'<td style="{TD}">{ind}<br>{etf_label}</td>\'
                f\'<td style="{TD_R}">{sc_html}</td>\'
                f\'<td style="{TD_R}">{pc_html}</td>\'
                f\'<td style="{TD_R}">{rsi_html}</td>\'
                f\'<td style="{TD_R}">{w1}</td>\'
                f\'<td style="{TD_R}">{m1}</td>\'
                f\'<td style="{TD_R}">{m3}</td>\'
                f\'<td style="{TD_R}">{m6}</td>\'
                f\'<td style="{TD}">{tickers_html}</td>\'
                f\'</tr>\'
            )
        return (
            f\'<div style="overflow-x:auto;border-radius:8px;border:1px solid {BORDER}">\'
            f\'<table style="width:100%;border-collapse:collapse">\'
            f\'<thead><tr>\'
            f\'<th style="{TH}">세부 산업 / ETF</th>\'
            f\'<th style="{TH_R}">매수신호</th>\'
            f\'<th style="{TH_R}">보유중</th>\'
            f\'<th style="{TH_R}">RSI</th>\'
            f\'<th style="{TH_R}">1주</th>\'
            f\'<th style="{TH_R}">1개월</th>\'
            f\'<th style="{TH_R}">분기</th>\'
            f\'<th style="{TH_R}">반기</th>\'
            f\'<th style="{TH}">종목</th>\'
            f\'</tr></thead><tbody>{rows}</tbody></table></div>\'
        )
    industry_html = _industry_table(scan_res, port_res, sector_map, sector_data)'''

# ═══════════════════════════════════════════════════════════════════
# 2. _earn_table 교체: 공통 분기 컬럼 단일 테이블
# ═══════════════════════════════════════════════════════════════════
OLD_EARN = '''    def _earn_table(earn):
        BORDER = "#1e2535"; BG_H = "#0a0e17"; PANEL = "#0d1119"
        C_G = "#15b98a"; C_R = "#f87171"; C_M = "#64748b"; C_T = "#e2e8f0"; C_B = "#4d9eff"
        if not earn:
            return f\'<div style="padding:32px;text-align:center;color:{C_M}">실적 데이터 없음</div>\'

        def _rev_str(v):
            """rev는 백만달러 단위 → $XB 또는 $XM으로 표시"""
            if v is None:
                return "—"
            try:
                v = float(v)
                if v == 0:
                    return "—"
                if abs(v) >= 1000:
                    return f"${v/1000:.1f}B"
                return f"${v:.0f}M"
            except:
                return "—"

        def _chg_str(cur, prev):
            """전분기 대비 변동률 계산"""
            if cur is None or prev is None or prev == 0:
                return ""
            try:
                pct = (float(cur) - float(prev)) / abs(float(prev)) * 100
                c = C_G if pct > 0 else C_R
                s = "+" if pct > 0 else ""
                return f\'<span style="font-size:10px;color:{c}"> {s}{pct:.1f}%</span>\'
            except:
                return ""

        def _opm_str(v, prev_v):
            if v is None:
                return f\'<span style="color:{C_M}">—</span>\'
            try:
                v = float(v)
                c = C_G if v >= 0 else C_R
                chg = _chg_str(v, prev_v) if prev_v is not None else ""
                return f\'<span style="color:{c}">{v:+.1f}%{chg}</span>\'
            except:
                return f\'<span style="color:{C_M}">—</span>\'

        TH_S = (f\'padding:7px 10px;font-size:10px;font-weight:600;letter-spacing:.5px;\'
                f\'text-transform:uppercase;color:{C_M};border-bottom:1px solid {BORDER};\'
                f\'background:{BG_H};text-align:right\')
        TH_L = TH_S + \';text-align:left\'
        TD_S = f\'padding:7px 10px;font-size:12px;border-bottom:1px solid {BORDER};color:{C_T};text-align:right\'
        TD_L = TD_S + \';text-align:left\'

        blocks = ""
        for tk, d in earn.items():
            try:
                company = str(d.get("company", d.get("name", tk)))
                quarters = d.get("quarters", [])
                if not quarters:
                    continue
                # 최근 8분기
                qs = quarters[:8]

                header_cells = (
                    f\'<th style="{TH_L}">티커</th>\'
                    f\'<th style="{TH_L}">종목명</th>\'
                    + "".join(f\'<th style="{TH_S}">{q.get("label","")}</th>\' for q in qs)
                )
                # 매출 행
                rev_vals = [q.get("rev") for q in qs]
                rev_cells = "".join(
                    f\'<td style="{TD_S}">{_rev_str(rev_vals[j])}{_chg_str(rev_vals[j], rev_vals[j+1]) if j+1 < len(rev_vals) else ""}</td>\'
                    for j in range(len(qs))
                )
                # 영업이익률 행
                opm_vals = [q.get("op_margin") for q in qs]
                opm_cells = "".join(
                    f\'<td style="{TD_S}">{_opm_str(opm_vals[j], opm_vals[j+1] if j+1<len(opm_vals) else None)}</td>\'
                    for j in range(len(qs))
                )

                block = (
                    f\'<div style="margin-bottom:20px;border-radius:8px;border:1px solid {BORDER};overflow-x:auto">\'
                    f\'<table style="width:100%;border-collapse:collapse">\'
                    f\'<thead><tr>{header_cells}</tr></thead>\'
                    f\'<tbody>\'
                    f\'<tr>\'
                    f\'<td style="{TD_L};font-weight:700;color:{C_B};vertical-align:top" rowspan="2">{tk}</td>\'
                    f\'<td style="{TD_L};color:{C_M};font-size:11px;vertical-align:top" rowspan="2">{company}</td>\'
                    + rev_cells +
                    f\'</tr>\'
                    f\'<tr>\'
                    + opm_cells +
                    f\'</tr>\'
                    f\'</tbody></table>\'
                    f\'<div style="padding:4px 10px 6px;font-size:10px;color:{C_M}">\'
                    f\'위: 매출 / 아래: 영업이익률  |  괄호: 전분기 대비 변동\'
                    f\'</div></div>\'
                )
                blocks += block
            except Exception as e:
                blocks += f\'<div style="color:{C_R};padding:8px">{tk} 오류: {e}</div>\'

        if not blocks:
            return f\'<div style="padding:32px;text-align:center;color:{C_M}">실적 데이터 없음</div>\'
        return blocks

    earn_html = _earn_table(earn_res or {})'''

NEW_EARN = '''    def _earn_table(earn):
        BORDER = "#1e2535"; BG_H = "#0a0e17"
        C_G = "#15b98a"; C_R = "#f87171"; C_M = "#64748b"; C_T = "#e2e8f0"; C_B = "#4d9eff"
        if not earn:
            return f\'<div style="padding:32px;text-align:center;color:{C_M}">실적 데이터 없음</div>\'

        def _rev_str(v):
            if v is None: return "—"
            try:
                v = float(v)
                if v == 0: return "—"
                return f"${v/1000:.1f}B" if abs(v) >= 1000 else f"${v:.0f}M"
            except: return "—"

        def _qoq(cur, nxt):
            """전분기 대비 변동률 (cur=최신, nxt=한분기 전)"""
            if cur is None or nxt is None or nxt == 0: return ""
            try:
                pct = (float(cur) - float(nxt)) / abs(float(nxt)) * 100
                c = C_G if pct > 0 else C_R
                s = "+" if pct > 0 else ""
                return f\'<br><span style="font-size:10px;color:{c}">{s}{pct:.1f}%</span>\'
            except: return ""

        def _opm(v, nxt_v):
            if v is None: return f\'<span style="color:{C_M}">—</span>\'
            try:
                v = float(v)
                c = C_G if v >= 0 else C_R
                chg = _qoq(v, nxt_v) if nxt_v is not None else ""
                return f\'<span style="color:{c}">{v:+.1f}%{chg}</span>\'
            except: return f\'<span style="color:{C_M}">—</span>\'

        # ── 전체 분기 레이블 수집 (최근 8개) ──────────────────────
        all_labels_set = set()
        ticker_data = {}
        for tk, d in earn.items():
            qs = d.get("quarters", [])[:8]
            if not qs:
                continue
            ticker_data[tk] = {"company": str(d.get("company", tk)), "quarters": qs}
            for q in qs:
                lbl = q.get("label","")
                if lbl:
                    all_labels_set.add(lbl)

        if not ticker_data:
            return f\'<div style="padding:32px;text-align:center;color:{C_M}">실적 데이터 없음</div>\'

        # 분기 레이블 정렬: YYQ# 형식 → 내림차순 (26Q2 > 26Q1 > 25Q4 ...)
        def _q_sort_key(lbl):
            try:
                yr = int(lbl[:2]); qn = int(lbl[-1])
                return yr * 10 + qn
            except: return 0
        col_labels = sorted(all_labels_set, key=_q_sort_key, reverse=True)[:8]

        TH = (f\'padding:8px 12px;font-size:11px;font-weight:600;letter-spacing:.5px;\'
              f\'text-transform:uppercase;color:{C_M};border-bottom:1px solid {BORDER};\'
              f\'background:{BG_H};text-align:right;white-space:nowrap\')
        TH_L = TH + \';text-align:left\'
        THL  = TH  + \';text-align:center\'
        TD  = f\'padding:8px 12px;font-size:12px;border-bottom:1px solid {BORDER};color:{C_T};text-align:right;white-space:nowrap\'
        TD_L = TD + \';text-align:left\'
        TD_IT = TD + \';font-size:11px;color:{C_M};text-align:left\'

        header = (
            f\'<th style="{TH_L}">티커</th>\'
            f\'<th style="{TH_L}">종목명</th>\'
            f\'<th style="{THL}">항목</th>\'
            + "".join(f\'<th style="{TH}">{lbl}</th>\' for lbl in col_labels)
        )

        rows = ""
        for tk, info in ticker_data.items():
            qs_by_lbl = {q.get("label",""): q for q in info["quarters"]}
            rev_vals = [qs_by_lbl.get(lbl, {}).get("rev") for lbl in col_labels]
            opm_vals = [qs_by_lbl.get(lbl, {}).get("op_margin") for lbl in col_labels]
            n = len(col_labels)

            rev_cells = "".join(
                f\'<td style="{TD}">{_rev_str(rev_vals[j])}{_qoq(rev_vals[j], rev_vals[j+1]) if j+1<n and rev_vals[j] is not None else ""}</td>\'
                for j in range(n)
            )
            opm_cells = "".join(
                f\'<td style="{TD}">{_opm(opm_vals[j], opm_vals[j+1] if j+1<n else None)}</td>\'
                for j in range(n)
            )

            rows += (
                f\'<tr>\'
                f\'<td style="{TD_L};font-weight:700;color:{C_B}" rowspan="2">{tk}</td>\'
                f\'<td style="{TD_L};font-size:11px;color:{C_M}" rowspan="2">{info["company"]}</td>\'
                f\'<td style="{TD_IT}">매출</td>\'
                + rev_cells +
                f\'</tr><tr>\'
                f\'<td style="{TD_IT}">영업이익률</td>\'
                + opm_cells +
                f\'</tr>\'
            )

        return (
            f\'<div style="overflow-x:auto;border-radius:8px;border:1px solid {BORDER}">\'
            f\'<table style="width:100%;border-collapse:collapse">\'
            f\'<thead><tr>{header}</tr></thead>\'
            f\'<tbody>{rows}</tbody></table>\'
            f\'<div style="padding:5px 12px 8px;font-size:10px;color:{C_M}">\'
            f\'매출: 백만달러(M)/십억달러(B) 단위 · 작은 숫자: 전분기 대비 변동률\'
            f\'</div></div>\'
        )

    earn_html = _earn_table(earn_res or {})'''

# ── 패치 적용 ──────────────────────────────────────────────────────
checks = [
    ("industry_table", OLD_IND in src),
    ("earn_table",     OLD_EARN in src),
]
all_ok = True
for name, found in checks:
    print(f"[{'OK' if found else 'MISS'}] {name}")
    if not found: all_ok = False

if not all_ok:
    sys.exit(1)

src = src.replace(OLD_IND,  NEW_IND,  1)
src = src.replace(OLD_EARN, NEW_EARN, 1)

nb['cells'][0]['source'] = [src]
with open(NB_PATH, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
print("patch26 done")
