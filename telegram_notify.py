"""
텔레그램 알림 모듈
- TELEGRAM_TOKEN, TELEGRAM_CHAT_ID 환경변수로 설정
"""
import os
import requests
import pandas as pd
from datetime import datetime


TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

MAX_LEN = 4000  # 텔레그램 최대 4096자


def _send_raw(text: str) -> bool:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("[텔레그램] TELEGRAM_TOKEN / TELEGRAM_CHAT_ID 환경변수 없음 — 전송 생략")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        resp = requests.post(url, data=payload, timeout=15)
        if not resp.ok:
            print(f"[텔레그램] 전송 실패 {resp.status_code}: {resp.text[:300]}")
        return resp.ok
    except Exception as e:
        print(f"[텔레그램] 전송 오류: {e}")
        return False


def send_message(text: str) -> bool:
    """긴 메시지는 자동 분할 전송"""
    if not text:
        return True
    chunks = [text[i:i + MAX_LEN] for i in range(0, len(text), MAX_LEN)]
    ok = True
    for chunk in chunks:
        ok = _send_raw(chunk) and ok
    return ok


# ─── 스캔 결과 메시지 ────────────────────────────────────────────────────────

def build_scan_report(today: str = None) -> str:
    if today is None:
        today = datetime.now().strftime("%Y%m%d")
    csv_path = f"scan_result_{today}.csv"
    if not os.path.exists(csv_path):
        return ""

    df = pd.read_csv(csv_path, encoding="utf-8-sig")

    # 우선순위 정렬
    _pri = {"🔥 최우선": 0, "✅ 관심": 1, "⭐ 참고": 2}
    if "priority" in df.columns:
        df["_pri"] = df["priority"].map(_pri).fillna(99)
        df = df.sort_values(["_pri", "signals"], ascending=[True, False])

    date_str = f"{today[:4]}-{today[4:6]}-{today[6:]}"
    lines = [
        f"<b>📊 주식 스캔 결과 — {date_str}</b>",
        f"총 신호 종목: <b>{len(df)}개</b>\n",
    ]

    for _, r in df.head(10).iterrows():
        priority = r.get("priority", "") or ""
        if not isinstance(priority, str):
            priority = ""
        ticker   = r["ticker"]
        price    = r["price"]
        strategy = r.get("strategy", "—")
        trend    = r.get("trend_type", "—")
        sector   = str(r.get("sector", "—")).replace("<", "").replace(">", "")
        stop     = r.get("stop", "")
        target   = r.get("target", "")
        rr       = r.get("rr", "")
        sigs     = int(r.get("signals", 0))
        growth   = r.get("growth_grade", "")

        lines.append(
            f"{priority} <b>{ticker}</b>  ${price:.2f}  [{strategy}전략]\n"
            f"  섹터: {sector} | 추세: {trend} | 신호: {sigs}개 {growth}\n"
            f"  손절: <code>${stop}</code>  목표: <code>${target}</code>  R/R {rr}\n"
        )

    if len(df) > 10:
        lines.append(f"… 외 {len(df) - 10}개 종목 (CSV 파일 참조)")

    return "\n".join(lines)


# ─── 포트폴리오 현황 메시지 ──────────────────────────────────────────────────

def build_portfolio_report(today: str = None) -> str:
    if today is None:
        today = datetime.now().strftime("%Y%m%d")
    csv_path = f"portfolio_update_{today}.csv"
    if not os.path.exists(csv_path):
        return ""

    df = pd.read_csv(csv_path, encoding="utf-8-sig")

    total_eval = df["eval_amt"].sum() if "eval_amt" in df.columns else 0
    total_pnl  = df["pnl_amt"].sum()  if "pnl_amt"  in df.columns else 0
    pnl_sign   = "📈" if total_pnl >= 0 else "📉"

    date_str = f"{today[:4]}-{today[4:6]}-{today[6:]}"
    lines = [
        f"<b>💼 포트폴리오 현황 — {date_str}</b>",
        f"평가금액: <b>${total_eval:,.0f}</b>  "
        f"평가손익: <b>{pnl_sign} ${total_pnl:,.0f}</b>\n",
    ]

    for _, r in df.iterrows():
        ticker   = r["ticker"]
        pnl_pct  = float(r.get("pnl_pct", 0))
        status   = r.get("status", "—")
        icon     = "📈" if pnl_pct >= 0 else "📉"
        stop_d   = r.get("stop_dist", "")
        tgt_d    = r.get("target_dist", "")

        lines.append(
            f"{icon} <b>{ticker}</b>  {pnl_pct:+.2f}%\n"
            f"  상태: {status}\n"
            f"  손절까지: {stop_d}%  목표까지: {tgt_d}%\n"
        )

    return "\n".join(lines)


# ─── 일일 리포트 전송 ────────────────────────────────────────────────────────

def send_daily_report(today: str = None) -> None:
    if today is None:
        today = datetime.now().strftime("%Y%m%d")

    scan_msg = build_scan_report(today)
    if scan_msg:
        send_message(scan_msg)
        print("[텔레그램] 스캔 결과 전송 완료")
    else:
        send_message(f"⚠️ {today} 스캔 결과 파일을 찾을 수 없습니다.")

    port_msg = build_portfolio_report(today)
    if port_msg:
        send_message(port_msg)
        print("[텔레그램] 포트폴리오 현황 전송 완료")
    else:
        send_message(f"⚠️ {today} 포트폴리오 업데이트 파일을 찾을 수 없습니다.")
