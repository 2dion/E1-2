"""점수 규칙과 선택지 개수가 한곳에서 관리되는지 확인한다."""

import unittest

from quiz import CHOICE_COUNT, Quiz
from scoring import HINT_PENALTY, POINTS_PER_CORRECT, calculate_score


class ScoringTests(unittest.TestCase):
    """채점 방식이 바뀌어도 수정 범위가 scoring.py로 모이는지 검사한다."""

    def test_mission_rule_examples(self):
        """정답 +2점, 힌트 -1점 규칙의 대표 사례를 계산한다."""
        self.assertEqual((POINTS_PER_CORRECT, HINT_PENALTY), (2, 1))
        self.assertEqual(calculate_score(3, 1), 5)
        self.assertEqual(calculate_score(0, 0), 0)
        self.assertEqual(calculate_score(8, 0), 16)

    def test_score_never_below_zero(self):
        """힌트를 정답보다 많이 써도 0점 아래로 내려가지 않는다."""
        self.assertEqual(calculate_score(0, 3), 0)
        self.assertEqual(calculate_score(1, 5), 0)


class ChoiceCountTests(unittest.TestCase):
    """선택지 개수 상수가 Quiz 검증 범위와 일치하는지 검사한다."""

    def test_quiz_uses_choice_count(self):
        """보기 수와 정답 범위가 CHOICE_COUNT를 따른다."""
        choices = [f"보기{n}" for n in range(1, CHOICE_COUNT + 1)]
        quiz = Quiz("질문", choices, CHOICE_COUNT)
        self.assertTrue(quiz.is_correct(CHOICE_COUNT))
        self.assertFalse(quiz.is_correct(CHOICE_COUNT + 1))
        with self.assertRaises(ValueError):
            Quiz("질문", choices[:-1], 1)
        with self.assertRaises(ValueError):
            Quiz("질문", choices, CHOICE_COUNT + 1)


if __name__ == "__main__":
    unittest.main()
