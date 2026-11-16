"""점수 규칙을 한곳에 모은다. 채점 방식이 바뀌면 이 파일만 고친다."""

POINTS_PER_CORRECT = 2  # 정답 한 문제당 더하는 점수
HINT_PENALTY = 1  # 힌트를 사용한 문제 한 개당 빼는 점수


def calculate_score(correct_count: int, hints_used: int) -> int:
    """정답 수와 힌트 사용 수로 한 판의 점수를 계산하며 0점 아래로 내려가지 않는다."""
    return max(0, correct_count * POINTS_PER_CORRECT - hints_used * HINT_PENALTY)
