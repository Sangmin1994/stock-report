"""
GitHub Actions 실행 스크립트
1. scanner_portpolio_v4.ipynb 실행 (jupyter nbconvert)
2. 노트북의 텍스트 출력 전체를 섹션별로 텔레그램 전송
   (섹터/스캔/포트폴리오/가치사슬/실적 등 모든 리포트 포함)
"""
import subprocess
import sys
import os
import json
import re
from datetime import datetime
from telegram_notify import send_message

NB_PATH = "scanner_portpolio_v4.ipynb"
TIMEOUT = 7200  # 초 (최대 2시간)
MAX_CHARS = 3900  # 텔레그램 메시지 최대 길이 여유분


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


def extract_sections(nb_path: str) -> list:
    """
    실행된 노트북의 모든 stdout 텍스트를 추출하고
    ===... 구분선 기준으로 섹션 분할
    """
    with open(nb_path, "r", encoding="utf-8") as f:
        nb = json.load(f)

    parts = []
    for cell in nb["cells"]:
        if cell["cell_type"] != "code":
            continue
        for output in cell.get("outputs", []):
            if output.get("output_type") == "stream" and output.get("name") == "stdout":
                text = output.get("text", [])
                if isinstance(text, list):
                    text = "".join(text)
                if text.strip():
                    parts.append(text)

    combined = "\n".join(parts)

    # ===== 40자 이상 구분선으로 섹션 분리
    sections = re.split(r"={40,}", combined)
    return [s.strip() for s in sections if s.strip()]


def send_report(nb_path: str) -> None:
    """섹션별로 텔레그램 전송"""
    sections = extract_sections(nb_path)
    if not sections:
        send_message("⚠️ 노트북 출력 내용이 없습니다. 노트북이 정상 실행됐는지 확인하세요.")
        return

    for section in sections:
        # HTML 특수문자 이스케이프 (<pre> 블록 안에서 필요)
        safe = (
            section
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        # 너무 긴 섹션은 잘라서 전송
        if len(safe) <= MAX_CHARS:
            send_message(f"<pre>{safe}</pre>")
        else:
            # MAX_CHARS 단위로 분할
            for i in range(0, len(safe), MAX_CHARS):
                chunk = safe[i:i + MAX_CHARS]
                send_message(f"<pre>{chunk}</pre>")


if __name__ == "__main__":
    send_message("🔄 주식 스캔을 시작합니다…")
    ok = run_notebook()
    if ok:
        send_report(NB_PATH)
        send_message("✅ 스캔 완료")
    else:
        send_message("❌ 스캔 실패 — GitHub Actions 로그를 확인하세요.")
    sys.exit(0 if ok else 1)
