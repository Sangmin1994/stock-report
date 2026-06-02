"""
GitHub Actions 실행 스크립트
1. scanner_portpolio_v4.ipynb 실행 (jupyter nbconvert)
2. 완료 후 텔레그램으로 결과 전송
"""
import subprocess
import sys
import os
from datetime import datetime
from telegram_notify import send_message, send_daily_report

NB_PATH = "scanner_portpolio_v4.ipynb"
TIMEOUT = 7200  # 초 (최대 2시간)


def run_notebook() -> bool:
    print(f"[{datetime.now():%H:%M:%S}] 노트북 실행 시작: {NB_PATH}")
    result = subprocess.run(
        [
            sys.executable, "-m", "jupyter", "nbconvert",
            "--to", "notebook",
            "--execute",
            f"--ExecutePreprocessor.timeout={TIMEOUT}",
            "--ExecutePreprocessor.kernel_name=python3",
            "--inplace",
            NB_PATH,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("=== STDERR (마지막 3000자) ===")
        print(result.stderr[-3000:])
        return False
    print(f"[{datetime.now():%H:%M:%S}] 노트북 실행 완료")
    return True


if __name__ == "__main__":
    send_message("🔄 주식 스캔 시작됩니다…")
    ok = run_notebook()
    if ok:
        send_daily_report()
    else:
        send_message("❌ 스캔 실패 — GitHub Actions 로그를 확인하세요.")
    sys.exit(0 if ok else 1)
