"""실제 CLI를 임시 복사본에서 실행해 재현 가능한 제출 증거를 만든다.

게임 화면을 흉내 내지 않고 subprocess의 실제 stdout/stderr를 기록한다.
프로젝트의 state.json은 읽거나 수정하지 않는다. 외부 라이브러리는 필요 없다.
"""

import json
import os
from pathlib import Path
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from defaults import create_default_quizzes
from state_io import save_state

EVIDENCE = ROOT / "docs" / "evidence"


def write_log(name: str, title: str, inputs: str, result: subprocess.CompletedProcess) -> None:
    """입력과 실제 출력을 분리해, 파이프 입력이 화면에 에코된 것처럼 꾸미지 않는다."""
    text = (
        f"{title}\n"
        f"캡처 시각: {datetime.now().astimezone().isoformat(timespec='seconds')}\n"
        "실행: python3 main.py (임시 복사본)\n"
        "프로젝트 원본 데이터는 변경하지 않음\n"
        f"입력 순서: {inputs!r}\n"
        f"종료 코드: {result.returncode}\n"
        "\n===== 실제 프로그램 출력 =====\n"
        f"{result.stdout}{result.stderr}"
    )
    (EVIDENCE / f"{name}.txt").write_text(text, encoding="utf-8")


def run_cli(directory: Path, name: str, title: str, inputs: str) -> None:
    """실제 main.py를 별도 프로세스로 실행하고 종료 코드·오류 추적 유무를 확인한다."""
    result = subprocess.run(
        [sys.executable, "-u", "main.py"], cwd=directory,
        input=inputs, capture_output=True, text=True, encoding="utf-8", timeout=10,
    )
    write_log(name, title, inputs, result)
    if result.returncode != 0 or "Traceback" in result.stderr:
        raise RuntimeError(f"{name} CLI 검증 실패")


def capture_ctrl_c(directory: Path) -> None:
    """입력 프롬프트까지 확인한 뒤 실제 SIGINT를 보내 안전 종료를 검증한다."""
    process = subprocess.Popen(
        [sys.executable, "-u", "main.py"], cwd=directory,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    before = bytearray()
    deadline = time.monotonic() + 8
    try:
        while "메뉴 번호:".encode("utf-8") not in before:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or process.poll() is not None:
                raise RuntimeError("Ctrl+C 검사 전 메뉴 대기 실패")
            ready, _, _ = select.select([process.stdout], [], [], remaining)
            if ready:
                before.extend(os.read(process.stdout.fileno(), 4096))
        process.send_signal(signal.SIGINT)
        after, errors = process.communicate(timeout=8)
    except BaseException:
        process.kill()
        process.communicate()
        raise
    result = subprocess.CompletedProcess(
        process.args, process.returncode,
        (before + after).decode("utf-8"), errors.decode("utf-8"),
    )
    write_log("ctrl-c", "실제 SIGINT(Ctrl+C) 안전 종료", "메뉴에서 SIGINT 전송", result)
    if result.returncode != 0 or "안전하게" not in result.stdout:
        raise RuntimeError("Ctrl+C 안전 종료 검증 실패")


def main() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    # 임시 데이터는 정답을 모두 2번에 배치해 랜덤 순서와 무관하게 점수를 재현한다.
    # 문제·실제 정답 내용은 유지하며, 이 재배치는 제출용 기본 데이터에는 적용하지 않는다.
    quizzes = []
    for quiz in create_default_quizzes():
        item = quiz.to_dict()
        correct_index = item["answer"] - 1
        item["choices"][1], item["choices"][correct_index] = (
            item["choices"][correct_index], item["choices"][1]
        )
        item["answer"] = 2
        quizzes.append(item)

    with tempfile.TemporaryDirectory(prefix="e1-2-evidence-") as temporary:
        directory = Path(temporary)
        for source in ROOT.glob("*.py"):
            shutil.copy2(source, directory / source.name)
        save_state(directory / "state.json", {"quizzes": quizzes, "best_score": 0})
        run_cli(directory, "menu", "메뉴와 정상 종료", "0\n")
        addition = "2\nPython에서 함수를 정의하는 키워드는?\nclass\ndef\nfor\nwhile\n2\n영어 define의 앞부분입니다.\n0\n"
        run_cli(directory, "add-quiz", "새 퀴즈 등록과 즉시 파일 저장", addition)
        run_cli(directory, "list", "추가한 문제를 포함한 퀴즈 목록", "3\n0\n")
        run_cli(directory, "play", "랜덤 3문제와 힌트 중복 차감 방지", "1\n3\nh\nh\n2\n2\n2\n0\n")
        state = json.loads((directory / "state.json").read_text(encoding="utf-8"))
        assert len(state["quizzes"]) == 9
        assert state["best_score"] == 5
        assert state["history"][-1]["hints_used"] == 1
        run_cli(directory, "score", "최고 점수 조회", "4\n0\n")
        run_cli(directory, "history", "날짜·시각·문제 수·점수 히스토리", "6\n0\n")
        run_cli(directory, "restart", "별도 실행 프로세스에서 추가 퀴즈와 5점 유지", "3\n4\n0\n")
        run_cli(directory, "delete", "퀴즈 삭제 확인과 저장", "5\n9\n1\n0\n")
        run_cli(directory, "invalid-input", "빈 입력·문자·범위 밖·앞뒤 공백 처리", "\nabc\n9\n 0 \n")
        run_cli(directory, "eof", "빈 표준 입력(EOF)에서 안전 종료", "")
        capture_ctrl_c(directory)
        # 정상 게임을 했던 복사본만 손상시킨다. 원본은 끝까지 접근하지 않는다.
        (directory / "state.json").write_text('{"quizzes": [', encoding="utf-8")
        run_cli(directory, "corrupt-recovery", "잘린 JSON 감지·원본 백업·기본값 복구", "0\n")
        assert list(directory.glob("*.bak"))
        restored = json.loads((directory / "state.json").read_text(encoding="utf-8"))
        assert len(restored["quizzes"]) == 8
    print("12개 실제 CLI 시나리오 증거 생성 및 검증 완료")


if __name__ == "__main__":
    main()
