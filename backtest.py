# -*- coding: utf-8 -*-
"""
backtest.py — TA 가중점수 & 시장 레짐 필터의 실효성 실측 (가격 기반, point-in-time)

측정 내용:
  1) TA 가중점수(weighted_base) 버킷별 이후 N일 수익률 → "점수가 높을수록 더 오르나?"
  2) 시장 레짐(SPY MA200) 조건별 → "하락 레짐에서 신호는 승률이 낮나?" (#3 필터 검증)

한계(정직): 신뢰도 #1 펀더멘털·#2 추정치·#4 실적일은 과거 스냅샷을 무료로 복원 불가 →
  이 하니스는 TA점수 + 레짐만 검증. 나머지는 전향 추적 로그(별도)로 검증 필요.

사용:
  python backtest.py                      # 기본 종목군, 5/10/20일 horizon
  python backtest.py --tickers AAPL,MSFT,NVDA
  python backtest.py --horizons 5,10,20 --min-hist 300
결과: backtest_result.csv + 콘솔 요약표
"""
import sys, json, argparse, re
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

NB = "scanner_portpolio_v4.ipynb"

# ── 노트북에서 필요한 함수만 추출해 exec ────────────────────────────────────
def _extract(src, name, kind="def"):
    """모듈 레벨(column 0) def/assign 소스 슬라이스."""
    if kind == "def":
        m = re.search(r"(?m)^def " + re.escape(name) + r"\(", src)
    else:  # 변수 할당
        m = re.search(r"(?m)^" + re.escape(name) + r"\s*=", src)
    if not m:
        raise RuntimeError(f"함수/변수 추출 실패: {name}")
    start = m.start()
    # 다음 column-0 def/class/구분선/변수 전까지
    nxt = re.search(r"(?m)^(def |class |# ═|[A-Za-z_]+\s*=\s*\{|_CHART_JS)", src[start + 1:])
    end = start + 1 + nxt.start() if nxt else len(src)
    return src[start:end]


def load_notebook_funcs():
    import yfinance as yf
    import ta
    from datetime import datetime, date, timedelta
    src = "".join(json.load(open(NB, encoding="utf-8"))["cells"][0]["source"])
    ns = {"pd": pd, "np": np, "yf": yf, "ta": ta,
          "datetime": datetime, "date": date, "timedelta": timedelta}
    # 순서 주의: 의존 함수 먼저
    for name in ["hts_rsi", "stoch_slow", "ichimoku_hts", "calc_atr",
                 "prepare_df", "count_buy_signals", "_classify_signal", "market_regime"]:
        try:
            exec(_extract(src, name), ns)
        except Exception as e:
            print(f"  [경고] {name} 추출/exec 실패: {e}")
    m = re.search(r"(?ms)^CATEGORY_CAP\s*=\s*\{.*?^\}", src)
    if m:
        exec(m.group(0), ns)
    else:
        ns["CATEGORY_CAP"] = {"추세": 2.0, "골든크로스": 2.5, "모멘텀": 2.0,
                              "되돌림": 0.5, "거래량": 1.5, "기타": 1.0}
    exec(_extract(src, "weighted_base"), ns)
    return ns


DEFAULT_TICKERS = [
    "AAPL","MSFT","NVDA","AMZN","GOOGL","META","TSLA","AVGO","AMD","NFLX",
    "CRM","ADBE","QCOM","INTC","MU","PLTR","SMCI","ARM","PANW","SNOW",
    "COST","PEP","LIN","TXN","INTU","NOW","ISRG","BKNG","VRTX","REGN",
    "RKLB","LMT","RTX","BA","GE","CAT","JPM","XOM","CVX","UNH",
]


def spy_regime_series(ns):
    """SPY 날짜별 레짐(+1/0/-1) 시리즈."""
    d, _ = ns["prepare_df"]("SPY")
    if d is None:
        return None
    c = d["Close"]
    ma50 = c.rolling(50).mean(); ma200 = c.rolling(200).mean()
    reg = pd.Series(0, index=c.index)
    reg[(c > ma200) & (ma50 >= ma200)] = 1
    reg[(c < ma200) & (ma50 < ma200)] = -1
    return reg


def run(tickers, horizons, min_hist):
    ns = load_notebook_funcs()
    prepare_df = ns["prepare_df"]; count_buy = ns["count_buy_signals"]
    weighted_base = ns["weighted_base"]
    print("  SPY 레짐 로딩...")
    reg = spy_regime_series(ns)
    maxH = max(horizons)
    recs = []
    for i, tk in enumerate(tickers, 1):
        try:
            d, _ = prepare_df(tk)
        except Exception as e:
            print(f"  [{tk}] prepare_df 오류: {e}"); continue
        if d is None or len(d) < min_hist:
            print(f"  [{tk}] 데이터 부족 (skip)"); continue
        closes = d["Close"].values
        idx = d.index
        n = len(d)
        for t in range(200, n - maxH):
            sub = d.iloc[:t + 1]
            try:
                cnt, sigs = count_buy(sub)
                wscore, _ = weighted_base(sigs)
            except Exception:
                continue
            dt = idx[t]
            rval = int(reg.reindex([dt]).iloc[0]) if reg is not None and dt in reg.index else 0
            row = {"ticker": tk, "date": str(dt.date()), "wscore": round(wscore, 2), "regime": rval}
            for H in horizons:
                row[f"fwd{H}"] = closes[t + H] / closes[t] - 1.0
            recs.append(row)
        print(f"  [{i}/{len(tickers)}] {tk}: 누적 {len(recs)}개")
    df = pd.DataFrame(recs)
    if df.empty:
        print("  기록 없음 — 종료"); return
    df.to_csv("backtest_result.csv", index=False, encoding="utf-8-sig")
    print(f"\n  저장: backtest_result.csv ({len(df)} rows)\n")
    _summary(df, horizons)


def _bucket(s):
    if s <= 0.01: return "0 (무신호)"
    if s < 2:     return "0<s<2"
    if s < 4:     return "2~4"
    if s < 6:     return "4~6"
    return "6+"


def _agg(df, hcol):
    g = df.groupby("bucket")[hcol]
    out = pd.DataFrame({
        "n": g.size(),
        "mean%": (g.mean() * 100).round(2),
        "median%": (g.median() * 100).round(2),
        "win%": (df.assign(w=df[hcol] > 0).groupby("bucket")["w"].mean() * 100).round(1),
    })
    order = ["0 (무신호)", "0<s<2", "2~4", "4~6", "6+"]
    return out.reindex([o for o in order if o in out.index])


def _summary(df, horizons):
    df = df.copy()
    df["bucket"] = df["wscore"].map(_bucket)
    for H in horizons:
        hcol = f"fwd{H}"
        print("=" * 64)
        print(f"[ Horizon {H}일 · 전체 레짐 ] — TA 점수 버킷별 이후 수익률")
        print(_agg(df, hcol).to_string())
        print(f"\n[ Horizon {H}일 · 레짐 분리 ] (신호 s>=2 만)")
        sig = df[df["wscore"] >= 2]
        for rlabel, rval in [("강세(+1)", 1), ("중립(0)", 0), ("약세(-1)", -1)]:
            sub = sig[sig["regime"] == rval]
            if len(sub) == 0:
                continue
            print(f"  {rlabel}: n={len(sub)} mean={sub[hcol].mean()*100:.2f}% "
                  f"median={sub[hcol].median()*100:.2f}% win={ (sub[hcol]>0).mean()*100:.1f}%")
        print()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", default="")
    ap.add_argument("--horizons", default="5,10,20")
    ap.add_argument("--min-hist", type=int, default=300)
    a = ap.parse_args()
    tickers = [t.strip().upper() for t in a.tickers.split(",") if t.strip()] or DEFAULT_TICKERS
    horizons = [int(h) for h in a.horizons.split(",")]
    print(f"  종목 {len(tickers)}개 · horizon {horizons} · 최소이력 {a.min_hist}")
    run(tickers, horizons, a.min_hist)
