"""퀴즈 상태를 검증하고 UTF-8 JSON 파일로 안전하게 저장한다."""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

from quiz import Quiz


def _integer(value: object, name: str, minimum: int, maximum=None) -> int:
    """bool을 제외한 정수의 범위를 검사한다."""
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name}은(는) {minimum} 이상의 정수여야 합니다.")
    if maximum is not None and value > maximum:
        raise ValueError(f"{name}은(는) {maximum} 이하여야 합니다.")
    return value


def _history_record(record: dict) -> dict:
    """기록 한 개를 끝까지 검사한 후 독립적인 딕셔너리로 복사한다."""
    fields = (
        "played_at", "question_count", "answered_count", "correct_count",
        "hints_used", "score", "completed",
    )
    if type(record) is not dict or any(key not in record for key in fields):
        raise ValueError("진행 기록에는 모든 필수 항목이 있어야 합니다.")

    played_at = record["played_at"]
    if not isinstance(played_at, str):
        raise ValueError("played_at은 시간대가 포함된 ISO 날짜·시간 문자열이어야 합니다.")
    # Python 3.10에서도 UTC를 뜻하는 ISO 접미사 Z를 지원한다.
    iso_value = played_at[:-1] + "+00:00" if played_at.endswith("Z") else played_at
    try:
        parsed = datetime.fromisoformat(iso_value)
    except ValueError as exc:
        raise ValueError("played_at의 ISO 날짜·시간 형식이 올바르지 않습니다.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("played_at에는 시간대가 필요합니다.")

    questions = _integer(record["question_count"], "question_count", 1)
    answered = _integer(record["answered_count"], "answered_count", 0, questions)
    correct = _integer(record["correct_count"], "correct_count", 0, answered)
    hints = _integer(record["hints_used"], "hints_used", 0, questions)
    score = _integer(record["score"], "score", 0)
    if score != max(0, correct * 2 - hints):
        raise ValueError("score가 정답 수와 힌트 수로 계산한 점수와 다릅니다.")
    completed = record["completed"]
    if type(completed) is not bool:
        raise ValueError("completed는 bool이어야 합니다.")
    if completed and answered != questions:
        raise ValueError("완료한 기록은 모든 문제에 응답해야 합니다.")
    return {key: record[key] for key in fields}


def validate_state(data: dict) -> dict:
    """상태 전체를 검증한 뒤 기본값을 채운 새 JSON 호환 딕셔너리를 반환한다.

    알 수 없는 항목은 버린다. 완료 기록이 있으면 has_played를 True로 보정하며,
    과거 최고 점수는 현재 문제 수나 남아 있는 기록으로 제한하지 않는다.
    """
    if type(data) is not dict:
        raise ValueError("상태는 딕셔너리여야 합니다.")
    if "quizzes" not in data or "best_score" not in data:
        raise ValueError("quizzes와 best_score 항목이 필요합니다.")
    version = _integer(data.get("schema_version", 1), "schema_version", 1, 1)
    best_score = _integer(data["best_score"], "best_score", 0)
    if type(data["quizzes"]) is not list:
        raise ValueError("quizzes는 리스트여야 합니다.")
    quizzes = [Quiz.from_dict(item).to_dict() for item in data["quizzes"]]

    raw_history = data.get("history", [])
    if type(raw_history) is not list:
        raise ValueError("history는 리스트여야 합니다.")
    history = [_history_record(record) for record in raw_history]
    has_played = data.get("has_played", best_score > 0)
    if type(has_played) is not bool:
        raise ValueError("has_played는 bool이어야 합니다.")
    has_played = has_played or any(record["completed"] for record in history)
    return {
        "schema_version": version,
        "quizzes": quizzes,
        "best_score": best_score,
        "has_played": has_played,
        "history": history,
    }


def load_state(path: Path) -> dict:
    """UTF-8 JSON 상태를 읽고 검증하며 파일·디코딩·검증 오류는 그대로 전달한다."""
    with path.open("r", encoding="utf-8") as stream:
        return validate_state(json.load(stream))


def save_state(path: Path, data: dict) -> None:
    """먼저 검증하고 같은 디렉터리의 임시 파일을 원자적으로 교체한다.

    부모 디렉터리는 만들지 않는다. 교체 전 오류가 나면 기존 파일을 보존하며,
    남은 임시 파일은 지운다. 정리할 파일이 이미 없을 때만 오류를 무시한다.
    """
    normalized = validate_state(data)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            json.dump(normalized, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass
