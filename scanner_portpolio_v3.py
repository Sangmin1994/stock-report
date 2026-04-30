#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import yfinance as yf
import ta
import numpy as np
import pandas as pd
import platform
import smtplib
import os
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler

# ════════════════════════════════════════════
#  ★ 사용자 설정 — 여기만 수정하세요
# ════════════════════════════════════════════
import os
try:
    import streamlit as st
    _HAS_ST = True
except ImportError:
    _HAS_ST = False
EMAIL_FROM     = os.environ.get("EMAIL_FROM", "")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "")
EMAIL_TO       = os.environ.get("EMAIL_TO", "")
GSHEET_KEY_FILE = os.environ.get("GSHEET_KEY_FILE", "stately-transit-494900-i8-524c44e2e62d.json")
GSHEET_ID       = os.environ.get("GSHEET_ID", "1YBeI6rKzlx8AK23FldZBHwMiLF3J4pFP141aUF6NSEg")
GSHEET_SHEET    = os.environ.get("GSHEET_SHEET", "시트1")

PORTFOLIO_FILE  = "portfolio.csv"
SCHEDULE_HOUR   = 10
SCHEDULE_MINUTE = 16

SCAN_BUY_THRESHOLD = 3
SCAN_WEEKLY_MIN    = 2
PORT_BUY_THRESHOLD = 3

# ════════════════════════════════════════════
#  신규 — yfinance 자동 티커/섹터 수집
# ════════════════════════════════════════════

def get_sp500_tickers_auto():
    """
    S&P500 구성종목 자동 수집
    방법 1: yfinance SPY funds_data (최신 yfinance 0.2.x+)
    방법 2: yfinance IVV/VOO funds_data
    방법 3: Wikipedia requests 파싱
    방법 4: 하드코딩 폴백
    """
    # 방법 1: SPY ETF 구성종목
    for etf in ["SPY", "IVV", "VOO"]:
        try:
            ticker = yf.Ticker(etf)
            # yfinance 0.2.x funds_data 방식
            fd = ticker.funds_data
            if hasattr(fd, 'top_holdings') and fd.top_holdings is not None:
                tickers = fd.top_holdings.index.tolist()
                if len(tickers) > 50:
                    print(f"  S&P500 로드 완료 ({etf} funds_data): {len(tickers)}종목")
                    return tickers
        except Exception:
            pass

    # 방법 2: yfinance info → holdings (구버전 호환)
    try:
        spy = yf.Ticker("SPY")
        info = spy.info
        if "holdings" in info and len(info["holdings"]) > 50:
            tickers = [h["symbol"] for h in info["holdings"]]
            print(f"  S&P500 로드 완료 (SPY info): {len(tickers)}종목")
            return tickers
    except Exception:
        pass

    # 방법 3: Wikipedia requests 파싱
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                  "AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        tbl = pd.read_html(resp.text, header=0)[0]
        tickers = tbl["Symbol"].str.replace(".", "-", regex=False).tolist()
        print(f"  S&P500 로드 완료 (Wikipedia): {len(tickers)}종목")
        return tickers
    except Exception as e:
        print(f"  ⚠ S&P500 Wikipedia 파싱 실패: {e}")

    # 방법 4: 폴백 하드코딩
    print(f"  ⚠ S&P500 자동 로드 전체 실패 — 하드코딩 사용 ({len(SP500_FALLBACK)}종목)")
    return SP500_FALLBACK


def get_nasdaq100_tickers_auto():
    """
    나스닥100 구성종목 자동 수집
    방법 1: yfinance QQQ funds_data
    방법 2: Wikipedia requests 파싱
    방법 3: 하드코딩 폴백
    """
    # 방법 1: QQQ ETF 구성종목
    for etf in ["QQQ", "QQQM"]:
        try:
            ticker = yf.Ticker(etf)
            fd = ticker.funds_data
            if hasattr(fd, 'top_holdings') and fd.top_holdings is not None:
                tickers = fd.top_holdings.index.tolist()
                if len(tickers) > 50:
                    print(f"  나스닥100 로드 완료 ({etf} funds_data): {len(tickers)}종목")
                    return tickers
        except Exception:
            pass

    # 방법 2: Wikipedia 파싱
    try:
        url = "https://en.wikipedia.org/wiki/Nasdaq-100"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                  "AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        tables = pd.read_html(resp.text, header=0)
        for tbl in tables:
            cols = [c.lower() for c in tbl.columns]
            if "ticker" in cols or "symbol" in cols:
                col = "Ticker" if "Ticker" in tbl.columns else "Symbol"
                tickers = tbl[col].str.replace(".", "-", regex=False).tolist()
                print(f"  나스닥100 로드 완료 (Wikipedia): {len(tickers)}종목")
                return tickers
    except Exception as e:
        print(f"  ⚠ 나스닥100 Wikipedia 파싱 실패: {e}")

    # 방법 3: 폴백 하드코딩
    print(f"  ⚠ 나스닥100 자동 로드 전체 실패 — 하드코딩 사용 ({len(NASDAQ100_FALLBACK)}종목)")
    return NASDAQ100_FALLBACK


def get_ticker_sector_map_auto(tickers):
    """
    yfinance info에서 종목별 섹터 자동 수집
    sector 필드 → SPDR ETF 코드로 매핑
    """
    SECTOR_TO_ETF = {
        "Technology":             "XLK",
        "Financial Services":     "XLF",
        "Healthcare":             "XLV",
        "Health Care":            "XLV",
        "Energy":                 "XLE",
        "Industrials":            "XLI",
        "Communication Services": "XLC",
        "Consumer Cyclical":      "XLY",
        "Consumer Defensive":     "XLP",
        "Basic Materials":        "XLB",
        "Utilities":              "XLU",
        "Real Estate":            "XLRE",
    }

    print(f"\n  [섹터 맵 자동 구축] {len(tickers)}종목 섹터 정보 수집 중...")
    sector_map = {}
    batch_size = 50   # yfinance 배치 다운로드

    # yfinance download로 배치 처리 (빠름)
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i+batch_size]
        for t in batch:
            try:
                info = yf.Ticker(t).fast_info
                # fast_info는 sector 없음 → 개별 info 호출
                sector_str = yf.Ticker(t).info.get("sector", "")
                etf = SECTOR_TO_ETF.get(sector_str, "")
                if etf:
                    sector_map[t] = etf
            except Exception:
                pass
        if (i + batch_size) % 100 == 0:
            print(f"    섹터 맵 진행: {min(i+batch_size, len(tickers))}/{len(tickers)}")

    print(f"  섹터 맵 완료: {len(sector_map)}종목 매핑됨")
    return sector_map


# ── 폴백 하드코딩 (자동 로드 실패 시) ────────
SP500_FALLBACK = [
    "AAPL","MSFT","NVDA","AVGO","AMD","QCOM","INTC","MU","AMAT","LRCX",
    "KLAC","TXN","ADI","MRVL","NXPI","MPWR","FTNT","CDNS","SNPS","CRM",
    "ORCL","NOW","INTU","ADBE","PANW","CRWD","ZS","DDOG","SNOW","WDAY",
    "META","GOOGL","GOOG","NFLX","DIS","CMCSA","T","VZ","TMUS","PARA",
    "AMZN","TSLA","HD","MCD","NKE","SBUX","LOW","TJX","BKNG","MAR",
    "PG","KO","PEP","WMT","COST","PM","MO","GIS","CLX","CL",
    "JPM","BAC","WFC","GS","MS","C","BLK","SCHW","AXP","COF",
    "JNJ","UNH","PFE","ABBV","MRK","LLY","BMY","AMGN","GILD","REGN",
    "GE","CAT","BA","HON","RTX","LMT","NOC","UPS","FDX","CSX",
    "XOM","CVX","COP","SLB","EOG","DVN","HAL","VLO","MPC","OXY",
    "LIN","APD","SHW","PPG","NEM","FCX","NUE","ALB","MOS","CF",
    "NEE","DUK","SO","D","AEP","EXC","XEL","ED","PEG","AWK",
    "AMT","PLD","CCI","EQIX","PSA","O","SPG","WELL","EQR","AVB",
]

NASDAQ100_FALLBACK = [
    "AAPL","MSFT","NVDA","AMZN","META","GOOGL","GOOG","TSLA","AVGO","COST",
    "NFLX","AMD","PEP","ADBE","CSCO","INTC","QCOM","TXN","AMGN","HON",
    "INTU","AMAT","SBUX","GILD","MDLZ","REGN","LRCX","VRTX","KLAC","SNPS",
    "CDNS","ORLY","MELI","PANW","MRVL","ADP","FTNT","CRWD","DXCM","ABNB",
    "ZS","TEAM","WDAY","ODFL","PCAR","BIIB","FAST","DDOG","ON","VRSK",
]

# ════════════════════════════════════════════
#  SPDR 섹터 ETF 정의 (분석용)
# ════════════════════════════════════════════
SECTOR_ETFS = {
    "XLK":  "기술 (Technology)",
    "XLF":  "금융 (Financials)",
    "XLV":  "헬스케어 (Health Care)",
    "XLE":  "에너지 (Energy)",
    "XLI":  "산업재 (Industrials)",
    "XLC":  "커뮤니케이션 (Communication)",
    "XLY":  "임의소비재 (Consumer Discretionary)",
    "XLP":  "필수소비재 (Consumer Staples)",
    "XLB":  "소재 (Materials)",
    "XLU":  "유틸리티 (Utilities)",
    "XLRE": "부동산 (Real Estate)",
}
SECTOR_STRATEGY = {
    "XLK":"C", "XLC":"C", "XLY":"C", "XLV":"C", "XLP":"C",
    "XLF":"D",
    "XLI":"A", "XLB":"A", "XLE":"A", "XLU":"A", "XLRE":"A",
}
TICKER_SECTOR = {
    "NVDA":"XLK","AMD":"XLK","AAPL":"XLK","MSFT":"XLK","AVGO":"XLK",
    "QCOM":"XLK","INTC":"XLK","MU":"XLK","AMAT":"XLK","LRCX":"XLK",
    "KLAC":"XLK","TXN":"XLK","ADI":"XLK","MRVL":"XLK","NXPI":"XLK",
    "MPWR":"XLK","FTNT":"XLK","CDNS":"XLK","SNPS":"XLK","CRM":"XLK",
    "ORCL":"XLK","NOW":"XLK","INTU":"XLK","ADBE":"XLK","PANW":"XLK",
    "CRWD":"XLK","ZS":"XLK","DDOG":"XLK","SNOW":"XLK","WDAY":"XLK",
    "META":"XLC","GOOGL":"XLC","GOOG":"XLC","NFLX":"XLC","DIS":"XLC",
    "CMCSA":"XLC","T":"XLC","VZ":"XLC","TMUS":"XLC",
    "AMZN":"XLY","TSLA":"XLY","HD":"XLY","MCD":"XLY","NKE":"XLY",
    "SBUX":"XLY","LOW":"XLY","TJX":"XLY","BKNG":"XLY","MAR":"XLY",
    "MGM":"XLY","WYNN":"XLY","EBAY":"XLY","BBY":"XLY","ROST":"XLY",
    "PG":"XLP","KO":"XLP","PEP":"XLP","WMT":"XLP","COST":"XLP",
    "PM":"XLP","MO":"XLP","GIS":"XLP","CLX":"XLP","CL":"XLP",
    "ADM":"XLP","BG":"XLP","MKC":"XLP","SJM":"XLP","CAG":"XLP",
    "JPM":"XLF","BAC":"XLF","WFC":"XLF","GS":"XLF","MS":"XLF",
    "C":"XLF","BLK":"XLF","SCHW":"XLF","AXP":"XLF","COF":"XLF",
    "USB":"XLF","BEN":"XLF","NDAQ":"XLF",
    "JNJ":"XLV","UNH":"XLV","PFE":"XLV","ABBV":"XLV","MRK":"XLV",
    "LLY":"XLV","BMY":"XLV","AMGN":"XLV","GILD":"XLV","REGN":"XLV",
    "XOM":"XLE","CVX":"XLE","COP":"XLE","SLB":"XLE","EOG":"XLE",
    "DVN":"XLE","HAL":"XLE","VLO":"XLE","MPC":"XLE","OXY":"XLE",
    "APA":"XLE","FANG":"XLE","CTRA":"XLE","TRGP":"XLE","OKE":"XLE",
    "GE":"XLI","CAT":"XLI","BA":"XLI","HON":"XLI","RTX":"XLI",
    "LMT":"XLI","NOC":"XLI","UPS":"XLI","FDX":"XLI","CSX":"XLI",
    "PCAR":"XLI","WAB":"XLI","GD":"XLI",
    "LIN":"XLB","APD":"XLB","SHW":"XLB","PPG":"XLB","NEM":"XLB",
    "FCX":"XLB","NUE":"XLB","LYB":"XLB","ALB":"XLB","CF":"XLB",
    "GLW":"XLB",
    "NEE":"XLU","DUK":"XLU","SO":"XLU","D":"XLU","AEP":"XLU",
    "EXC":"XLU","XEL":"XLU","ED":"XLU","NI":"XLU","WEC":"XLU",
    "AMT":"XLRE","PLD":"XLRE","CCI":"XLRE","EQIX":"XLRE","PSA":"XLRE",
    "O":"XLRE","SPG":"XLRE","WELL":"XLRE","EQR":"XLRE","VTR":"XLRE",
    "EXR":"XLRE","STX":"XLK","LITE":"XLK","RKLB":"XLI",
}

SECTOR_EXCEPTIONS_LABEL = {
    "XLF":  "무형자산/기타자산/우선주 (금융 구조상 정상)",
    "XLRE": "무형자산/기타자산 (부동산 구조상 정상)",
    "XLK":  "무형자산 (소프트웨어 IP 정상)",
    "XLV":  "무형자산 (특허/IP 정상)",
    "XLI":  "매출채권증가 (B2B 정상)",
    "XLU":  "기타장기자산 (인프라 정상)",
}
DEFAULT_STRATEGY = "C"

STRATEGY_PARAMS = {
    "A": {"weekly_min": 0, "need_cloud": False},
    "C": {"weekly_min": 2, "need_cloud": False},
    "D": {"weekly_min": 2, "need_cloud": True },
}

# ════════════════════════════════════════════
#  1. 공통 지표 계산
# ════════════════════════════════════════════
def hts_rsi(close, period=14, signal_period=9):
    delta    = close.diff()
    gain     = delta.clip(lower=0)
    loss     = (-delta).clip(lower=0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs       = avg_gain / avg_loss.replace(0, np.nan)
    rsi      = 100 - (100 / (1 + rs))
    signal   = rsi.ewm(span=signal_period, adjust=False).mean()
    return rsi, signal

def stoch_slow(high, low, close, k_period=5, slow_k=3, slow_d=3):
    lowest  = low.rolling(window=k_period).min()
    highest = high.rolling(window=k_period).max()
    fast_k  = (close - lowest) / (highest - lowest).replace(0, np.nan) * 100
    sk      = fast_k.ewm(span=slow_k, adjust=False).mean()
    sd      = sk.ewm(span=slow_d, adjust=False).mean()
    return sk, sd

def ichimoku_hts(high, low):
    tenkan = (high.rolling(9).max()  + low.rolling(9).min())  / 2
    kijun  = (high.rolling(26).max() + low.rolling(26).min()) / 2
    span_a = ((tenkan + kijun) / 2).shift(26)
    span_b = ((high.rolling(52).max() + low.rolling(52).min()) / 2).shift(26)
    return span_a, span_b

def calc_atr(df, period=14):
    high, low, close = df["High"], df["Low"], df["Close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low  - prev_close).abs()
    ], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()

def prepare_df(ticker):
    d = yf.Ticker(ticker).history(period="2y")
    if len(d) < 60:
        return None, None
    d = d[["Open","High","Low","Close","Volume"]].copy()
    d.index = d.index.tz_localize(None)
    for w in [5, 20, 60, 120, 200]:
        d[f"MA{w}"] = ta.trend.SMAIndicator(d["Close"], window=w).sma_indicator()
    d["RSI"], d["RSI_sig"] = hts_rsi(d["Close"])
    macd = ta.trend.MACD(d["Close"], window_fast=12, window_slow=26, window_sign=9)
    d["MACDh"] = macd.macd_diff()
    bb = ta.volatility.BollingerBands(d["Close"], window=20, window_dev=2)
    d["BB_upper"] = bb.bollinger_hband()
    d["BB_lower"] = bb.bollinger_lband()
    d["BB_pct"]   = bb.bollinger_pband()
    d["%K"], d["%D"] = stoch_slow(d["High"], d["Low"], d["Close"])
    d["span_a"], d["span_b"] = ichimoku_hts(d["High"], d["Low"])
    d["ATR"] = calc_atr(d)
    # OBV 계산
    obv = [0]
    for i in range(1, len(d)):
        if d["Close"].iloc[i] > d["Close"].iloc[i-1]:
            obv.append(obv[-1] + d["Volume"].iloc[i])
        elif d["Close"].iloc[i] < d["Close"].iloc[i-1]:
            obv.append(obv[-1] - d["Volume"].iloc[i])
        else:
            obv.append(obv[-1])
    d["OBV"] = obv
    d["OBV_MA"] = pd.Series(obv).rolling(20).mean().values
    
    # ADX 계산
    high, low, close = d["High"], d["Low"], d["Close"]
    plus_dm  = high.diff().clip(lower=0)
    minus_dm = (-low.diff()).clip(lower=0)
    plus_dm[plus_dm < (-low.diff()).clip(lower=0)]  = 0
    minus_dm[minus_dm < high.diff().clip(lower=0)] = 0
    atr14    = calc_atr(d, period=14)
    plus_di  = 100 * (plus_dm.ewm(span=14).mean()  / atr14)
    minus_di = 100 * (minus_dm.ewm(span=14).mean() / atr14)
    dx       = (abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.nan)) * 100
    d["ADX"]      = dx.ewm(span=14).mean()
    d["PLUS_DI"]  = plus_di
    d["MINUS_DI"] = minus_di

    w = yf.Ticker(ticker).history(period="3y", interval="1wk")
    if len(w) < 30:
        return d, None
    w = w[["Open","High","Low","Close","Volume"]].copy()
    w.index = w.index.tz_localize(None)
    for ww in [5, 10, 20, 60, 120]:
        w[f"MA{ww}"] = ta.trend.SMAIndicator(w["Close"], window=ww).sma_indicator()
    w["span_a"], w["span_b"] = ichimoku_hts(w["High"], w["Low"])
    return d, w

# ════════════════════════════════════════════
#  2. 신호 / 추세 계산
# ════════════════════════════════════════════
def weekly_trend_score(w_df):
    if w_df is None or len(w_df) < 5:
        return 0
    r = w_df.iloc[-1]
    score = 0
    if pd.notna(r.get("MA20")) and pd.notna(r.get("MA60")):
        score += 1 if r["Close"] > r["MA20"] else -1
        score += 1 if r["MA20"]  > r["MA60"]  else -1
    if pd.notna(r.get("span_a")) and pd.notna(r.get("span_b")):
        cloud_top = max(r["span_a"], r["span_b"])
        score += 1 if r["Close"] > cloud_top else -1
    return score

def count_buy_signals(d_df):
    if d_df is None or len(d_df) < 3:
        return 0, []
    r, r1 = d_df.iloc[-1], d_df.iloc[-2]
    sigs = []

    if pd.notna(r.get("span_a")) and pd.notna(r.get("span_b")):
        if r["Close"] > max(r["span_a"], r["span_b"]):
            sigs.append("구름대 위")

    if pd.notna(r.get("MA5")) and pd.notna(r.get("MA20")) and pd.notna(r.get("MA60")):
        if r["MA5"] > r["MA20"] > r["MA60"]:
            sigs.append("MA 정배열")

    if pd.notna(r.get("RSI")) and pd.notna(r.get("RSI_sig")):
        if r1["RSI"] <= r1["RSI_sig"] and r["RSI"] > r["RSI_sig"] and r["RSI"] < 65:
            sigs.append("RSI 상향돌파")

    if pd.notna(r.get("MACDh")) and pd.notna(r1.get("MACDh")):
        if r1["MACDh"] < 0 and r["MACDh"] >= 0:
            sigs.append("MACD 양전환")

    if pd.notna(r.get("%K")) and pd.notna(r.get("%D")):
        if r["%K"] < 35 and r1["%K"] <= r1["%D"] and r["%K"] > r["%D"]:
            sigs.append(f"Stoch GC(K={r['%K']:.0f})")

    if pd.notna(r.get("BB_pct")) and r["BB_pct"] < 0.25:
        sigs.append(f"BB하단({r['BB_pct']:.2f})")

    vol_ma = d_df["Volume"].rolling(20).mean().iloc[-1]
    if pd.notna(vol_ma) and r["Volume"] > vol_ma * 1.5 and r["Close"] >= r["Open"]:
        sigs.append(f"거래량급증({r['Volume']/vol_ma:.1f}x)")

    # RSI 상승 기울기 — 최근 3일 RSI 우상향 + 30~70 구간
    rsi_3d_ago = d_df["RSI"].iloc[-3]
    if pd.notna(r.get("RSI")) and pd.notna(rsi_3d_ago):
        rsi_slope = r["RSI"] - rsi_3d_ago
        if rsi_slope > 3 and 30 < r["RSI"] < 70:
            sigs.append(f"RSI상승기울기(+{rsi_slope:.1f})")

    # OBV 상승 — 보정 점수만
    if "OBV" in d_df.columns and "OBV_MA" in d_df.columns:
        if pd.notna(r.get("OBV")) and pd.notna(r.get("OBV_MA")):
            if r["OBV"] > r["OBV_MA"] and d_df["OBV"].iloc[-1] > d_df["OBV"].iloc[-5]:
                sigs.append(f"OBV상승({r['OBV']/r['OBV_MA']:.2f}x)")
    
    # ADX 강세 — 보정 점수만
    if "ADX" in d_df.columns and pd.notna(r.get("ADX")):
        if r["ADX"] > 25:
            sigs.append(f"ADX강세({r['ADX']:.1f})")

    return len(sigs), sigs

def count_sell_signals(d_df):
    """매도 신호 카운트"""
    if d_df is None or len(d_df) < 2:
        return 0, []
    r, r1 = d_df.iloc[-1], d_df.iloc[-2]
    sigs = []

    # 가격이 구름대 아래
    if pd.notna(r.get("span_a")) and pd.notna(r.get("span_b")):
        if r["Close"] < min(r["span_a"], r["span_b"]):
            sigs.append("구름대 아래")

    # MA 역배열
    if pd.notna(r.get("MA5")) and pd.notna(r.get("MA20")) and pd.notna(r.get("MA60")):
        if r["MA5"] < r["MA20"] < r["MA60"]:
            sigs.append("MA 역배열")

    # RSI Signal 하향 돌파
    if pd.notna(r.get("RSI")) and pd.notna(r.get("RSI_sig")):
        if r1["RSI"] >= r1["RSI_sig"] and r["RSI"] < r["RSI_sig"] and r["RSI"] > 35:
            sigs.append(f"RSI 하향돌파({r['RSI']:.1f})")

    # MACD 히스토그램 음전환
    if pd.notna(r.get("MACDh")) and pd.notna(r1.get("MACDh")):
        if r1["MACDh"] > 0 and r["MACDh"] <= 0:
            sigs.append("MACD 음전환")

    # Stoch 데드크로스 (65 이상)
    if pd.notna(r.get("%K")) and pd.notna(r.get("%D")):
        if r["%K"] > 65 and r1["%K"] >= r1["%D"] and r["%K"] < r["%D"]:
            sigs.append(f"Stoch DC(K={r['%K']:.0f})")

    # BB 상단 이탈
    if pd.notna(r.get("BB_pct")) and r["BB_pct"] > 0.90:
        sigs.append(f"BB상단({r['BB_pct']:.2f})")

    # 거래량 급증 + 음봉
    vol_ma = d_df["Volume"].rolling(20).mean().iloc[-1]
    if pd.notna(vol_ma) and r["Volume"] > vol_ma * 1.5 and r["Close"] < r["Open"]:
        sigs.append(f"거래량급증+음봉({r['Volume']/vol_ma:.1f}x)")

    return len(sigs), sigs

def check_fundamental(ticker, etf_code=""):
    """
    대차대조표 기반 펀더멘털 체크리스트 (8가지)
    섹터별 예외 처리 포함
    반환: (위험_개수, 위험_항목_리스트, 판정)
    """
    # 섹터별 예외 항목 정의
    SECTOR_EXCEPTIONS = {
        "XLF":  [5, 6, 7],   # 금융: 무형자산/기타장기자산/우선주 구조적 정상
        "XLRE": [5, 6],       # 부동산: 무형자산/기타장기자산 정상
        "XLK":  [5],          # 기술: 무형자산 높음 정상 (소프트웨어 특성)
        "XLV":  [5],          # 헬스케어: 무형자산 높음 정상 (특허/IP)
        "XLI":  [2],          # 산업재: 매출채권 증가 일부 정상 (B2B)
        "XLU":  [6],          # 유틸리티: 기타장기자산 높음 정상 (인프라)
    }
    exceptions = SECTOR_EXCEPTIONS.get(etf_code, [])

    try:
        ticker_obj = yf.Ticker(ticker)
        bs = ticker_obj.balance_sheet      # 대차대조표
        fs = ticker_obj.financials         # 손익계산서
        cf = ticker_obj.cashflow           # 현금흐름표

        if bs is None or bs.empty:
            return 0, [], "데이터없음"

        # 최신 / 전년도 컬럼
        col0 = bs.columns[0]   # 최신
        col1 = bs.columns[1] if len(bs.columns) > 1 else col0

        def get(df, *keys):
            """여러 키 중 존재하는 첫 번째 값 반환"""
            for k in keys:
                if k in df.index:
                    v = df.loc[k, col0]
                    return float(v) if pd.notna(v) else 0.0
            return 0.0

        def get_prev(df, *keys):
            for k in keys:
                if k in df.index:
                    v = df.loc[k, col1]
                    return float(v) if pd.notna(v) else 0.0
            return 0.0

        # 주요 항목 추출
        cash          = get(bs, "Cash And Cash Equivalents",
                             "Cash Cash Equivalents And Short Term Investments")
        total_debt    = get(bs, "Total Debt", "Long Term Debt And Capital Lease Obligation")
        current_debt  = get(bs, "Current Debt", "Current Debt And Capital Lease Obligation",
                             "Short Long Term Debt")
        total_assets  = get(bs, "Total Assets")
        intangibles   = get(bs, "Goodwill And Other Intangible Assets",
                             "Net PPE", "Goodwill")
        other_assets  = get(bs, "Other Non Current Assets", "Other Assets")
        preferred     = get(bs, "Preferred Stock", "Preferred Securities Outside StockHolders Equity")
        equity        = get(bs, "Stockholders Equity", "Common Stock Equity")
        inventory     = get(bs, "Inventory")
        receivables   = get(bs, "Receivables", "Accounts Receivable")

        # 전년도
        inventory_prev    = get_prev(bs, "Inventory")
        receivables_prev  = get_prev(bs, "Receivables", "Accounts Receivable")

        # 손익계산서
        revenue     = 0.0
        revenue_prev= 0.0
        net_income  = 0.0
        if fs is not None and not fs.empty:
            fc0 = fs.columns[0]
            fc1 = fs.columns[1] if len(fs.columns) > 1 else fc0
            for k in ["Total Revenue", "Operating Revenue"]:
                if k in fs.index:
                    revenue      = float(fs.loc[k, fc0]) if pd.notna(fs.loc[k, fc0]) else 0.0
                    revenue_prev = float(fs.loc[k, fc1]) if pd.notna(fs.loc[k, fc1]) else 0.0
                    break
            for k in ["Net Income", "Net Income Common Stockholders"]:
                if k in fs.index:
                    net_income = float(fs.loc[k, fc0]) if pd.notna(fs.loc[k, fc0]) else 0.0
                    break

        # ── 체크리스트 판정 ──────────────────────
        risks = []

        # 1. 현금 < 총부채 → 유동성 위기
        if 1 not in exceptions:
            if total_debt > 0 and cash < total_debt:
                risks.append("현금<총부채")

        # 2. 매출채권 증가율 > 매출 증가율 → 외상 매출 위험
        if 2 not in exceptions:
            if revenue_prev > 0 and receivables_prev > 0:
                rev_growth = (revenue - revenue_prev) / abs(revenue_prev)
                rec_growth = (receivables - receivables_prev) / abs(receivables_prev)
                if rec_growth > rev_growth + 0.05:   # 5%p 이상 차이
                    risks.append("매출채권↑>매출↑")

        # 3. 재고 증가율 > 순이익 증가율 → 수요 감소
        if 3 not in exceptions:
            if inventory_prev > 0 and inventory > inventory_prev:
                inv_growth = (inventory - inventory_prev) / abs(inventory_prev)
                if net_income < 0 or inv_growth > 0.15:   # 재고 15% 이상 증가
                    risks.append("재고↑이익↓")

        # 4. 단기부채 > 보유현금 → 채무 상환 능력 부족
        if 4 not in exceptions:
            if current_debt > 0 and current_debt > cash:
                risks.append("단기부채>현금")

        # 5. 무형자산 > 총자산 50% → 자산가치 변동성
        if 5 not in exceptions:
            if total_assets > 0 and intangibles / total_assets > 0.5:
                risks.append(f"무형자산{intangibles/total_assets*100:.0f}%")

        # 6. 기타장기자산 > 총자산 50% → 불투명한 자산
        if 6 not in exceptions:
            if total_assets > 0 and other_assets / total_assets > 0.5:
                risks.append(f"기타자산{other_assets/total_assets*100:.0f}%")

        # 7. 우선주 존재 → 일반 주주 불리
        if 7 not in exceptions:
            if preferred > 0:
                risks.append("우선주존재")

        # 8. 자기자본 음수 → 자본잠식
        if 8 not in exceptions:
            if equity < 0:
                risks.append("자본잠식")

        # 판정
        risk_count = len(risks)
        if risk_count == 0:
            judgment = "✅ 양호"
        elif risk_count <= 2:
            judgment = "⚠ 주의"
        else:
            judgment = "🔴 위험"

        return risk_count, risks, judgment

    except Exception as e:
        return 0, [], "조회실패"

def calc_stop_target(d_df, entry):
    if d_df is None or len(d_df) < 20:
        return entry * 0.95, entry * 1.10, 0
    r = d_df.iloc[-1]
    atr = r["ATR"] if pd.notna(r.get("ATR")) else entry * 0.03
    recent_low = d_df["Low"].tail(20).min()
    cloud_bot  = min(r["span_a"], r["span_b"]) if pd.notna(r.get("span_a")) else recent_low
    stop_swing = max(recent_low, cloud_bot) * 0.995
    stop_atr   = entry - atr * 2.0
    stop       = max(stop_swing, stop_atr)
    risk       = entry - stop
    target_rr  = entry + risk * 2.0
    target_bb  = r["BB_upper"] if pd.notna(r.get("BB_upper")) else entry * 1.10
    target     = float(np.median([target_rr, target_bb, target_rr]))
    rr         = (target - entry) / risk if risk > 0 else 0

    # 피보나치 되돌림 레벨 계산
    high_recent = d_df["High"].tail(60).max()
    low_recent  = d_df["Low"].tail(60).min()
    fib_382 = round(high_recent - (high_recent - low_recent) * 0.382, 2)
    fib_618 = round(high_recent - (high_recent - low_recent) * 0.618, 2)

    return round(stop, 2), round(target, 2), round(rr, 2)

def generate_chart_base64(ticker, d_df):
    """일봉 180일 차트 생성 → Base64 문자열 반환"""
    import io, base64
    import matplotlib as mpl
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec
    from matplotlib.patches import Rectangle

    # 한글 폰트
    import platform
    _sys = platform.system()
    font = "Malgun Gothic" if _sys=="Windows" else \
           "AppleGothic"   if _sys=="Darwin"  else "NanumGothic"
    mpl.rcParams["font.family"]        = font
    mpl.rcParams["axes.unicode_minus"] = False

    df = d_df.tail(180).copy()
    if len(df) < 30:
        return None

    fig = plt.figure(figsize=(14, 12))
    fig.suptitle(f"{ticker} — 일봉 180일", fontsize=13, fontweight="bold")
    gs = gridspec.GridSpec(4, 1, figure=fig,
                           height_ratios=[3, 1, 1, 1],
                           hspace=0.08)

    # ── 1. 캔들 + MA + BB + 일목 ──────────────
    ax1 = fig.add_subplot(gs[0])
    for i, (idx, row) in enumerate(df.iterrows()):
        color = "#ef4444" if row["Close"] >= row["Open"] else "#3b82f6"
        ax1.plot([i, i], [row["Low"], row["High"]], color=color, lw=0.8)
        ax1.add_patch(Rectangle(
            (i-0.3, min(row["Open"], row["Close"])),
            0.6, abs(row["Close"]-row["Open"]),
            color=color, zorder=2))

    x = range(len(df))
    # MA
    for w, c, lw in [(5,"#f59e0b",1.0),(20,"#8b5cf6",1.2),
                     (60,"#06b6d4",1.4),(120,"#10b981",1.4)]:
        col = f"MA{w}"
        if col in df.columns:
            ax1.plot(x, df[col], color=c, lw=lw, label=f"MA{w}", alpha=0.8)

    # 볼린저밴드
    if "BB_upper" in df.columns:
        ax1.plot(x, df["BB_upper"], color="#94a3b8", lw=0.8, ls="--", alpha=0.6)
        ax1.plot(x, df["BB_lower"], color="#94a3b8", lw=0.8, ls="--", alpha=0.6)
        ax1.fill_between(x, df["BB_upper"], df["BB_lower"],
                         alpha=0.05, color="#94a3b8")

    # 일목균형표 구름대
    if "span_a" in df.columns and "span_b" in df.columns:
        ax1.fill_between(x, df["span_a"], df["span_b"],
                         where=df["span_a"] >= df["span_b"],
                         alpha=0.15, color="#ef4444", label="구름대(양)")
        ax1.fill_between(x, df["span_a"], df["span_b"],
                         where=df["span_a"] < df["span_b"],
                         alpha=0.15, color="#3b82f6", label="구름대(음)")

    ax1.legend(loc="upper left", fontsize=8, ncol=4)
    ax1.set_xlim(-1, len(df))
    ax1.xaxis.set_visible(False)
    ax1.set_ylabel("가격", fontsize=9)
    ax1.grid(axis="y", alpha=0.3)

    # ── 2. RSI ────────────────────────────────
    ax2 = fig.add_subplot(gs[1], sharex=ax1)
    if "RSI" in df.columns:
        ax2.plot(x, df["RSI"],     color="#8b5cf6", lw=1.2, label="RSI")
        ax2.plot(x, df["RSI_sig"], color="#f59e0b", lw=0.9,
                 ls="--", label="Signal")
        ax2.axhline(70, color="#ef4444", lw=0.7, ls="--", alpha=0.6)
        ax2.axhline(30, color="#3b82f6", lw=0.7, ls="--", alpha=0.6)
        ax2.fill_between(x, df["RSI"], 70,
                         where=df["RSI"]>=70, alpha=0.15, color="#ef4444")
        ax2.fill_between(x, df["RSI"], 30,
                         where=df["RSI"]<=30, alpha=0.15, color="#3b82f6")
        ax2.set_ylim(0, 100)
        ax2.set_ylabel("RSI", fontsize=9)
        ax2.legend(loc="upper left", fontsize=8)
        ax2.grid(alpha=0.3)
    ax2.xaxis.set_visible(False)

    # ── 3. MACD ───────────────────────────────
    ax3 = fig.add_subplot(gs[2], sharex=ax1)
    if "MACDh" in df.columns:
        colors = ["#ef4444" if v >= 0 else "#3b82f6"
                  for v in df["MACDh"]]
        ax3.bar(x, df["MACDh"], color=colors, alpha=0.7, width=0.8)
        ax3.axhline(0, color="gray", lw=0.7)
        ax3.set_ylabel("MACD", fontsize=9)
        ax3.grid(axis="y", alpha=0.3)
    ax3.xaxis.set_visible(False)

    # ── 4. Stoch Slow ─────────────────────────
    ax4 = fig.add_subplot(gs[3], sharex=ax1)
    if "%K" in df.columns and "%D" in df.columns:
        ax4.plot(x, df["%K"], color="#8b5cf6", lw=1.2, label="%K")
        ax4.plot(x, df["%D"], color="#f59e0b", lw=0.9,
                 ls="--", label="%D")
        ax4.axhline(80, color="#ef4444", lw=0.7, ls="--", alpha=0.6)
        ax4.axhline(20, color="#3b82f6", lw=0.7, ls="--", alpha=0.6)
        ax4.set_ylim(0, 100)
        ax4.set_ylabel("Stoch", fontsize=9)
        ax4.legend(loc="upper left", fontsize=8)
        ax4.grid(alpha=0.3)

    # X축 날짜 레이블
    tick_step = max(1, len(df) // 10)
    ticks = list(range(0, len(df), tick_step))
    labels = [df.index[i].strftime("%m/%d") for i in ticks]
    ax4.set_xticks(ticks)
    ax4.set_xticklabels(labels, fontsize=8)

    plt.tight_layout()

    # Base64 변환
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    img_b64 = base64.b64encode(buf.read()).decode("utf-8")
    return img_b64

# ════════════════════════════════════════════
#  3. 섹터 분석
# ════════════════════════════════════════════
def analyze_sectors():
    print("\n  [섹터 분석] SPDR ETF 11개 로딩 중...")
    sector_data = {}
    for etf, label in SECTOR_ETFS.items():
        try:
            d_df, w_df = prepare_df(etf)
            if d_df is None:
                continue
            ws      = weekly_trend_score(w_df)
            rsi_val = round(d_df["RSI"].iloc[-1], 1) if pd.notna(d_df["RSI"].iloc[-1]) else 50
            cur     = d_df["Close"].iloc[-1]
            ret_1w  = round((cur / d_df["Close"].iloc[-5]  - 1) * 100, 2) if len(d_df) >= 5  else 0
            ret_1m  = round((cur / d_df["Close"].iloc[-21] - 1) * 100, 2) if len(d_df) >= 21 else 0
            ret_3m  = round((cur / d_df["Close"].iloc[-63] - 1) * 100, 2) if len(d_df) >= 63 else 0
            ret_6m  = round((cur / d_df["Close"].iloc[-126]- 1) * 100, 2) if len(d_df) >= 126 else 0

            # 기간별 강세/약세 판정 (True/False)
            bull_1w = ret_1w > 0
            bull_1m = ret_1m > 0
            bull_3m = ret_3m > 0
            bull_6m = ret_6m > 0

            # 강세 기간 카운트 (0~4)
            bull_count = sum([bull_1w, bull_1m, bull_3m, bull_6m])

            # 추세 유형 판정
            if bull_count == 4:
                trend_type = "완전상승"   # 전 기간 강세
            elif bull_count == 3:
                trend_type = "상승추세"
            elif bull_count == 2:
                if bull_1w and bull_1m:
                    trend_type = "단기반등"   # 장기는 약세, 단기만 강세
                elif bull_3m and bull_6m:
                    trend_type = "장기강세"   # 장기는 강세, 단기 조정
                else:
                    trend_type = "혼조"
            elif bull_count == 1:
                if bull_1w:
                    trend_type = "반등시도"   # 1주만 강세 → 일시 반등
                else:
                    trend_type = "약세전환"
            else:
                trend_type = "완전약세"

            # 섹터 가중치 (주봉 + 1달 기준)
            if ws >= 2 and ret_1m > 0 and rsi_val < 70:
                status, weight_add = "🟢 강세", 1
            elif ws >= 1 and ret_1m > -2:
                status, weight_add = "🟡 중립", 0
            elif ws <= -1 or ret_1m < -5:
                status, weight_add = "🔴 약세", -1
            else:
                status, weight_add = "⚪ 관망", 0

            sector_data[etf] = {
                "label": label, "score": ws, "rsi": rsi_val,
                "ret_1w": ret_1w, "ret_1m": ret_1m,
                "ret_3m": ret_3m, "ret_6m": ret_6m,
                "bull_1w": bull_1w, "bull_1m": bull_1m,
                "bull_3m": bull_3m, "bull_6m": bull_6m,
                "trend_type": trend_type,
                "status": status, "weight_add": weight_add,
            }
        except Exception as e:
            print(f"    [{etf}] 오류: {e}")
    sector_data = dict(sorted(sector_data.items(),
        key=lambda x: (x[1]["score"], x[1]["ret_1m"]), reverse=True))
    print(f"  섹터 분석 완료 ({len(sector_data)}개)")
    return sector_data

def get_sector_weight(ticker, sector_map, sector_data):
    """
    sector_map: {ticker: etf코드} — yfinance 자동 수집
    sector_data: {etf코드: {...}} — ETF 분석 결과
    """
    etf = sector_map.get(ticker.upper())
    if etf and etf in sector_data:
        return sector_data[etf]["weight_add"], sector_data[etf]["status"]
    return 0, "미분류"

def print_sector_summary(sector_data):
    print(f"\n  {'ETF':>5}  {'섹터':28}  {'주봉':>4}  {'RSI':>5}  "
          f"{'1주':>6}  {'1달':>6}  {'분기':>6}  {'반기':>6}  "
          f"{'추세유형':>8}  상태")
    print("  " + "─"*95)
    for etf, d in sector_data.items():
        # 기간별 색상 표시
        def fmt(val, bull):
            arrow = "▲" if bull else "▼"
            return f"{arrow}{abs(val):.1f}%"

        print(f"  {etf:>5}  {d['label']:28}  {d['score']:>+4}  "
              f"{d['rsi']:>5.1f}  "
              f"{fmt(d['ret_1w'], d['bull_1w']):>6}  "
              f"{fmt(d['ret_1m'], d['bull_1m']):>6}  "
              f"{fmt(d['ret_3m'], d['bull_3m']):>6}  "
              f"{fmt(d['ret_6m'], d['bull_6m']):>6}  "
              f"{d['trend_type']:>8}  {d['status']}")

# ════════════════════════════════════════════
#  4. 전략C — 전종목 스캔
# ════════════════════════════════════════════
def run_market_scan(sector_data=None, sector_map=None):
    print(f"\n{'='*60}")
    print(f"  시장 스캔 시작: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  기준: 섹터별 최적 전략 자동 적용 (백테스팅 기반)")
    print(f"        XLK/XLC/XLY/XLV/XLP → 전략C | XLF → 전략D | 나머지 → 전략A")
    print(f"{'='*60}")

    # 티커 자동 수집
    sp500   = get_sp500_tickers_auto()
    ndaq100 = get_nasdaq100_tickers_auto()
    tickers = list(set(sp500 + ndaq100))
    print(f"  스캔 대상: {len(tickers)}종목")

    # sector_map 없으면 자동 구축 (시간 소요 — 생략 가능)
    if sector_map is None:
        sector_map = {}

    results = []
    errors  = 0

    for i, ticker in enumerate(tickers):
        try:
            d_df, w_df = prepare_df(ticker)
            if d_df is None:
                continue
            ws = weekly_trend_score(w_df)
            sig_cnt,  sig_list  = count_buy_signals(d_df)
            sell_cnt, sell_list = count_sell_signals(d_df)

            sector_etf = (sector_map or {}).get(ticker.upper(), "")
            strategy   = SECTOR_STRATEGY.get(sector_etf, DEFAULT_STRATEGY)
            params   = STRATEGY_PARAMS[strategy]

            if ws < params["weekly_min"]:
                continue
            if sig_cnt < SCAN_BUY_THRESHOLD:
                continue
            if params["need_cloud"]:
                r_chk = d_df.iloc[-1]
                if not (pd.notna(r_chk.get("span_a")) and
                        pd.notna(r_chk.get("span_b")) and
                        r_chk["Close"] > max(r_chk["span_a"], r_chk["span_b"])):
                    continue
            entry = round(d_df["Close"].iloc[-1], 2)
            # 52주 신고가 근접 여부
            high_52w = d_df["High"].tail(252).max()
            near_52w_high = entry >= high_52w * 0.80  # 신고가 20% 이내

            # 베타 계수 계산
            try:
                spy_df, _ = prepare_df("SPY")
                if spy_df is not None and len(spy_df) >= 60:
                    ret_stock = d_df["Close"].pct_change().tail(60)
                    ret_spy   = spy_df["Close"].pct_change().tail(60)
                    cov   = np.cov(ret_stock, ret_spy)[0][1]
                    var   = np.var(ret_spy)
                    beta  = round(cov / var, 2) if var > 0 else 1.0
                else:
                    beta = 1.0
            except:
                beta = 1.0
            etf_code   = (sector_map or {}).get(ticker.upper(), "")
            trend_type = sector_data.get(etf_code, {}).get("trend_type", "미분류") if sector_data else "미분류"
            fund_cnt, fund_risks, fund_judge = check_fundamental(ticker, etf_code)
            stop, target, rr = calc_stop_target(d_df, entry)
            stop_pct   = round((stop   / entry - 1) * 100, 2)
            target_pct = round((target / entry - 1) * 100, 2)
            sec_add, sec_status = get_sector_weight(ticker, sector_map, sector_data or {})
            # 52주 신고가 근접 보정
            if near_52w_high:
                sec_add += 1
            # 베타 안정적 보정
            if 0.5 <= beta <= 1.5:
                sec_add += 1
            adj_signals = sig_cnt + sec_add
            results.append({
                "date":      datetime.now().strftime("%Y-%m-%d"),
                "ticker":    ticker,
                "price":     entry,
                "signals":   sig_cnt,
                "adj_sig":   adj_signals,
                "sell_cnt":  sell_cnt,
                "weekly":    ws,
                "sector":    sec_status,
                "trend_type": trend_type,
                "stop":      stop,
                "stop_pct":  stop_pct,
                "target":    target,
                "target_pct":target_pct,
                "rr":        rr,
                "buy_detail": " / ".join(sig_list),
                "sell_detail":" / ".join(sell_list) if sell_list else "없음",
                "strategy": strategy,
                "details":   " / ".join(sig_list),
                "fund_judge": fund_judge,
                "beta":         beta,
                "near_52w":     near_52w_high,
                "adx":          round(r["ADX"], 1) if pd.notna(r.get("ADX")) else 0,
                "fund_cnt":   fund_cnt,
                "fund_risks": " / ".join(fund_risks) if fund_risks else "없음",
            })
            if (i+1) % 50 == 0:
                print(f"  진행: {i+1}/{len(tickers)} ... 신호 {len(results)}종목")
        except Exception as e:
            errors += 1
            if errors <= 5:   # 처음 5개 오류만 출력
                print(f"  [{ticker}] 오류: {type(e).__name__}: {e}")

    results.sort(key=lambda x: (x["adj_sig"], x["weekly"]), reverse=True)
    print(f"\n  스캔 완료 → 신호 발생: {len(results)}종목 (오류: {errors})")
    return results

# ════════════════════════════════════════════
#  5. 포트폴리오 데일리 업데이트 (기존 동일)
# ════════════════════════════════════════════
def create_sample_portfolio():
    sample = pd.DataFrame([
        {"ticker":"CAT","buy_price":764.3021,"shares":10,"buy_date":"2026-01-01"},
        {"ticker":"CDNS","buy_price":332.28,"shares":60,"buy_date":"2026-01-01"},
        {"ticker":"GOOGL","buy_price":308.3147,"shares":4,"buy_date":"2026-01-01"},
        {"ticker":"JPM","buy_price":309.1727,"shares":3,"buy_date":"2026-01-01"},
        {"ticker":"NVDA","buy_price":186.6520,"shares":5,"buy_date":"2026-01-01"},
        {"ticker":"RKLB","buy_price":59.2025,"shares":42,"buy_date":"2026-01-01"},
        {"ticker":"TSLA","buy_price":416.1024,"shares":3,"buy_date":"2026-01-01"},
        {"ticker":"WMT","buy_price":129.1158,"shares":7,"buy_date":"2026-01-01"},


    ])
    sample.to_csv(PORTFOLIO_FILE, index=False, encoding="utf-8-sig")
    print(f"  샘플 포트폴리오 생성: {PORTFOLIO_FILE}")
    return sample

def run_portfolio_update(sector_map=None, sector_data=None):
    print(f"\n{'='*60}")
    print(f"  포트폴리오 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}")
     # Google Sheets에서 포트폴리오 로드
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        import json
        if os.path.exists(GSHEET_KEY_FILE):
            # 로컬 환경
            creds = Credentials.from_service_account_file(
                        GSHEET_KEY_FILE, scopes=scopes)
        else:
            # Streamlit Cloud 환경
            key_dict = json.loads(os.environ.get("GSHEET_JSON", "{}"))
            creds = Credentials.from_service_account_info(
                        key_dict, scopes=scopes)
        gc        = gspread.authorize(creds)
        sh        = gc.open_by_key(GSHEET_ID)
        ws        = sh.worksheet(GSHEET_SHEET)
        data      = ws.get_all_records()
        portfolio = pd.DataFrame(data)
        print(f"  Google Sheets 로드 완료: {len(portfolio)}종목")
    except Exception as e:
        print(f"  ⚠ Google Sheets 로드 실패: {e}")
        print(f"  → CSV 폴백으로 전환")
        if not os.path.exists(PORTFOLIO_FILE):
            portfolio = create_sample_portfolio()
        else:
            portfolio = pd.read_csv(PORTFOLIO_FILE, encoding="utf-8-sig")
    required = {"ticker","buy_price","shares","buy_date"}
    if not required.issubset(portfolio.columns):
        return []
    port_results = []
    for _, row in portfolio.iterrows():
        ticker    = row["ticker"]
        buy_price = float(row["buy_price"])
        shares    = float(row["shares"])
        buy_date  = str(row["buy_date"])
        try:
            d_df, w_df = prepare_df(ticker)
            if d_df is None:
                continue
            cur_price   = round(d_df["Close"].iloc[-1], 2)
            pnl_pct     = round((cur_price / buy_price - 1) * 100, 2)
            eval_amt    = round(cur_price * shares, 2)
            pnl_amt     = round(eval_amt - buy_price * shares, 2)
            sig_cnt, sig_list = count_buy_signals(d_df)
            ws          = weekly_trend_score(w_df)
            stop, target, rr = calc_stop_target(d_df, cur_price)
            etf_code_port  = (sector_map or {}).get(ticker.upper(), "")
            fund_cnt, fund_risks, fund_judge = check_fundamental(ticker, etf_code_port)
            stop_dist   = round((stop   / cur_price - 1) * 100, 2)
            target_dist = round((target / cur_price - 1) * 100, 2)
            try:
                hold_days = (datetime.now() -
                             datetime.strptime(buy_date, "%Y-%m-%d")).days
            except:
                hold_days = 0
            _, sec_status = get_sector_weight(
                ticker, sector_map or {}, sector_data or {})
            # 목표가 대비 현재 수익 진행률
            target_progress = (cur_price - buy_price) / (target - buy_price) * 100 \
                              if target > buy_price else 0

            # 섹터 추세 확인
            _, sec_status = get_sector_weight(ticker, sector_map or {}, sector_data or {})
            sec_bull = "강세" in sec_status

            # 펀더멘털 판정
            fund_ok = "✅" in fund_judge

            try:
                memo_val = row["memo"] if "memo" in row.index else ""
                memo = str(memo_val).strip() if pd.notna(memo_val) and str(memo_val) != "nan" else ""
            except:
                memo = ""

            if "재진입대기" in memo:
                if sig_cnt >= 3 and ws >= 2:
                    status = "🟣 재진입 신호 발생 — 매수 검토"
                elif sig_cnt >= 1:
                    status = "🔵 재진입 대기 (신호 약함)"
                else:
                    status = "🔵 재진입 대기 (신호 없음)"

            elif cur_price <= stop:
                status = "🔴 손절 고려"

            elif target_progress >= 80:
                if fund_ok and ws >= 2 and sec_bull:
                    status = "🟡 1/3 익절 후 장기보유"
                else:
                    status = "🟡 1/3 익절 고려"

            elif target_progress >= 50:
                if fund_ok and ws >= 2 and sec_bull:
                    status = "🟡 분할익절 고려 (추세 양호)"
                else:
                    status = "🟠 분할익절 고려 (추세 점검)"

            elif cur_price <= stop * 1.03:
                status = "🟠 손절가 근접 (모니터링)"

            elif sig_cnt >= 3 and ws >= 2 and pnl_pct < 5:
                status = "🟣 추가매수 고려"

            elif fund_ok and ws >= 2 and sec_bull and sig_cnt >= 2:
                status = "🟢 장기보유 유지"

            elif not sec_bull and ws <= 0:
                status = "🔵 추세 약화 (모니터링)"

            elif sig_cnt == 0 and pnl_pct < 0:
                status = "🟠 신호 소멸 (모니터링)"

            else:
                status = "⚪ 보유 유지"

            port_results.append({
                "ticker": ticker, "buy_price": buy_price,
                "cur_price": cur_price, "pnl_pct": pnl_pct,
                "pnl_amt": pnl_amt, "eval_amt": eval_amt,
                "hold_days": hold_days, "signals": sig_cnt,
                "weekly": ws, "sector": sec_status,
                "stop": stop, "target": target,
                "stop_dist": stop_dist, "target_dist": target_dist,
                "status": status,
                "memo": memo,
                "target_progress": round(target_progress, 1),
                "sig_details": " / ".join(sig_list) if sig_list else "없음",
                "fund_judge": fund_judge,
                "fund_cnt":   fund_cnt,
                "fund_risks": " / ".join(fund_risks) if fund_risks else "없음",
            })
        except Exception as e:
            print(f"  [{ticker}] 오류: {e}")
    if port_results:
        total_eval = sum(r["eval_amt"] for r in port_results)
        total_cost = sum(
            r["buy_price"] * portfolio[
                portfolio["ticker"]==r["ticker"]]["shares"].values[0]
            for r in port_results)
        total_pnl = total_eval - total_cost
        total_pct = (total_eval / total_cost - 1) * 100 if total_cost > 0 else 0
        print(f"\n  총 평가금액: ${total_eval:,.2f}  |  "
              f"총 손익: ${total_pnl:+,.2f} ({total_pct:+.2f}%)")
    return port_results

# ════════════════════════════════════════════
#  6. 이메일 발송
# ════════════════════════════════════════════
def send_email(scan_results, port_results, sector_data=None):
    today = datetime.now().strftime("%Y-%m-%d")

    # ── 섹터별 현황 ──────────────────────────
    sector_html = ""
    if sector_data:
        rows = ""
        for etf, d in sector_data.items():
            if   "강세" in d["status"]: bg="#f0fdf4"; sc="#16a34a"
            elif "약세" in d["status"]: bg="#fef2f2"; sc="#dc2626"
            elif "중립" in d["status"]: bg="#fffbeb"; sc="#d97706"
            else:                       bg="#f9fafb"; sc="#6b7280"
            sc2 = "#16a34a" if d["score"]>=2 else "#dc2626" if d["score"]<=-1 else "#d97706"
            r1c = "#16a34a" if d["ret_1m"]>0 else "#dc2626"
            r3c = "#16a34a" if d["ret_3m"]>0 else "#dc2626"
            r1w = "#16a34a" if d["ret_1w"]>0 else "#dc2626"
            r6m = "#16a34a" if d["ret_6m"]>0 else "#dc2626"
            tc  = {"완전상승":"#16a34a","상승추세":"#16a34a","장기강세":"#d97706",
                   "단기반등":"#d97706","혼조":"#d97706","반등시도":"#dc2626",
                   "약세전환":"#dc2626","완전약세":"#dc2626"}.get(d["trend_type"],"#6b7280")
            rows += f"""<tr style="background:{bg}">
  <td style="padding:10px 16px;font-weight:600;color:#1e40af">{etf}</td>
  <td style="padding:10px 16px">{d["label"]}</td>
  <td style="padding:10px 16px;text-align:center;color:{sc2};font-weight:600">{d["score"]:+d}</td>
  <td style="padding:10px 16px;text-align:center">{d["rsi"]:.1f}</td>
  <td style="padding:10px 16pxx;text-align:center;color:{r1w};font-weight:600">{d["ret_1w"]:+.1f}%</td>
  <td style="padding:10px 16px;text-align:center;color:{r1c};font-weight:600">{d["ret_1m"]:+.1f}%</td>
  <td style="padding:10px 16pxx;text-align:center;color:{r3c};font-weight:600">{d["ret_3m"]:+.1f}%</td>
  <td style="padding:10px 16pxx;text-align:center;color:{r6m};font-weight:600">{d["ret_6m"]:+.1f}%</td>
  <td style="padding:10px 16pxx;text-align:center;font-size:12px;font-weight:600;color:{tc}">{d["trend_type"]}</td>
  <td style="padding:10px 16px;text-align:center;font-weight:700;color:#4338ca">
    {SECTOR_STRATEGY.get(etf, DEFAULT_STRATEGY)}</td>
  <td style="padding:10px 16pxx;text-align:center;color:{sc};font-weight:600">{d["status"]}</td>
</tr>"""
        sector_html = f"""
<h3 style="color:#1e40af;border-bottom:2px solid #1e40af;padding-bottom:6px;margin-top:20px">
  📊 산업 섹터별 현황
</h3>
<table style="width:100%;border-collapse:collapse;font-size:14px;margin-bottom:20px">
<thead><tr style="background:#1e40af;color:white">
  <th style="padding:11px 16px;text-align:left">ETF</th>
  <th style="padding:11px 16px;text-align:left">섹터</th>
  <th style="padding:11px 16px;text-align:center">주봉점수</th>
  <th style="padding:11px 16px;text-align:center">RSI</th>
  <th style="padding:11px 16px;text-align:center">1주</th>
  <th style="padding:11px 16px;text-align:center">1달</th>
  <th style="padding:11px 16px;text-align:center">분기</th>
  <th style="padding:11px 16px;text-align:center">반기</th>
  <th style="padding:11px 16px;text-align:center">추세유형</th>
  <th style="padding:11px 16px;text-align:center">적용전략</th>
  <th style="padding:11px 16px;text-align:center">상태</th>
</tr></thead><tbody>{rows}</tbody></table>
<p style="font-size:12px;color:#6b7280;margin-top:6px;line-height:1.8">
  ※ 적용 전략 기준 (백테스팅 결과 기반)<br>
  ▪ <b>전략A</b> — 신호 3개 이상 (주봉 무관) | 안정적 종목 적합 | 에너지·소재·산업재·유틸리티·부동산<br>
  ▪ <b>전략C</b> — 주봉 점수 +2 이상 + 신호 3개 이상 | 고변동 종목 노이즈 필터링 | 기술·커뮤니케이션·임의소비재·헬스케어·필수소비재<br>
  ▪ <b>전략D</b> — 주봉 점수 +2 이상 + 구름대 위 + 신호 3개 이상 | 가장 보수적 | 금융
</p>"""

    # ── 매수 시그널 상세 테이블 ───────────────
    if scan_results:
        scan_rows = ""
        for i, r in enumerate(scan_results):
            bg       = "#f0fdf4" if i%2==0 else "white"
            rr_c     = "#16a34a" if r["rr"]>=2 else "#dc2626"
            sec      = r.get("sector","미분류")
            sec_c    = "#16a34a" if "강세" in sec else "#dc2626" if "약세" in sec                        else "#d97706" if "중립" in sec else "#9ca3af"
            sp       = r.get("stop_pct",  round((r["stop"]  /r["price"]-1)*100,1))
            tp       = r.get("target_pct",round((r["target"]/r["price"]-1)*100,1))
            sell_cnt = r.get("sell_cnt", 0)
            sell_det = r.get("sell_detail","없음")
            buy_det  = r.get("buy_detail", r.get("details",""))
            date_str = r.get("date", today)
            scan_rows += f"""<tr style="background:{bg}">
  <td style="padding:10px 12px;font-weight:700;color:#1e40af">{r["ticker"]}</td>
  <td style="padding:10px 12px;text-align:right">${r["price"]:.2f}</td>
  <td style="padding:10px 12px;text-align:center">
    <span style="background:#dcfce7;color:#16a34a;font-weight:700;padding:1px 7px;border-radius:10px">{r["signals"]}개</span></td>
  <td style="padding:10px 12px;text-align:center">
    <span style="background:#fee2e2;color:#dc2626;font-weight:700;padding:1px 7px;border-radius:10px">{sell_cnt}개</span></td>
  <td style="padding:10px 12px;text-align:center">
    <span style="background:#e0e7ff;color:#4338ca;font-weight:700;padding:1px 7px;border-radius:10px">{r["adj_sig"]}개</span></td>
  <td style="padding:10px 12px;text-align:center;font-weight:600;
      color:{"#16a34a" if r["weekly"]>=2 else "#d97706"}">{r["weekly"]:+d}</td>
  <td style="padding:10px 12px;text-align:center;font-weight:700;color:#4338ca">[{r.get("strategy","C")}]</td>
  <td style="padding:10px 12px;text-align:center;font-size:12px;color:{sec_c};font-weight:600">{sec}</td>
  <td style="padding:10px 12px;text-align:center;color:#dc2626;font-weight:600">
    ${r["stop"]:.2f}<br><small style="color:#dc2626">{sp:+.1f}%</small></td>
  <td style="padding:10px 12px;text-align:center;color:#16a34a;font-weight:600">
    ${r["target"]:.2f}<br><small style="color:#16a34a">{tp:+.1f}%</small></td>
  <td style="padding:10px 12px;font-size:12px;color:#15803d;
    word-break:break-word;overflow-wrap:break-word">{buy_det}</td>
  <td style="padding:10px 12px;font-size:12px;color:#dc2626;
    word-break:break-word;overflow-wrap:break-word">{sell_det}</td>
</tr>"""
        scan_section = f"""
<h3 style="color:#16a34a;border-bottom:2px solid #16a34a;padding-bottom:6px">
  🔍 매수 시그널 종목 — {len(scan_results)}종목
  <small style="color:#6b7280;font-size:13px;font-weight:400">
    (S&P500+나스닥100 | 주봉 +2이상 + 신호 3개이상)
  </small>
</h3>
<table style="width:100%;border-collapse:collapse;font-size:13px;table-layout:fixed">
<thead><tr style="background:#16a34a;color:white">
  <th style="padding:11px 12px;text-align:left">종목</th>
  <th style="padding:11px 12px;text-align:right">현재가</th>
  <th style="padding:11px 12px;text-align:center">매수신호</th>
  <th style="padding:11px 12px;text-align:center">매도신호</th>
  <th style="padding:11px 12px;text-align:center">보정</th>
  <th style="padding:11px 12px;text-align:center">주봉</th>
  <th style="padding:11px 12px;text-align:center">전략</th>
  <th style="padding:11px 12px;text-align:center">섹터</th>
  <th style="padding:11px 12px;text-align:center">손절가(%)</th>
  <th style="padding:11px 12px;text-align:center">목표가(%)</th>
  <th style="padding:11px 12px;text-align:left;width:180px">매수 근거</th>
  <th style="padding:11px 12px;text-align:left;width:140px">매도 근거</th>
</tr></thead><tbody>{scan_rows}</tbody></table>"""
    else:
        scan_section = """
<h3 style="color:#16a34a;border-bottom:2px solid #16a34a;padding-bottom:6px">
  🔍 매수 시그널 종목
</h3>
<p style="color:#6b7280">오늘은 신호 발생 종목이 없습니다.</p>"""

# ── 펀더멘털 체크리스트 — 매수 시그널 ──────
    fund_scan_rows = ""
    for i, r in enumerate(scan_results):
        bg       = "#f8faff" if i%2==0 else "white"
        judge    = r.get("fund_judge", "조회실패")
        cnt      = r.get("fund_cnt", 0)
        risks    = r.get("fund_risks", "없음")
        etf_code = TICKER_SECTOR.get(r["ticker"].upper(), "")
        exc_items= SECTOR_EXCEPTIONS_LABEL.get(etf_code, "해당없음")
        jc       = "#16a34a" if "✅" in judge else \
                   "#d97706" if "⚠"  in judge else \
                   "#dc2626" if "🔴" in judge else "#9ca3af"
        fund_scan_rows += f"""<tr style="background:{bg}">
  <td style="padding:10px 16pxx;font-weight:700;color:#1e40af">{r["ticker"]}</td>
  <td style="padding:10px 16px;text-align:center;font-weight:700;color:{jc}">{judge}({cnt}/8)</td>
  <td style="padding:10px 16px;font-size:12px;color:#dc2626">{risks}</td>
  <td style="padding:10px 16px;font-size:12px;color:#9ca3af">{exc_items}</td>
</tr>"""
    fund_scan_footnote = """<p style="font-size:12px;color:#6b7280;margin-top:6px;line-height:1.8">
  ※ 펀더멘털 체크리스트 항목 설명<br>
  ▪ <b>현금&lt;총부채</b> — 보유 현금이 총부채보다 적음 → 유동성 위기 가능성<br>
  ▪ <b>매출채권↑&gt;매출↑</b> — 매출채권 증가율이 매출보다 5%p↑ → 외상 매출, 현금 유입 불확실<br>
  ▪ <b>재고↑이익↓</b> — 재고 15%↑ 또는 순이익 마이너스 → 수요 감소 신호<br>
  ▪ <b>단기부채&gt;현금</b> — 단기 상환 의무 > 보유 현금 → 채무 상환 능력 부족<br>
  ▪ <b>무형자산N%</b> — 무형자산이 총자산 50% 초과 → 자산가치 변동성 증가<br>
  ▪ <b>기타자산N%</b> — 기타장기자산이 총자산 50% 초과 → 자산 구성 불투명<br>
  ▪ <b>우선주존재</b> — 우선주 발행 → 일반 주주보다 우선주 투자자에게 유리한 구조<br>
  ▪ <b>자본잠식</b> — 자기자본 음수 → 누적 손실로 자본 잠식, 상장폐지 위험<br>
  ▪ ✅ 양호(0개) &nbsp;|&nbsp; ⚠ 주의(1~2개) &nbsp;|&nbsp; 🔴 위험(3개 이상)
</p>"""
    fund_scan_section = f"""
<h3 style="color:#7c3aed;border-bottom:2px solid #7c3aed;
           padding-bottom:6px;margin-top:24px">
  🔬 펀더멘털 체크리스트 — 매수 시그널 종목
  <small style="color:#6b7280;font-size:13px;font-weight:400">
    (대차대조표 기준 8가지 위험 항목 | 섹터 특성 예외 반영)
  </small>
</h3>
<table style="width:100%;border-collapse:collapse;font-size:13px">
<thead><tr style="background:#7c3aed;color:white">
  <th style="padding:11px 16px;text-align:left">종목</th>
  <th style="padding:11px 16px;text-align:center">판정</th>
  <th style="padding:11px 16px;text-align:left">위험 항목</th>
  <th style="padding:11px 16px;text-align:left">섹터 예외 적용</th>
</tr></thead><tbody>{fund_scan_rows}</tbody></table>"""

    # ── 포트폴리오 현황 ───────────────────────
    if port_results:
        total_eval = sum(r["eval_amt"] for r in port_results)
        total_pnl  = sum(r["pnl_amt"]  for r in port_results)
        total_cost = total_eval - total_pnl
        total_pct  = (total_pnl/total_cost*100) if total_cost>0 else 0
        port_rows  = ""
        for i, r in enumerate(port_results):
            bg    = "#faf5ff" if i%2==0 else "white"
            pc    = "#16a34a" if r["pnl_pct"]>=0 else "#dc2626"
            port_rows += f"""<tr style="background:{bg}">
  <td style="padding:10px 12px;font-weight:700;color:#7c3aed">{r["ticker"]}</td>
  <td style="padding:10px 12px;text-align:right">${r["buy_price"]:.2f}</td>
  <td style="padding:10px 12px;text-align:right">${r["cur_price"]:.2f}</td>
  <td style="padding:10px 12px;text-align:center;font-weight:700;color:{pc}">{r["pnl_pct"]:+.2f}%</td>
  <td style="padding:10px 12px;text-align:right;color:{pc}">${r["pnl_amt"]:+,.2f}</td>
  <td style="padding:10px 12px;text-align:center">{r["hold_days"]}일</td>
  <td style="padding:10px 12px;text-align:center;font-size:12px">{r.get("sector","미분류")}</td>
  <td style="padding:10px 12px;text-align:center;color:#dc2626;font-weight:600">
    ${r["stop"]:.2f}<br><small>{r["stop_dist"]:+.1f}%</small></td>
  <td style="padding:10px 12px;text-align:center;color:#16a34a;font-weight:600">
    ${r["target"]:.2f}<br><small>{r["target_dist"]:+.1f}%</small></td>
  <td style="padding:10px 12px;text-align:center;font-weight:600;
      color:{"#16a34a" if r.get("target_progress",0)>=50 else "#6b7280"}">
    {r.get("target_progress",0):.1f}%</td>
  <td style="padding:10px 12px;text-align:center">{r["signals"]}개</td>
  <td style="padding:10px 12px;font-size:12px;color:#6b7280">{r.get("memo","")}</td>
  <td style="padding:10px 12px">{r["status"]}</td>
</tr>"""
        port_section = f"""
<h3 style="color:#7c3aed;border-bottom:2px solid #7c3aed;padding-bottom:6px;margin-top:24px">
  💼 포트폴리오 현황 — {len(port_results)}종목
</h3>
<p style="font-size:14px;margin-bottom:8px">
  총 평가: <b>${total_eval:,.2f}</b> | 손익:
  <b style="color:{"#16a34a" if total_pnl>=0 else "#dc2626"}">
    ${total_pnl:+,.2f} ({total_pct:+.2f}%)</b>
</p>
<table style="width:100%;border-collapse:collapse;font-size:13px">
<thead><tr style="background:#7c3aed;color:white">
  <th style="padding:11px 12px;text-align:left">종목</th>
  <th style="padding:11px 12px;text-align:right">매수가</th>
  <th style="padding:11px 12px;text-align:right">현재가</th>
  <th style="padding:11px 12px;text-align:center">수익률</th>
  <th style="padding:11px 12px;text-align:right">평가손익</th>
  <th style="padding:11px 12px;text-align:center">보유일</th>
  <th style="padding:11px 12px;text-align:center">섹터</th>
  <th style="padding:11px 12px;text-align:center">손절가(%)</th>
  <th style="padding:11px 12px;text-align:center">목표가(%)</th>
  <th style="padding:11px 12px;text-align:center">목표진행률</th>
  <th style="padding:11px 12px;text-align:center">신호</th>
  <th style="padding:11px 12px;text-align:left">메모</th>
  <th style="padding:11px 12px;text-align:left">상태</th>
</tr></thead><tbody>{port_rows}</tbody></table>"""
    else:
        port_section = """
<h3 style="color:#7c3aed;border-bottom:2px solid #7c3aed;padding-bottom:6px;margin-top:24px">
  💼 포트폴리오 현황
</h3>
<p style="color:#6b7280">포트폴리오 데이터가 없습니다.</p>"""

# ── 펀더멘털 체크리스트 — 포트폴리오 ────────
    fund_port_rows = ""
    for i, r in enumerate(port_results):
        bg       = "#f0f9ff" if i%2==0 else "white"
        judge    = r.get("fund_judge", "조회실패")
        cnt      = r.get("fund_cnt", 0)
        risks    = r.get("fund_risks", "없음")
        etf_code = TICKER_SECTOR.get(r["ticker"].upper(), "")
        exc_items= SECTOR_EXCEPTIONS_LABEL.get(etf_code, "해당없음")
        jc       = "#16a34a" if "✅" in judge else \
                   "#d97706" if "⚠"  in judge else \
                   "#dc2626" if "🔴" in judge else "#9ca3af"
        fund_port_rows += f"""<tr style="background:{bg}">
  <td style="padding:10px 16px;font-weight:700;color:#7c3aed">{r["ticker"]}</td>
  <td style="padding:10px 16px;text-align:center;font-weight:700;color:{jc}">{judge}({cnt}/8)</td>
  <td style="padding:10px 16px;font-size:12px;color:#dc2626">{risks}</td>
  <td style="padding:10px 16px;font-size:12px;color:#9ca3af">{exc_items}</td>
</tr>"""
    fund_port_footnote = """<p style="font-size:12px;color:#6b7280;margin-top:6px;line-height:1.8">
  ※ 펀더멘털 체크리스트 항목 설명<br>
  ▪ <b>현금&lt;총부채</b> — 보유 현금이 총부채보다 적음 → 유동성 위기 가능성<br>
  ▪ <b>매출채권↑&gt;매출↑</b> — 매출채권 증가율이 매출보다 5%p↑ → 외상 매출, 현금 유입 불확실<br>
  ▪ <b>재고↑이익↓</b> — 재고 15%↑ 또는 순이익 마이너스 → 수요 감소 신호<br>
  ▪ <b>단기부채&gt;현금</b> — 단기 상환 의무 > 보유 현금 → 채무 상환 능력 부족<br>
  ▪ <b>무형자산N%</b> — 무형자산이 총자산 50% 초과 → 자산가치 변동성 증가<br>
  ▪ <b>기타자산N%</b> — 기타장기자산이 총자산 50% 초과 → 자산 구성 불투명<br>
  ▪ <b>우선주존재</b> — 우선주 발행 → 일반 주주보다 우선주 투자자에게 유리한 구조<br>
  ▪ <b>자본잠식</b> — 자기자본 음수 → 누적 손실로 자본 잠식, 상장폐지 위험<br>
  ▪ ✅ 양호(0개) &nbsp;|&nbsp; ⚠ 주의(1~2개) &nbsp;|&nbsp; 🔴 위험(3개 이상)
</p>"""

    # ── 보정 6개 이상 종목 차트 생성 ─────────
    chart_section = ""
    chart_tickers = [r for r in scan_results if r.get("adj_sig", 0) >= 6]
    if chart_tickers:
        chart_html = ""
        for r in chart_tickers:
            try:
                d_df, _ = prepare_df(r["ticker"])
                if d_df is not None:
                    img_b64 = generate_chart_base64(r["ticker"], d_df)
                    if img_b64:
                        chart_html += f"""
<div style="margin-bottom:20px">
  <p style="font-size:13px;font-weight:600;color:#1e40af;margin-bottom:6px">
    {r["ticker"]} — 현재가 ${r["price"]:.2f} | 
    매수신호 {r["signals"]}개 | 보정 {r["adj_sig"]}개 | 
    {r.get("strategy","C")} 전략 | {r.get("sector","미분류")}
  </p>
  <img src="data:image/png;base64,{img_b64}" 
       style="width:100%;max-width:900px;border:1px solid #e5e7eb;
              border-radius:8px">
</div>"""
            except Exception as e:
                chart_html += f'<p style="color:#9ca3af">[{r["ticker"]}] 차트 생성 실패: {e}</p>'

        chart_section = f"""
<h3 style="color:#dc2626;border-bottom:2px solid #dc2626;
           padding-bottom:6px;margin-top:24px">
  📊 주요 매수 후보 차트 — 보정신호 6개 이상 종목
  <small style="color:#6b7280;font-size:12px;font-weight:400">
    (일봉 180일 | MA/볼린저밴드/일목구름/RSI/MACD/Stoch)
  </small>
</h3>
{chart_html}"""

    fund_port_section = f"""
<h3 style="color:#0891b2;border-bottom:2px solid #0891b2;
           padding-bottom:6px;margin-top:24px">
  🔬 펀더멘털 체크리스트 — 내 포트폴리오
  <small style="color:#6b7280;font-size:13px;font-weight:400">
    (대차대조표 기준 8가지 위험 항목 | 섹터 특성 예외 반영)
  </small>
</h3>
<table style="width:100%;border-collapse:collapse;font-size:13px">
<thead><tr style="background:#0891b2;color:white">
  <th style="padding:11px 16px;text-align:left">종목</th>
  <th style="padding:11px 16px;text-align:center">판정</th>
  <th style="padding:11px 16px;text-align:left">위험 항목</th>
  <th style="padding:11px 16px;text-align:left">섹터 예외 적용</th>
</tr></thead><tbody>{fund_port_rows}</tbody></table>"""

    html = f"""<html><body style="font-family:Arial,sans-serif;max-width:1200px;
margin:0 auto;padding:16px">
<h2 style="color:#1e40af;border-bottom:3px solid #1e40af;padding-bottom:8px">
  📈 주식 분석 리포트 — {today}
</h2>
{sector_html}
{scan_section}
{fund_scan_section}
{fund_scan_footnote}
{port_section}
{fund_port_section}
{fund_port_footnote}
{chart_section}
<p style="color:#9ca3af;font-size:12px;margin-top:24px;
  border-top:1px solid #e5e7eb;padding-top:10px">
  자동 생성 | {datetime.now().strftime("%Y-%m-%d %H:%M KST")} | 투자 판단은 본인 책임
</p></body></html>"""

    try:
            msg = MIMEMultipart("related")
            msg["Subject"] = (f"📈 주식 시그널 {today} "
                              f"— 스캔 {len(scan_results)}종목 / "
                              f"포트폴리오 {len(port_results)}종목")
            msg["From"] = EMAIL_FROM
            msg["To"]   = EMAIL_TO if isinstance(EMAIL_TO, str) \
                          else ", ".join(EMAIL_TO)

            import re
            from email.mime.image import MIMEImage

            cid_map = {}
            def replace_b64(match):
                b64_data = match.group(1)
                cid = f"chart_{len(cid_map)}"
                cid_map[cid] = b64_data
                return f'cid:{cid}'

            html_cid = re.sub(
                r'data:image/png;base64,([A-Za-z0-9+/=]+)',
                replace_b64, html)

            alt = MIMEMultipart("alternative")
            alt.attach(MIMEText(html_cid, "html"))
            msg.attach(alt)

            import base64 as b64lib
            for cid, b64_data in cid_map.items():
                img_data = b64lib.b64decode(b64_data)
                mime_img = MIMEImage(img_data, _subtype="png")
                mime_img.add_header("Content-ID", f"<{cid}>")
                mime_img.add_header("Content-Disposition", "inline",
                                    filename=f"{cid}.png")
                msg.attach(mime_img)

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(EMAIL_FROM, EMAIL_PASSWORD)
                server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
            print(f"\n  ✅ 이메일 발송 완료 → {EMAIL_TO}")
    except Exception as e:
        print(f"\n  ⚠ 이메일 발송 실패: {e}")

# ════════════════════════════════════════════
#  7. 출력 함수
# ════════════════════════════════════════════
def print_scan_results(scan_results):
    if not scan_results:
        print("  신호 발생 종목 없음")
        return
    print(f"\n  {'종목':>6}  {'전략':>4}  {'현재가':>8}  {'신호':>3}  "
          f"{'보정':>3}  {'주봉':>3}  {'섹터':>8}  {'추세':>6}  "
          f"{'손절가':>8}  {'목표가':>8}  R/R  신호 상세")
    print("  " + "─"*108)

    # 출력 줄에 전략 추가
    for r in scan_results:
        sec   = r.get("sector","미분류")[:6]
        strat = r.get("strategy","C")
        print(f"  {r['ticker']:>6}  [{strat}]  ${r['price']:>7.2f}  "
              f"{r['signals']:>3}개  {r['adj_sig']:>3}개  {r['weekly']:>+3}  "
              f"{sec:>8}  {r.get('trend_type','미분류')[:4]:>6}  ${r['stop']:>7.2f}  ${r['target']:>7.2f}  "
              f"1:{r['rr']:.1f}  {r['details'][:25]}")

def print_portfolio_results(port_results):
    if not port_results:
        print("  포트폴리오 없음")
        return
    print(f"\n  {'종목':>6}  {'매수가':>7}  {'현재가':>7}  {'수익률':>7}  "
          f"{'손절가':>7}  {'목표가':>7}  {'신호':>3}  상태")
    print("  " + "─"*75)
    for r in port_results:
        print(f"  {r['ticker']:>6}  ${r['buy_price']:>6.2f}  "
              f"${r['cur_price']:>6.2f}  {r['pnl_pct']:>+6.2f}%  "
              f"${r['stop']:>6.2f}  ${r['target']:>6.2f}  "
              f"{r['signals']:>3}개  {r['status']}")

# ════════════════════════════════════════════
#  8. 통합 실행
# ════════════════════════════════════════════
def daily_job():
    import json, os

    # 섹터 분석
    sector_data = analyze_sectors()
    print_sector_summary(sector_data)

    # 섹터 맵 캐시 로드
    if os.path.exists("sector_map_cache.json"):
        with open("sector_map_cache.json", "r") as f:
            sector_map = json.load(f)
        print(f"  섹터 맵 로드: {len(sector_map)}종목")
    else:
        sector_map = {}
        print("  ⚠ sector_map_cache.json 없음 — 섹터 가중치 미적용")

    scan_res = run_market_scan(sector_data, sector_map)
    print_scan_results(scan_res)

    port_res = run_portfolio_update(sector_map, sector_data)
    print_portfolio_results(port_res)

    today = datetime.now().strftime("%Y%m%d")
    if scan_res:
        pd.DataFrame(scan_res).to_csv(
            f"scan_result_{today}.csv", index=False, encoding="utf-8-sig")
        print(f"\n  스캔 결과 저장: scan_result_{today}.csv")
    if port_res:
        pd.DataFrame(port_res).to_csv(
            f"portfolio_update_{today}.csv", index=False, encoding="utf-8-sig")
        print(f"  포트폴리오 저장: portfolio_update_{today}.csv")

    if EMAIL_FROM != "your_email@gmail.com":
        send_email(scan_res, port_res, sector_data)
    else:
        print("\n  ⚠ 이메일 미설정")

# ════════════════════════════════════════════
#  9. 스케줄러 (Jupyter에서 실행)
# ════════════════════════════════════════════
if __name__ == "__main__":
    import sys
    from apscheduler.schedulers.blocking import BlockingScheduler

    if "--now" in sys.argv:
        print("▶ 즉시 실행 모드")
        daily_job()
    else:
        print(f"▶ 스케줄러 시작 — 매일 KST {SCHEDULE_HOUR:02d}:{SCHEDULE_MINUTE:02d} 자동 실행")
        scheduler = BlockingScheduler(timezone="Asia/Seoul")
        scheduler.add_job(
            daily_job,
            "cron",
            hour=SCHEDULE_HOUR,
            minute=SCHEDULE_MINUTE,
            id="daily_scan"
        )
        try:
            scheduler.start()
        except KeyboardInterrupt:
            print("\n  스케줄러 종료")

