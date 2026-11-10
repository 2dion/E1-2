"""입력 재시도와 종료 신호의 전달을 표준 라이브러리만으로 확인한다."""

import io
import unittest
from contextlib import redirect_stdout
from unittest import mock

from input_utils import read_int, read_text


class InputUtilsTests(unittest.TestCase):
    """실제 터미널 대신 입력 모의와 출력 버퍼를 사용한다."""

    def setUp(self):
        self.output = io.StringIO()
        self.addCleanup(self.output.close)
        capture = redirect_stdout(self.output)
        capture.__enter__()
        self.addCleanup(capture.__exit__, None, None, None)

    def test_integer_retries_blank_and_whitespace(self):
        """빈 줄과 공백 줄은 각각 안내하고 다시 읽는다."""
        with mock.patch("builtins.input", side_effect=["", " \t ", "2"]) as read:
            self.assertEqual(read_int("번호: ", 1, 4), 2)
        self.assertEqual(read.call_count, 3)
        self.assertEqual(self.output.getvalue().count("입력이 비어 있습니다"), 2)

    def test_integer_retries_non_number(self):
        """abc를 숫자로 오인하거나 예외로 종료하지 않는다."""
        with mock.patch("builtins.input", side_effect=["abc", "3"]):
            self.assertEqual(read_int("번호: ", 1, 4), 3)
        self.assertIn("숫자로 입력", self.output.getvalue())

    def test_integer_retries_both_out_of_range_sides(self):
        """허용 범위보다 작은 수와 큰 수를 모두 거절한다."""
        with mock.patch("builtins.input", side_effect=["0", "5", "1"]):
            self.assertEqual(read_int("번호: ", 1, 4), 1)
        self.assertEqual(self.output.getvalue().count("1~4 범위"), 2)

    def test_integer_strips_and_accepts_upper_boundary(self):
        """숫자 주변 공백을 제거하고 최댓값을 받아들인다."""
        with mock.patch("builtins.input", return_value=" \t4\n") as read:
            self.assertEqual(read_int("정답: ", 1, 4), 4)
        read.assert_called_once_with("정답: ")
        self.assertEqual(self.output.getvalue(), "")

    def test_text_retries_blank_then_strips_valid_text(self):
        """빈 내용은 반복하고 한글 내용의 양끝 공백만 제거한다."""
        with mock.patch("builtins.input", side_effect=["", " \t ", " 질문 내용 \n"]) as read:
            self.assertEqual(read_text("문제: "), "질문 내용")
        self.assertEqual(read.call_count, 3)
        self.assertEqual(self.output.getvalue().count("내용이 비어 있습니다"), 2)

    def test_eof_propagates_from_both_readers(self):
        """입력 끝은 재시도하지 않고 호출자에게 같은 예외로 전달한다."""
        for reader, args in ((read_int, ("번호: ", 0, 6)), (read_text, ("내용: ",))):
            error = EOFError("입력 끝")
            with self.subTest(reader=reader.__name__), mock.patch("builtins.input", side_effect=error) as read:
                with self.assertRaises(EOFError) as caught:
                    reader(*args)
                self.assertIs(caught.exception, error)
                read.assert_called_once()

    def test_keyboard_interrupt_propagates_after_retry(self):
        """잘못된 입력 뒤의 Ctrl+C도 삼키지 않는다."""
        for reader, args in ((read_int, ("번호: ", 0, 6)), (read_text, ("내용: ",))):
            error = KeyboardInterrupt()
            with self.subTest(reader=reader.__name__), mock.patch("builtins.input", side_effect=["", error]) as read:
                with self.assertRaises(KeyboardInterrupt) as caught:
                    reader(*args)
                self.assertIs(caught.exception, error)
                self.assertEqual(read.call_count, 2)


if __name__ == "__main__":
    unittest.main()
