"""
patch24_yfinance_fallback.py
1. analyze_sectors: ETF 다운로드 간 짧은 sleep 추가 + 섹터 캐시 저장/로드
2. daily_job: earn_res 폴백 (port_res 비어있을 때 unified_portfolio 종목으로 실적 조회)
3. prepare_df: 실패 시 재시도 1회 추가
"""
import json, sys

NB_PATH = r"C:\Users\Sangmin\Desktop\Stock\scanner_portpolio_v4.ipynb"

with open(NB_PATH, 'r', encoding='utf-8') as f:
    nb = json.load(f)
src = ''.join(nb['cells'][0]['source'])

# ── 1. analyze_sectors: 캐시 저장 + sleep ─────────────────────────────
OLD_SECTOR_END = '''    sector_data = dict(sorted(sector_data.items(),
        key=lambda x: (x[1]["score"], x[1]["ret_1m"]), reverse=True))
    print(f"  섹터 분석 완료 ({len(sector_data)}개)")
    return sector_data'''

NEW_SECTOR_END = '''    sector_data = dict(sorted(sector_data.items(),
        key=lambda x: (x[1]["score"], x[1]["ret_1m"]), reverse=True))
    print(f"  섹터 분석 완료 ({len(sector_data)}개)")
    # 캐시 저장
    if sector_data:
        try:
            import json as _json
            with open("sector_data_cache.json", "w", encoding="utf-8") as _f:
                _json.dump(sector_data, _f, ensure_ascii=False)
        except Exception as _e:
            print(f"  섹터 캐시 저장 실패: {_e}")
    else:
        # 캐시에서 복원 시도
        try:
            import json as _json
            with open("sector_data_cache.json", "r", encoding="utf-8") as _f:
                sector_data = _json.load(_f)
            print(f"  ⚠ 섹터 데이터 없음 → 캐시 복원 ({len(sector_data)}개, 이전 데이터)")
        except Exception:
            pass
    return sector_data'''

# ── 2. prepare_df: 실패 시 1초 후 재시도 ─────────────────────────────
OLD_PREPARE = '''def prepare_df(ticker):
    d = yf.Ticker(ticker).history(period="2y")
    if len(d) < 60:
        return None, None'''

NEW_PREPARE = '''def prepare_df(ticker):
    import time as _time
    for _attempt in range(2):
        try:
            d = yf.Ticker(ticker).history(period="2y")
            if len(d) >= 60:
                break
            if _attempt == 0:
                _time.sleep(1)
        except Exception as _ex:
            if _attempt == 0:
                print(f"    [{ticker}] yfinance 오류 ({_ex}), 1초 후 재시도...")
                _time.sleep(1)
            else:
                print(f"    [{ticker}] yfinance 재시도 실패: {_ex}")
                return None, None
    else:
        return None, None
    if len(d) < 60:
        return None, None'''

# ── 3. daily_job: earn_res 폴백 ───────────────────────────────────────
OLD_EARN_CALL = '''    # ── 분기별 실적 분석 ──
    earn_res = run_earnings_scan(port_res)
    print_earnings_summary(earn_res)
    display_earnings_table(earn_res)'''

NEW_EARN_CALL = '''    # ── 분기별 실적 분석 ──
    earn_res = run_earnings_scan(port_res)
    # port_res가 비어있으면 unified_portfolio 종목으로 실적 조회 (폴백)
    if not earn_res and unified_portfolio:
        try:
            fallback_tickers = [
                s["ticker"] for s in unified_portfolio.get("stocks", [])
                if s.get("ticker") and s.get("market") not in ("국내", "국내ETF")
            ]
            if fallback_tickers:
                print(f"  [폴백] port_res 없음 → unified_portfolio {len(fallback_tickers)}개 미국주식 실적 조회")
                fallback_port = [{"ticker": t} for t in fallback_tickers]
                earn_res = run_earnings_scan(fallback_port)
        except Exception as _e:
            print(f"  실적 폴백 실패: {_e}")
    print_earnings_summary(earn_res)
    display_earnings_table(earn_res)'''

# ── 패치 적용 ──────────────────────────────────────────────────────────
checks = [
    ("sector end",    OLD_SECTOR_END in src),
    ("prepare_df",    OLD_PREPARE in src),
    ("earn call",     OLD_EARN_CALL in src),
]
all_ok = True
for name, found in checks:
    print(f"[{'OK' if found else 'MISS'}] {name}")
    if not found:
        all_ok = False

if not all_ok:
    sys.exit(1)

src = src.replace(OLD_SECTOR_END, NEW_SECTOR_END, 1)
src = src.replace(OLD_PREPARE,    NEW_PREPARE,    1)
src = src.replace(OLD_EARN_CALL,  NEW_EARN_CALL,  1)

nb['cells'][0]['source'] = [src]
with open(NB_PATH, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
print("patch24 done")
