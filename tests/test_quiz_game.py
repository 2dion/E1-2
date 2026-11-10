"""게임의 입력·기록·복구를 프로젝트 상태 파일과 분리해 검사한다."""

import io
import json
import os
import random
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from unittest import mock

from defaults import create_default_quizzes
from quiz import Quiz
from quiz_game import QuizGame
from state_io import load_state


class QuizGameTests(unittest.TestCase):
    """모든 게임은 명시한 임시 state_path와 모의 입력만 사용한다."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.state_path = self.root / "state.json"
        self.output = io.StringIO()
        self.addCleanup(self.output.close)
        # enterContext는 Python 3.11 기능이므로 3.10에서도 되는 정리 방식을 쓴다.
        capture = redirect_stdout(self.output)
        capture.__enter__()
        self.addCleanup(capture.__exit__, None, None, None)
        patcher = mock.patch("builtins.input", side_effect=AssertionError("예상하지 않은 입력"))
        self.input = patcher.start()
        self.addCleanup(patcher.stop)
        self.game = QuizGame(state_path=self.state_path, rng=random.Random(7))
        self.clear_output()

    def clear_output(self):
        """현재 동작의 안내만 비교할 수 있도록 출력 버퍼를 비운다."""
        self.output.seek(0)
        self.output.truncate(0)

    def new_game(self, **kwargs):
        """재시작도 반드시 같은 임시 파일을 명시한다."""
        return QuizGame(state_path=self.state_path, **kwargs)

    def quizzes(self, count=1, hint="힌트"):
        """정답이 일정한 독립 문제로 무작위 순서와 점수를 쉽게 확인한다."""
        return [Quiz(f"질문 {index}", ["보기 가", "보기 나", "보기 다", "보기 라"], 1, hint)
                for index in range(count)]

    def seed(self, count=1, hint="힌트"):
        """정상 원본을 먼저 저장하여 이후의 무변경·실패를 비교한다."""
        self.game.quizzes = self.quizzes(count, hint)
        self.game.dirty = True
        self.assertTrue(self.game.save_state())
        self.clear_output()

    def record(self):
        """저장된 마지막 기록도 스키마 검증을 통과해야 한다."""
        state = load_state(self.state_path)
        self.assertEqual(state["history"], self.game.history)
        return state["history"][-1]

    def check_corrupt_recovery(self, original):
        """손상 원본의 바이트 백업 후 정상 기본값으로 복구되는지 확인한다."""
        self.state_path.write_bytes(original)
        game = self.new_game()
        backups = list(self.root.glob("state.json.corrupt-*.bak"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), original)
        self.assertEqual(self.state_path.read_bytes(), original)
        self.assertTrue(game.write_allowed)
        self.assertTrue(game.dirty)
        self.assertEqual(len(game.quizzes), 8)
        self.assertIn("손상", self.output.getvalue())
        self.assertIn("백업했습니다", self.output.getvalue())
        self.assertTrue(game.save_state())
        self.assertEqual(load_state(self.state_path), game.to_state())
        self.assertFalse(game.dirty)
        self.assertEqual(backups[0].read_bytes(), original)
        self.assertEqual(self.new_game().to_state(), game.to_state())

    def test_missing_file_uses_defaults_without_early_write(self):
        """없는 파일은 기본 여덟 문제로 시작하고 저장 전에는 생성하지 않는다."""
        game = self.new_game()
        self.assertEqual([q.to_dict() for q in game.quizzes],
                         [q.to_dict() for q in create_default_quizzes()])
        self.assertEqual(len(game.quizzes), 8)
        self.assertEqual((game.best_score, game.has_played, game.history), (0, False, []))
        self.assertTrue(game.dirty)
        self.assertFalse(self.state_path.exists())
        self.assertIn("데이터 파일이 없어", self.output.getvalue())
        self.assertTrue(game.save_state())
        self.assertEqual(load_state(self.state_path), game.to_state())

    def test_add_valid_persists_and_restarts(self):
        """모든 항목을 받은 문제는 정리한 값으로 저장하고 재시작해 복원한다."""
        self.seed()
        self.input.side_effect = [" 새 질문 ", " 가 ", "나", "다", "라", "4", " 새 힌트 "]
        self.game.add_quiz()
        expected = {"question": "새 질문", "choices": ["가", "나", "다", "라"],
                    "answer": 4, "hint": "새 힌트"}
        self.assertEqual(self.game.quizzes[-1].to_dict(), expected)
        self.assertEqual(load_state(self.state_path)["quizzes"][-1], expected)
        self.assertFalse(self.game.dirty)
        restarted = self.new_game()
        self.assertEqual(restarted.to_state(), self.game.to_state())
        self.assertIn("퀴즈를 추가했습니다", self.output.getvalue())
        self.assertIn("저장 완료", self.output.getvalue())

    def test_incomplete_add_never_mutates_or_saves(self):
        """질문·보기·마지막 힌트 입력 중단 어느 단계도 미완성 등록을 남기지 않는다."""
        self.seed()
        original = self.state_path.read_bytes()
        snapshot = self.game.to_state()
        cases = ([EOFError()], ["문제", "가", KeyboardInterrupt()],
                 ["문제", "가", "나", "다", "라", "1", EOFError()])
        for values in cases:
            with self.subTest(stage=len(values)):
                self.input.side_effect = values
                with self.assertRaises((EOFError, KeyboardInterrupt)):
                    self.game.add_quiz()
                self.assertEqual(self.game.to_state(), snapshot)
                self.assertEqual(self.state_path.read_bytes(), original)
                self.assertFalse(self.game.dirty)
        self.assertNotIn("추가했습니다", self.output.getvalue())

    def test_list_empty(self):
        """문제가 없을 때 명확한 빈 목록 안내를 제공한다."""
        self.game.quizzes = []
        self.game.list_quizzes()
        self.assertIn("등록된 퀴즈가 없습니다", self.output.getvalue())
        self.input.assert_not_called()

    def test_list_nonempty_does_not_reveal_answer_or_hint(self):
        """번호와 질문만 보여 주고 보기·정답·힌트는 공개하지 않는다."""
        self.game.quizzes = self.quizzes(2, "비공개 힌트")
        self.game.list_quizzes()
        text = self.output.getvalue()
        self.assertIn("1. 질문 0", text)
        self.assertIn("2. 질문 1", text)
        self.assertNotIn("보기 가", text)
        self.assertNotIn("정답", text)
        self.assertNotIn("비공개 힌트", text)

    def test_score_distinguishes_unplayed_from_completed_zero(self):
        """완료 전 상태와 완료했지만 0점인 상태를 구분한다."""
        self.game.show_score()
        self.assertIn("아직 완료한", self.output.getvalue())
        self.clear_output()
        self.seed()
        self.input.side_effect = ["1", "2"]
        self.game.play()
        self.clear_output()
        self.new_game().show_score()
        self.assertIn("최고 점수: 0점", self.output.getvalue())
        self.assertNotIn("아직 완료한", self.output.getvalue())

    def test_best_score_retained_after_lower_completed_score(self):
        """다음 판이 낮은 점수여도 기존 최고 점수와 완료 기록을 유지한다."""
        self.seed(2)
        self.input.side_effect = ["2", "1", "1", "1", "2"]
        self.game.play()
        self.game.play()
        self.assertEqual([r["score"] for r in self.game.history], [4, 0])
        self.assertEqual(self.game.best_score, 4)
        self.assertTrue(self.game.has_played)
        self.assertEqual(self.new_game().best_score, 4)

    def test_delete_cancellation_at_both_prompts_preserves_file(self):
        """번호 선택과 최종 확인에서 취소해도 메모리·파일은 그대로다."""
        self.seed()
        original = self.state_path.read_bytes()
        before = self.game.to_state()
        for answers in (["0"], ["1", "0"]):
            with self.subTest(answers=answers):
                self.input.side_effect = answers
                self.game.delete_quiz()
                self.assertEqual(self.game.to_state(), before)
                self.assertEqual(self.state_path.read_bytes(), original)
                self.assertFalse(self.game.dirty)
        self.assertEqual(self.output.getvalue().count("삭제를 취소했습니다"), 2)

    def test_delete_confirm_persists_empty_collection(self):
        """마지막 문제를 지운 빈 목록을 저장하고 기본 문제로 되돌리지 않는다."""
        self.seed()
        self.input.side_effect = ["1", "1"]
        self.game.delete_quiz()
        self.assertEqual(self.game.quizzes, [])
        self.assertEqual(load_state(self.state_path)["quizzes"], [])
        self.assertEqual(self.new_game().quizzes, [])
        self.assertIn("삭제했습니다", self.output.getvalue())

    def test_delete_empty_never_requests_input(self):
        """빈 목록 삭제는 번호를 묻지 않고 안내로 끝난다."""
        self.game.quizzes = []
        self.game.delete_quiz()
        self.input.assert_not_called()
        self.assertIn("삭제할 퀴즈가 없습니다", self.output.getvalue())

    def test_random_sample_count_unique_order_and_injected_determinism(self):
        """주입한 난수 시드의 표본만 풀며 원본 순서와 객체를 보존한다."""
        self.seed(8)
        original = self.game.quizzes.copy()
        expected = random.Random(19).sample(original, k=5)
        self.game.rng = random.Random(19)
        self.input.side_effect = ["5"] + ["1"] * 5
        with mock.patch.object(Quiz, "display", autospec=True) as display:
            self.game.play()
        observed = [call.args[0] for call in display.call_args_list]
        self.assertEqual(observed, expected)
        self.assertEqual(len(observed), 5)
        self.assertEqual(len({id(quiz) for quiz in observed}), 5)
        self.assertEqual(self.game.quizzes, original)
        restarted = self.new_game(rng=random.Random(19))
        self.input.side_effect = ["5"] + ["1"] * 5
        with mock.patch.object(Quiz, "display", autospec=True) as display:
            restarted.play()
        self.assertEqual([call.args[0].question for call in display.call_args_list],
                         [quiz.question for quiz in expected])

    def test_play_empty_does_not_start_history(self):
        """빈 목록에서는 풀이 입력이나 게임 기록을 만들지 않는다."""
        self.game.quizzes = []
        self.game.play()
        self.input.assert_not_called()
        self.assertEqual(self.game.history, [])
        self.assertIn("먼저 퀴즈를 추가", self.output.getvalue())

    def test_hint_missing_never_deducts_points(self):
        """힌트 없는 문제의 h 요청은 여러 번이어도 차감하지 않는다."""
        self.seed(hint="")
        self.input.side_effect = ["1", "h", "H", "1"]
        self.game.play()
        record = self.record()
        self.assertEqual((record["hints_used"], record["score"]), (0, 2))
        self.assertEqual(self.output.getvalue().count("힌트가 없습니다"), 2)

    def test_repeated_hint_deducts_once(self):
        """같은 문제의 대소문자 h 재요청은 최초 한 번만 차감한다."""
        self.seed()
        self.input.side_effect = ["1", " h ", "H", "h", "1"]
        self.game.play()
        record = self.record()
        self.assertEqual((record["hints_used"], record["score"]), (1, 1))
        self.assertEqual(self.output.getvalue().count("추가 차감 없음"), 2)

    def test_invalid_answers_retry_without_counting_attempts(self):
        """빈칸·문자·범위 오류는 응답 수나 힌트 수를 늘리지 않는다."""
        self.seed()
        self.input.side_effect = ["1", "", "  ", "abc", "0", "5", "1"]
        self.game.play()
        record = self.record()
        self.assertEqual((record["answered_count"], record["correct_count"], record["hints_used"]), (1, 1, 0))
        text = self.output.getvalue()
        self.assertEqual(text.count("입력이 비어 있습니다"), 2)
        self.assertIn("숫자 또는 힌트", text)
        self.assertEqual(text.count("1~4 범위"), 2)

    def test_score_lower_bound_with_wrong_hinted_answers(self):
        """오답과 힌트로 계산 결과가 음수여도 최종 저장 점수는 0이다."""
        self.seed(2)
        self.input.side_effect = ["2", "h", "2", "h", "2"]
        self.game.play()
        record = self.record()
        self.assertEqual((record["correct_count"], record["hints_used"], record["score"]), (0, 2, 0))
        self.assertTrue(record["completed"])
        self.assertTrue(self.game.has_played)

    def test_completed_history_has_timezone_counts_and_persisted_score(self):
        """완료 기록의 필수 항목·시간대·점수 산식과 재시작 보존을 확인한다."""
        self.seed(2)
        self.input.side_effect = ["2", "h", "1", "2"]
        self.game.play()
        record = self.record()
        self.assertEqual(set(record), {"played_at", "question_count", "answered_count",
                                      "correct_count", "hints_used", "score", "completed"})
        self.assertEqual((record["question_count"], record["answered_count"], record["correct_count"],
                          record["hints_used"], record["score"], record["completed"]), (2, 2, 1, 1, 1, True))
        self.assertIsNotNone(datetime.fromisoformat(record["played_at"]).utcoffset())
        self.assertEqual(self.new_game().history, [record])
        self.assertEqual(self.game.best_score, 1)

    def test_eof_before_first_answer_saves_interrupted_history(self):
        """첫 응답 전 EOF도 미완료 기록으로 저장하되 최고 점수는 건드리지 않는다."""
        self.seed()
        error = EOFError()
        self.input.side_effect = ["1", error]
        with self.assertRaises(EOFError) as caught:
            self.game.play()
        self.assertIs(caught.exception, error)
        record = self.record()
        self.assertEqual((record["answered_count"], record["correct_count"], record["score"]), (0, 0, 0))
        self.assertFalse(record["completed"])
        self.assertFalse(self.game.has_played)
        self.assertFalse(self.game.dirty)
        self.assertIn("중단", self.output.getvalue())

    def test_keyboard_after_correct_answer_does_not_update_best(self):
        """정답 점수가 생긴 판도 Ctrl+C 중단이면 최고 기록으로 인정하지 않는다."""
        self.seed(2)
        self.input.side_effect = ["2", "1", KeyboardInterrupt()]
        with self.assertRaises(KeyboardInterrupt):
            self.game.play()
        record = self.record()
        self.assertEqual((record["question_count"], record["answered_count"], record["correct_count"], record["score"]), (2, 1, 1, 2))
        self.assertFalse(record["completed"])
        restarted = self.new_game()
        self.assertEqual(restarted.best_score, 0)
        self.assertFalse(restarted.has_played)

    def test_interrupt_after_hint_preserves_hint_and_existing_best(self):
        """미응답 문제의 사용 힌트도 기록하며 EOF와 Ctrl+C 모두 기존 최고값을 지킨다."""
        self.seed()
        self.game.best_score = 9
        self.game.has_played = True
        self.game.dirty = True
        self.game.save_state()
        for exception in (EOFError, KeyboardInterrupt):
            with self.subTest(exception=exception.__name__):
                self.input.side_effect = ["1", "h", exception()]
                with self.assertRaises(exception):
                    self.game.play()
                record = self.record()
                self.assertEqual((record["answered_count"], record["hints_used"], record["score"]), (0, 1, 0))
                self.assertFalse(record["completed"])
                restarted = self.new_game()
                self.assertEqual((restarted.best_score, restarted.has_played), (9, True))

    def test_history_output_empty_then_completed_and_interrupted(self):
        """히스토리는 빈 상태와 완료·중단의 시각 및 풀이 수를 구분해 보여 준다."""
        self.game.show_history()
        self.assertIn("아직 게임 기록이 없습니다", self.output.getvalue())
        self.seed()
        self.input.side_effect = ["1", "1", "1", EOFError()]
        self.game.play()
        with self.assertRaises(EOFError):
            self.game.play()
        self.clear_output()
        self.game.show_history()
        text = self.output.getvalue()
        self.assertIn("완료", text)
        self.assertIn("중단", text)
        self.assertIn("1/1문제 풀이", text)
        self.assertIn("0/1문제 풀이", text)
        for record in self.game.history:
            self.assertIn(record["played_at"], text)

    def test_invalid_json_backup_and_restore(self):
        """깨진 JSON 원본을 백업한 뒤 정상 기본 상태를 저장한다."""
        self.check_corrupt_recovery(b'{"quizzes":')

    def test_invalid_utf8_backup_and_restore(self):
        """UTF-8 디코딩 실패도 원본 바이트를 손실 없이 백업한다."""
        self.check_corrupt_recovery(b'\xff\xfe\x00broken')

    def test_invalid_schema_backup_and_restore(self):
        """JSON 문법이 맞아도 점수 타입이 잘못되면 전체 상태를 복구한다."""
        self.check_corrupt_recovery(json.dumps({"quizzes": [], "best_score": True}).encode("utf-8"))

    def test_backup_failure_blocks_write_and_preserves_source(self):
        """백업 실패 시 원본 보호가 우선이며 이후 저장도 막는다."""
        original = b"{broken source"
        self.state_path.write_bytes(original)
        with mock.patch("quiz_game.shutil.copy2", side_effect=OSError("백업 거부")) as backup:
            game = self.new_game()
        backup.assert_called_once()
        self.assertFalse(game.write_allowed)
        game.dirty = True
        with mock.patch("quiz_game.write_state_file") as write:
            self.assertFalse(game.save_state())
        write.assert_not_called()
        self.assertTrue(game.dirty)
        self.assertEqual(self.state_path.read_bytes(), original)
        self.assertEqual(list(self.root.glob("*.bak")), [])
        self.assertIn("원본 백업 실패", self.output.getvalue())
        self.assertNotIn("저장 완료", self.output.getvalue())

    def test_read_permission_error_patches_imported_target_and_blocks_save(self):
        """실제 호출 대상 별칭에 읽기 권한 오류를 주입하여 잘못된 복구를 막는다."""
        self.seed()
        original = self.state_path.read_bytes()
        with mock.patch("quiz_game.read_state_file", side_effect=PermissionError("읽기 거부")) as read:
            game = self.new_game()
        read.assert_called_once_with(self.state_path)
        self.assertFalse(game.write_allowed)
        self.assertEqual(len(game.quizzes), 8)
        with mock.patch("quiz_game.write_state_file") as write:
            self.assertFalse(game.save_state())
        write.assert_not_called()
        self.assertEqual(self.state_path.read_bytes(), original)
        self.assertEqual(list(self.root.glob("*.bak")), [])
        self.assertIn("읽을 수 없습니다", self.output.getvalue())
        self.assertNotIn("손상", self.output.getvalue())

    def test_save_oserror_is_honest_retains_dirty_and_original(self):
        """교체 실패를 성공으로 알리지 않고 메모리 변경과 이전 파일을 보존한다."""
        self.seed()
        original = self.state_path.read_bytes()
        self.game.quizzes.append(self.quizzes()[0])
        self.game.dirty = True
        with mock.patch("state_io.os.replace", side_effect=OSError("디스크 쓰기 실패")):
            self.assertFalse(self.game.save_state())
        self.assertTrue(self.game.dirty)
        self.assertEqual(self.state_path.read_bytes(), original)
        self.assertEqual(set(self.root.iterdir()), {self.state_path})
        self.assertIn("저장 실패", self.output.getvalue())
        self.assertIn("메모리에만", self.output.getvalue())
        self.assertNotIn("저장 완료", self.output.getvalue())
        self.assertTrue(self.game.save_state())
        self.assertFalse(self.game.dirty)
        self.assertEqual(len(self.new_game().quizzes), 2)

    def test_save_keyboard_interrupt_reports_uncertainty_and_retains_dirty(self):
        """최종 저장 중 재차 Ctrl+C가 와도 성공으로 알리지 않고 재시도 가능하게 둔다."""
        self.seed()
        original = self.state_path.read_bytes()
        self.game.quizzes.append(self.quizzes()[0])
        self.game.dirty = True
        with mock.patch("quiz_game.write_state_file", side_effect=KeyboardInterrupt()) as write:
            self.assertFalse(self.game.save_state())
        write.assert_called_once_with(self.state_path, self.game.to_state())
        self.assertTrue(self.game.dirty)
        self.assertEqual(self.state_path.read_bytes(), original)
        self.assertIn("저장 도중 중단", self.output.getvalue())
        self.assertIn("보장할 수 없습니다", self.output.getvalue())
        self.assertNotIn("state.json 저장 완료", self.output.getvalue())

    def test_clean_save_does_not_rewrite(self):
        """변경 없는 상태의 종료 저장은 파일을 다시 쓰지 않는다."""
        self.seed()
        original = self.state_path.read_bytes()
        with mock.patch("quiz_game.write_state_file") as write:
            self.assertTrue(self.game.save_state())
        write.assert_not_called()
        self.assertEqual(self.state_path.read_bytes(), original)
        self.assertEqual(self.output.getvalue(), "")

    def test_explicit_state_path_survives_different_working_directory(self):
        """실행 위치를 바꾸어도 명시한 절대 경로만 읽고 쓴다."""
        elsewhere = self.root / "다른 작업 폴더"
        elsewhere.mkdir()
        previous = Path.cwd()
        try:
            os.chdir(elsewhere)
            game = self.new_game()
            self.assertTrue(game.save_state())
            self.assertEqual(self.new_game().to_state(), game.to_state())
        finally:
            os.chdir(previous)
        self.assertTrue(self.state_path.exists())
        self.assertFalse((elsewhere / "state.json").exists())

    def test_run_routes_every_menu_and_exits(self):
        """유효한 메뉴는 해당 메서드로 전달하고 종료 뒤 추가 입력을 하지 않는다."""
        methods = ("play", "add_quiz", "list_quizzes", "show_score", "delete_quiz", "show_history")
        with mock.patch.multiple(self.game, **{name: mock.DEFAULT for name in methods}) as actions:
            self.input.side_effect = ["1", "2", "3", "4", "5", "6", "0"]
            self.game.run()
        for action in actions.values():
            action.assert_called_once_with()
        self.assertEqual(self.input.call_count, 7)
        self.assertIn("게임을 종료합니다", self.output.getvalue())


if __name__ == "__main__":
    unittest.main()
