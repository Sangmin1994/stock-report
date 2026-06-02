"""
GitHub Actions 실행 스크립트
1. scanner_portpolio_v4.ipynb 실행 (jupyter nbconvert)
2. 노트북 stdout 출력 전체를 섹션별로 텔레그램 전송
   (섹터/스캔/포트폴리오/가치사슬/실적 등 모든 리포트 포함)
"""
import subprocess
import sys
import json
import re
from datetime import datetime
from telegram_notify import send_message, send_daily_report

NB_PATH = "scanner_portpolio_v4.ipynb"
TIMEOUT = 7200  # 초 (최대 2시간)
MAX_CHARS = 3800


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


def extract_notebook_text(nb_path: str) -> str:
    """실행된 노트북에서 모든 텍스트 출력(stdout + display_data)을 추출"""
    with open(nb_path, "r", encoding="utf-8") as f:
        nb = json.load(f)

    parts = []
    for cell in nb["cells"]:
        if cell["cell_type"] != "code":
            continue
        for output in cell.get("outputs", []):
            otype = output.get("output_type", "")

            # print() 출력
            if otype == "stream" and output.get("name") == "stdout":
                text = output.get("text", [])

            # display(HTML(...)) 등 — text/plain 버전 사용
            elif otype in ("display_data", "execute_result"):
                text = output.get("data", {}).get("text/plain", [])

            else:
                continue

            if isinstance(text, list):
                text = "".join(text)
            if text.strip():
                parts.append(text.strip())

    return "\n\n".join(parts)


def send_notebook_report(nb_path: str) -> None:
    """노트북 출력을 섹션별로 분할해 텔레그램 전송"""
    full_text = extract_notebook_text(nb_path)
    if not full_text.strip():
        print("[노트북] stdout 출력 없음 — CSV 기반 리포트만 전송")
        return

    # 줄 시작의 ===... 구분선으로 섹션 분리 (들여쓰기된 ─── 행은 제외)
    sections = re.split(r"(?m)^={40,}$", full_text)
    sections = [s.strip() for s in sections if s.strip()]

    if not sections:
        print("[노트북] 섹션 구분선 없음 — 전체 텍스트를 통으로 전송")
        sections = [full_text]

    print(f"[노트북] {len(sections)}개 섹션 전송")
    for section in sections:
        safe = (
            section
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        for i in range(0, len(safe), MAX_CHARS):
            send_message(f"<pre>{safe[i:i + MAX_CHARS]}</pre>")


if __name__ == "__main__":
    send_message("🔄 주식 스캔을 시작합니다…")
    ok = run_notebook()
    if ok:
        # ① CSV 기반 리포트 (스캔 결과 + 포트폴리오)
        send_daily_report()
        # ② 노트북 출력 기반 리포트 (섹터/가치사슬/실적 등 전체)
        send_notebook_report(NB_PATH)
        send_message("✅ 스캔 완료")
    else:
        send_message("❌ 스캔 실패 — GitHub Actions 로그를 확인하세요.")
    sys.exit(0 if ok else 1)
