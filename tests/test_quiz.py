"""퀴즈가 데이터 검증과 정답 판정의 책임을 지키는지 확인한다."""

import io
import unittest
from contextlib import redirect_stdout

from quiz import Quiz


class QuizTests(unittest.TestCase):
    """외부 입력과 출력에 드러나는 퀴즈 동작을 검사한다."""

    def make_quiz(self, **changes):
        """각 테스트에서 필요한 항목만 바꿀 수 있는 퀴즈를 만든다."""
        values = {
            "question": "수도의 이름은?",
            "choices": ["서울", "부산", "인천", "대구"],
            "answer": 1,
        }
        values.update(changes)
        return Quiz(**values)

    def test_strips_unicode_question_choices_and_hint(self):
        """한글과 유니코드 문자는 보존하고 양끝 공백만 없앤다."""
        quiz = self.make_quiz(
            question=" \t대한민국의 수도는?\n",
            choices=[" 서울 ", "\t부산", "인천\n", " 제주 🏝 "],
            hint="  한강을 생각해 보세요.  ",
        )
        self.assertEqual(quiz.question, "대한민국의 수도는?")
        self.assertEqual(quiz.choices, ["서울", "부산", "인천", "제주 🏝"])
        self.assertEqual(quiz.hint, "한강을 생각해 보세요.")

    def test_rejects_invalid_question(self):
        """비어 있거나 문자열이 아닌 질문은 허용하지 않는다."""
        for question in ("", " \t\n", None, 1, True, []):
            with self.subTest(question=question), self.assertRaises(ValueError):
                self.make_quiz(question=question)

    def test_requires_exact_list_for_choices(self):
        """보기 묶음은 튜플이나 리스트 하위 클래스가 아닌 리스트여야 한다."""
        class Choices(list):
            pass

        for choices in (("a", "b", "c", "d"), "abcd", None, Choices("abcd")):
            with self.subTest(choices=choices), self.assertRaises(ValueError):
                self.make_quiz(choices=choices)

    def test_requires_exactly_four_choices(self):
        """보기 개수의 하한과 상한을 확인한다."""
        for count in (0, 1, 3, 5):
            with self.subTest(count=count), self.assertRaises(ValueError):
                self.make_quiz(choices=["보기"] * count)

    def test_rejects_blank_or_nonstring_choice(self):
        """보기 하나라도 비었거나 문자열이 아니면 거부한다."""
        for choice in ("", " \n\t", None, 3, True, []):
            with self.subTest(choice=choice), self.assertRaises(ValueError):
                self.make_quiz(choices=["가", choice, "다", "라"])

    def test_accepts_answer_boundaries(self):
        """정답 번호의 양 끝값인 1과 4를 허용한다."""
        for answer in (1, 4):
            with self.subTest(answer=answer):
                quiz = self.make_quiz(answer=answer)
                self.assertEqual(quiz.answer, answer)
                self.assertTrue(quiz.is_correct(answer))

    def test_rejects_invalid_answer_including_bool(self):
        """범위를 벗어난 정수와 bool 등 다른 타입은 정답이 될 수 없다."""
        for answer in (0, -1, 5, True, False, 1.0, "1", None):
            with self.subTest(answer=answer), self.assertRaises(ValueError):
                self.make_quiz(answer=answer)

    def test_hint_defaults_to_empty_and_requires_string(self):
        """힌트는 생략하거나 공백으로 둘 수 있지만 문자열이어야 한다."""
        self.assertEqual(self.make_quiz().hint, "")
        self.assertEqual(self.make_quiz(hint=" \t ").hint, "")
        for hint in (None, 1, True, []):
            with self.subTest(hint=hint), self.assertRaises(ValueError):
                self.make_quiz(hint=hint)

    def test_constructor_copies_input_choices(self):
        """생성 후 원본 리스트를 고쳐도 퀴즈의 보기는 바뀌지 않는다."""
        choices = ["가", "나", "다", "라"]
        quiz = self.make_quiz(choices=choices)
        choices[0] = "변경"
        choices.append("추가")
        self.assertEqual(quiz.choices, ["가", "나", "다", "라"])

    def test_is_correct_distinguishes_valid_selections(self):
        """네 개의 유효한 선택 중 정답에만 True를 반환한다."""
        quiz = self.make_quiz(answer=3)
        for selected in range(1, 5):
            with self.subTest(selected=selected):
                self.assertIs(quiz.is_correct(selected), selected == 3)

    def test_invalid_selection_returns_false_without_raising(self):
        """선택 오류는 예외 대신 False로 처리하며 bool도 거부한다."""
        quiz = self.make_quiz()
        for selected in (0, -1, 5, True, False, 1.0, "1", None, [], {}):
            with self.subTest(selected=selected):
                self.assertIs(quiz.is_correct(selected), False)

    def test_to_dict_has_expected_values_and_defensive_copy(self):
        """내보낸 데이터의 키와 값을 확인하고 수정 영향이 없는지 검사한다."""
        quiz = self.make_quiz(hint="한강")
        data = quiz.to_dict()
        self.assertEqual(data, {
            "question": "수도의 이름은?",
            "choices": ["서울", "부산", "인천", "대구"],
            "answer": 1,
            "hint": "한강",
        })
        data["choices"][0] = "변경"
        data["question"] = "새 질문"
        self.assertEqual(quiz.question, "수도의 이름은?")
        self.assertEqual(quiz.choices[0], "서울")
        self.assertIsNot(quiz.to_dict()["choices"], quiz.choices)

    def test_from_dict_restores_with_optional_hint_and_copy(self):
        """복원 시 기본 힌트, 문자열 정리, 원본 보기 복사를 적용한다."""
        data = {
            "question": " 수도는? ",
            "choices": [" 서울 ", "부산", "인천", "대구"],
            "answer": 1,
        }
        quiz = Quiz.from_dict(data)
        self.assertEqual(quiz.question, "수도는?")
        self.assertEqual(quiz.hint, "")
        data["choices"][0] = "변경"
        self.assertEqual(quiz.choices[0], "서울")
        self.assertEqual(Quiz.from_dict(quiz.to_dict()).to_dict(), quiz.to_dict())
        data["hint"] = " 힌트 "
        self.assertEqual(Quiz.from_dict(data).hint, "힌트")

    def test_from_dict_rejects_wrong_container_or_missing_fields(self):
        """딕셔너리가 아니거나 필수 항목이 빠지면 ValueError를 발생시킨다."""
        class Data(dict):
            pass

        valid = self.make_quiz().to_dict()
        invalid = [None, [], "데이터", Data(valid), {}]
        invalid.extend({key: value for key, value in valid.items() if key != missing}
                       for missing in ("question", "choices", "answer"))
        for data in invalid:
            with self.subTest(data=data), self.assertRaises(ValueError):
                Quiz.from_dict(data)

    def test_from_dict_validates_every_field(self):
        """딕셔너리 복원도 생성자와 동일한 검증 규칙을 따른다."""
        for field, value in (("question", " "), ("choices", ["a"]),
                             ("answer", True), ("answer", 5), ("hint", None)):
            data = self.make_quiz().to_dict()
            data[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                Quiz.from_dict(data)

    def test_display_prints_question_and_numbered_choices_only(self):
        """출력에는 질문과 번호 매긴 보기만 있고 정답과 힌트는 없다."""
        quiz = self.make_quiz(hint="비공개 힌트")
        output = io.StringIO()
        with redirect_stdout(output):
            result = quiz.display()
        self.assertIsNone(result)
        self.assertEqual(output.getvalue(), "수도의 이름은?\n1. 서울\n2. 부산\n3. 인천\n4. 대구\n")


if __name__ == "__main__":
    unittest.main()
