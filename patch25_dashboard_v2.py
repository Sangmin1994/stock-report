"""
patch25_dashboard_v2.py
1) 탭 순서: 자산현황 → 섹터 → 스캔결과 → 포트폴리오 → 분기실적
2) 분기실적: 최근 8분기 + 전분기 대비 변동량
3) 섹터탭 하단에 상세 산업별 현황 테이블 추가
4) 스캔탭 하단에 밸류에이션/펀더멘털 체크리스트 추가
5) 벨류체인 투자 현황 탭 추가
6) 분기실적 매출 단위 수정 ($0.0B → 올바른 값)
"""
import json, sys

NB_PATH = r"C:\Users\Sangmin\Desktop\Stock\scanner_portpolio_v4.ipynb"

with open(NB_PATH, 'r', encoding='utf-8') as f:
    nb = json.load(f)
src = ''.join(nb['cells'][0]['source'])

# ═══════════════════════════════════════════════════════════════════
# 1. 탭 버튼 순서 변경
# ═══════════════════════════════════════════════════════════════════
OLD_TABS = '''<div class="tabs">
  <button class="tab-btn active" data-tab="asset" onclick="switchTab('asset')">자산 현황</button>
  <button class="tab-btn" data-tab="scan" onclick="switchTab('scan')">스캔 결과</button>
  <button class="tab-btn" data-tab="port" onclick="switchTab('port')">포트폴리오</button>
  <button class="tab-btn" data-tab="earn" onclick="switchTab('earn')">분기 실적</button>
  <button class="tab-btn" data-tab="sector" onclick="switchTab('sector')">섹터</button>
</div>'''

NEW_TABS = '''<div class="tabs">
  <button class="tab-btn active" data-tab="asset" onclick="switchTab('asset')">자산 현황</button>
  <button class="tab-btn" data-tab="sector" onclick="switchTab('sector')">섹터</button>
  <button class="tab-btn" data-tab="scan" onclick="switchTab('scan')">스캔 결과</button>
  <button class="tab-btn" data-tab="port" onclick="switchTab('port')">포트폴리오</button>
  <button class="tab-btn" data-tab="earn" onclick="switchTab('earn')">분기 실적</button>
  <button class="tab-btn" data-tab="vc" onclick="switchTab('vc')">벨류체인</button>
</div>'''

# ═══════════════════════════════════════════════════════════════════
# 2. 섹터탭 + 스캔탭 + 실적탭 + VC탭 전체 교체
# ═══════════════════════════════════════════════════════════════════
OLD_TABS_CONTENT = '''<!-- TAB: 스캔 -->
<div id="tab-scan" class="tab-content">
  <div class="section">
    <div class="section-title">오늘의 스캔 결과</div>
    {scan_html}
  </div>
</div>

<!-- TAB: 포트폴리오 -->
<div id="tab-port" class="tab-content">
  <div class="section">
    <div class="section-title">포트폴리오 현황</div>
    {port_html}
  </div>
</div>

<!-- TAB: 실적 -->
<div id="tab-earn" class="tab-content">
  <div class="section">
    <div class="section-title">분기별 실적</div>
    {earn_html}
  </div>
</div>

<!-- TAB: 섹터 -->
<div id="tab-sector" class="tab-content">
  <div class="section">
    <div class="section-title">섹터 동향</div>
    {sector_html_content}
  </div>
</div>'''

NEW_TABS_CONTENT = '''<!-- TAB: 섹터 -->
<div id="tab-sector" class="tab-content">
  <div class="section">
    <div class="section-title">섹터 동향</div>
    {sector_html_content}
  </div>
  <div class="section">
    <div class="section-title">상세 산업별 현황</div>
    {industry_html}
  </div>
</div>

<!-- TAB: 스캔 -->
<div id="tab-scan" class="tab-content">
  <div class="section">
    <div class="section-title">오늘의 스캔 결과</div>
    {scan_html}
  </div>
  {scan_detail_html}
</div>

<!-- TAB: 포트폴리오 -->
<div id="tab-port" class="tab-content">
  <div class="section">
    <div class="section-title">포트폴리오 현황</div>
    {port_html}
  </div>
</div>

<!-- TAB: 실적 -->
<div id="tab-earn" class="tab-content">
  <div class="section">
    <div class="section-title">분기별 실적 (최근 8분기)</div>
    {earn_html}
  </div>
</div>

<!-- TAB: 벨류체인 -->
<div id="tab-vc" class="tab-content">
  <div class="section">
    <div class="section-title">벨류체인 투자 현황</div>
    {vc_html}
  </div>
</div>'''

# ═══════════════════════════════════════════════════════════════════
# 3. generate_html_report 함수 내 렌더 로직 추가
#    _earn_table, sector_html_content 바로 뒤에 새 변수들 추가
# ═══════════════════════════════════════════════════════════════════

OLD_HTML_ASSIGN = '''    sector_html_content = _sector_table(sector_data)'''

NEW_HTML_ASSIGN = '''    sector_html_content = _sector_table(sector_data)

    # ── 상세 산업별 현황 ──────────────────────────────────────────
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
    industry_html = _industry_table(scan_res, port_res)

    # ── 스캔 결과 상세 (밸류에이션 + 펀더멘털) ───────────────────
    def _scan_detail_html(scan_r):
        if not scan_r:
            return ""
        BORDER = "#1e2535"; BG_H = "#0a0e17"; PANEL = "#111620"
        C_G = "#15b98a"; C_R = "#f87171"; C_M = "#64748b"; C_T = "#e2e8f0"
        C_B = "#4d9eff"; C_Y = "#f5c842"; C_P = "#a78bfa"
        TH = (f\'padding:9px 14px;font-size:11px;font-weight:600;letter-spacing:.7px;\'
              f\'text-transform:uppercase;color:{C_M};border-bottom:1px solid {BORDER};\'
              f\'background:{BG_H};text-align:left\')
        TH_R = TH + \';text-align:right\'
        TD = f\'padding:9px 14px;font-size:13px;border-bottom:1px solid {BORDER};color:{C_T}\'
        TD_R = TD + \';text-align:right\'
        TD_S = TD + \';font-size:11px;color:{C_M}\'

        rows = ""
        for r in scan_r:
            tk = r.get("ticker","")
            fund_judge = str(r.get("fund_judge","—"))
            fund_risks = str(r.get("fund_risks","없음"))
            growth_grade = str(r.get("growth_grade","—"))
            growth_detail = str(r.get("growth_detail",""))
            growth_score = r.get("growth_score", 0) or 0
            iv_label = str(r.get("iv_label","N/A"))
            pcr_label = str(r.get("pcr_label","N/A"))
            vix_status = str(r.get("vix_status",""))
            tw_warning = str(r.get("tw_warning",""))

            # 펀더멘털 판정 색상
            fj_color = C_G if "✅" in fund_judge else (C_R if "❌" in fund_judge else C_M)
            gs_color = C_G if growth_score >= 7 else (C_Y if growth_score >= 5 else C_M)

            rows += (
                f\'<tr>\'
                f\'<td style="{TD};font-weight:700;color:{C_B}">{tk}</td>\'
                f\'<td style="{TD};color:{fj_color}">{fund_judge}</td>\'
                f\'<td style="{TD};font-size:11px;color:{C_M}">{fund_risks}</td>\'
                f\'<td style="{TD_R};color:{gs_color}">{growth_grade} ({growth_score}점)</td>\'
                f\'<td style="{TD};font-size:11px;color:{C_M}">{growth_detail[:60]}</td>\'
                f\'<td style="{TD_R}">{iv_label}</td>\'
                f\'<td style="{TD_R}">{pcr_label}</td>\'
                f\'<td style="{TD}">{vix_status}</td>\'
                f\'</tr>\'
            )
            if tw_warning:
                rows += (
                    f\'<tr><td style="{TD};color:{C_Y}" colspan="8">\'
                    f\'⚠ {tk} {tw_warning}</td></tr>\'
                )

        return (
            f\'<div class="section">\'
            f\'<div class="section-title" style="margin-top:0">밸류에이션 / 펀더멘털 체크리스트</div>\'
            f\'<div style="overflow-x:auto;border-radius:8px;border:1px solid {BORDER}">\'
            f\'<table style="width:100%;border-collapse:collapse">\'
            f\'<thead><tr>\'
            f\'<th style="{TH}">티커</th>\'
            f\'<th style="{TH}">펀더멘털</th>\'
            f\'<th style="{TH}">리스크 요인</th>\'
            f\'<th style="{TH_R}">성장 등급</th>\'
            f\'<th style="{TH}">성장 세부</th>\'
            f\'<th style="{TH_R}">IV</th>\'
            f\'<th style="{TH_R}">P/C Ratio</th>\'
            f\'<th style="{TH}">VIX</th>\'
            f\'</tr></thead><tbody>{rows}</tbody></table></div></div>\'
        )
    scan_detail_html = _scan_detail_html(scan_res)

    # ── 실적 테이블 재작성 (8분기 + QoQ) ────────────────────────'''

# ═══════════════════════════════════════════════════════════════════
# 4. _earn_table 함수 교체 (8분기 + QoQ)
# ═══════════════════════════════════════════════════════════════════
OLD_EARN_TABLE = '''    def _earn_table(earn):
        BORDER = "#1e2535"; BG_H = "#0a0e17"
        C_G = "#15b98a"; C_R = "#f87171"; C_M = "#64748b"; C_T = "#e2e8f0"
        TH = (f\'padding:9px 14px;font-size:11px;font-weight:600;letter-spacing:.7px;\'
              f\'text-transform:uppercase;color:{C_M};border-bottom:1px solid {BORDER};\'
              f\'background:{BG_H};text-align:left\')
        TH_R = TH + \';text-align:right\'
        TD   = f\'padding:9px 14px;font-size:13px;border-bottom:1px solid {BORDER};color:{C_T}\'
        TD_R = TD + \';text-align:right\'
        if not earn:
            return f\'<div style="padding:32px;text-align:center;color:{C_M}">실적 데이터 없음</div>\'
        try:
            rows_html = ""
            for tk, d in earn.items():
                try:
                    company  = str(d.get("company", d.get("name", tk)))
                    quarters = d.get("quarters", [])
                    if not quarters:
                        continue
                    q    = quarters[0]
                    rev  = q.get("rev")
                    op_m = q.get("op_margin")
                    rev_str = f"${float(rev)/1e9:.1f}B" if rev else "—"
                    if op_m is not None:
                        op_m_f = float(op_m)
                        op_c   = C_G if op_m_f >= 0 else C_R
                        op_str = f\'<span style="color:{op_c}">{op_m_f:+.1f}%</span>\'
                    else:
                        op_str = f\'<span style="color:{C_M}">—</span>\'
                    rows_html += (
                        f\'<tr>\'
                        f\'<td style="{TD}"><b>{tk}</b></td>\'
                        f\'<td style="{TD}">{company}</td>\'
                        f\'<td style="{TD}">{q.get("label","")}</td>\'
                        f\'<td style="{TD_R}">{rev_str}</td>\'
                        f\'<td style="{TD_R}">{op_str}</td>\'
                        f\'</tr>\'
                    )
                except Exception as row_e:
                    rows_html += (
                        f\'<tr><td style="{TD}" colspan="5" style="color:{C_R}">\'
                        f\'{tk} 오류: {row_e}</td></tr>\'
                    )
            if not rows_html:
                return f\'<div style="padding:32px;text-align:center;color:{C_M}">실적 데이터 없음</div>\'
            return (
                f\'<div style="overflow-x:auto;border-radius:8px;border:1px solid {BORDER}">\'
                f\'<table style="width:100%;border-collapse:collapse">\'
                f\'<thead><tr>\'
                f\'<th style="{TH}">티커</th>\'
                f\'<th style="{TH}">종목명</th>\'
                f\'<th style="{TH}">분기</th>\'
                f\'<th style="{TH_R}">매출</th>\'
                f\'<th style="{TH_R}">영업이익률</th>\'
                f\'</tr></thead>\'
                f\'<tbody>{rows_html}</tbody>\'
                f\'</table></div>\'
            )
        except Exception as e:
            return f\'<div style="color:{C_R};padding:16px">실적 렌더링 오류: {e}</div>\'

    earn_html = _earn_table(earn_res or {})'''

NEW_EARN_TABLE = '''    def _earn_table(earn):
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

# ═══════════════════════════════════════════════════════════════════
# 5. vc_html 생성 코드 추가 (earn_html 바로 뒤)
# ═══════════════════════════════════════════════════════════════════
OLD_AFTER_EARN = '''    earn_html = _earn_table(earn_res or {})'''

NEW_AFTER_EARN = '''    earn_html = _earn_table(earn_res or {})

    # ── 벨류체인 투자 현황 ────────────────────────────────────────
    def _vc_html(vc):
        BORDER = "#1e2535"; BG_H = "#0a0e17"
        C_G = "#15b98a"; C_R = "#f87171"; C_M = "#64748b"; C_T = "#e2e8f0"
        C_B = "#4d9eff"; C_Y = "#f5c842"; C_P = "#a78bfa"
        TH = (f\'padding:9px 14px;font-size:11px;font-weight:600;letter-spacing:.7px;\'
              f\'text-transform:uppercase;color:{C_M};border-bottom:1px solid {BORDER};\'
              f\'background:{BG_H};text-align:left\')
        TH_R = TH + \';text-align:right\'
        TD = f\'padding:9px 14px;font-size:12px;border-bottom:1px solid {BORDER};color:{C_T}\'
        TD_R = TD + \';text-align:right\'
        if not vc:
            return f\'<div style="padding:32px;text-align:center;color:{C_M}">벨류체인 데이터 없음</div>\'

        def _chg(v, size="13px"):
            if v is None:
                return f\'<span style="color:{C_M};font-size:{size}">N/A</span>\'
            try:
                v = float(v)
                c = C_G if v > 0 else (C_R if v < 0 else C_M)
                s = "+" if v > 0 else ""
                return f\'<span style="color:{c};font-size:{size}">{s}{v:.1f}%</span>\'
            except:
                return f\'<span style="color:{C_M}">—</span>\'

        # 부모 기업별로 그룹핑
        groups = {}
        for r in vc:
            p = r.get("parent","기타")
            if p not in groups:
                groups[p] = {"display": r.get("display", p), "rows": []}
            groups[p]["rows"].append(r)

        html = ""
        for parent, g in groups.items():
            rows_html = ""
            for r in g["rows"]:
                tk = r.get("ticker","비상장")
                price = r.get("price")
                price_s = f\'$\' + f\'{price:,.2f}\' if price else "비상장"
                inv_usd = r.get("inv_usd") or 0
                inv_fmt = r.get("inv_fmt","—")
                # 투자금 색상
                if inv_usd >= 1e9:
                    inv_c = C_G
                elif inv_usd >= 1e8:
                    inv_c = C_Y
                else:
                    inv_c = C_T
                # 관계 유형 배지
                rel = str(r.get("rel_type",""))
                rel_html = (f\'<span style="background:rgba(167,139,250,.15);color:{C_P};\'
                            f\'padding:1px 7px;border-radius:4px;font-size:10px">{rel}</span>\')

                rows_html += (
                    f\'<tr>\'
                    f\'<td style="{TD}">{r.get("area","")}</td>\'
                    f\'<td style="{TD};font-weight:600">{r.get("company","")}</td>\'
                    f\'<td style="{TD};color:{C_B}">{tk if tk != "비상장" else ""}</td>\'
                    f\'<td style="{TD_R};color:{inv_c}">{inv_fmt}</td>\'
                    f\'<td style="{TD_R}">{price_s}</td>\'
                    f\'<td style="{TD_R}">{_chg(r.get("ret_1m"))}</td>\'
                    f\'<td style="{TD_R}">{_chg(r.get("ret_3m"))}</td>\'
                    f\'<td style="{TD}">{rel_html}</td>\'
                    f\'<td style="{TD};font-size:11px;color:{C_M}">{str(r.get("inv_date",""))}</td>\'
                    f\'</tr>\'
                )
            html += (
                f\'<div style="margin-bottom:24px">\'
                f\'<div style="font-size:14px;font-weight:700;color:{C_Y};\'
                f\'padding:8px 14px;background:{BG_H};border-radius:6px 6px 0 0;\'
                f\'border:1px solid {BORDER};border-bottom:none">\'
                f\'{g["display"]}</div>\'
                f\'<div style="overflow-x:auto;border:1px solid {BORDER};border-radius:0 0 6px 6px">\'
                f\'<table style="width:100%;border-collapse:collapse">\'
                f\'<thead><tr>\'
                f\'<th style="{TH}">분야</th>\'
                f\'<th style="{TH}">기업명</th>\'
                f\'<th style="{TH}">티커</th>\'
                f\'<th style="{TH_R}">투자금액</th>\'
                f\'<th style="{TH_R}">현재가</th>\'
                f\'<th style="{TH_R}">1개월</th>\'
                f\'<th style="{TH_R}">3개월</th>\'
                f\'<th style="{TH}">관계</th>\'
                f\'<th style="{TH}">투자일</th>\'
                f\'</tr></thead>\'
                f\'<tbody>{rows_html}</tbody></table></div></div>\'
            )
        return html if html else f\'<div style="padding:32px;text-align:center;color:{C_M}">벨류체인 데이터 없음</div>\'

    vc_html = _vc_html(vc_res or [])'''

# ═══════════════════════════════════════════════════════════════════
# 패치 적용
# ═══════════════════════════════════════════════════════════════════
checks = [
    ("tab buttons",      OLD_TABS in src),
    ("tabs content",     OLD_TABS_CONTENT in src),
    ("html_assign",      OLD_HTML_ASSIGN in src),
    ("earn_table",       OLD_EARN_TABLE in src),
    ("after_earn",       OLD_AFTER_EARN in src),
]
all_ok = True
for name, found in checks:
    print(f"[{'OK' if found else 'MISS'}] {name}")
    if not found:
        all_ok = False

if not all_ok:
    print("일부 앵커 없음 — 패치 중단")
    sys.exit(1)

# 순서 중요: OLD_AFTER_EARN이 OLD_EARN_TABLE의 마지막 줄과 겹치므로
# earn_table 먼저 교체 후 after_earn 교체
src = src.replace(OLD_TABS,          NEW_TABS,          1)
src = src.replace(OLD_TABS_CONTENT,  NEW_TABS_CONTENT,  1)
src = src.replace(OLD_HTML_ASSIGN,   NEW_HTML_ASSIGN,   1)
src = src.replace(OLD_EARN_TABLE,    NEW_EARN_TABLE,    1)
# OLD_AFTER_EARN은 NEW_EARN_TABLE 마지막 줄이므로 NEW_EARN_TABLE 안에 이미 포함됨
# → 별도 교체 불필요, 하지만 vc_html은 NEW_EARN_TABLE 끝에 이미 삽입됨

# NEW_EARN_TABLE 이미 OLD_AFTER_EARN 포함했으므로 별도 치환 skip
# 하지만 vc_html 코드가 NEW_EARN_TABLE 뒤에 위치해야 하므로 확인
if "vc_html = _vc_html" not in src:
    # NEW_EARN_TABLE이 OLD_AFTER_EARN을 먹어버렸으므로 수동 삽입
    src = src.replace(
        "    earn_html = _earn_table(earn_res or {})",
        NEW_AFTER_EARN,
        1
    )
    print("[FIX] vc_html 별도 삽입")

nb['cells'][0]['source'] = [src]
with open(NB_PATH, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
print("patch25 done")
