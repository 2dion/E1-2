"""종료 조율과 독립 CLI 실행을 실제 프로젝트 데이터 없이 검사한다."""

import ast
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import main as application
from state_io import load_state


ROOT = Path(__file__).resolve().parents[1]


class MainTests(unittest.TestCase):
    """게임 객체를 모의하여 main의 종료·저장 책임만 확인한다."""

    def setUp(self):
        self.output = io.StringIO()
        self.addCleanup(self.output.close)
        capture = redirect_stdout(self.output)
        capture.__enter__()
        self.addCleanup(capture.__exit__, None, None, None)
        patcher = mock.patch("main.QuizGame", autospec=True)
        self.factory = patcher.start()
        self.addCleanup(patcher.stop)
        self.game = self.factory.return_value

    def test_normal_exit_saves_once(self):
        """정상 메뉴 종료도 finally를 통해 한 번 저장한다."""
        application.main()
        self.factory.assert_called_once_with()
        self.game.run.assert_called_once_with()
        self.game.save_state.assert_called_once_with()
        self.assertEqual(self.output.getvalue(), "")

    def test_eof_from_game_saves_and_reports_safe_exit(self):
        """EOF는 추적 로그 없이 종료 안내와 저장으로 처리한다."""
        self.game.run.side_effect = EOFError()
        application.main()
        self.game.save_state.assert_called_once_with()
        self.assertIn("안전하게 마칩니다", self.output.getvalue())

    def test_keyboard_interrupt_from_game_saves_and_reports_safe_exit(self):
        """Ctrl+C도 실행 실패로 전파하지 않고 마지막 저장을 호출한다."""
        self.game.run.side_effect = KeyboardInterrupt()
        application.main()
        self.game.save_state.assert_called_once_with()
        self.assertIn("안전하게 마칩니다", self.output.getvalue())

    def test_constructor_interrupt_has_no_uninitialized_save(self):
        """생성 도중 중단되면 아직 없는 게임에 저장을 요청하지 않는다."""
        self.factory.side_effect = EOFError()
        application.main()
        self.game.run.assert_not_called()
        self.game.save_state.assert_not_called()
        self.assertIn("안전하게 마칩니다", self.output.getvalue())


class MainCliTests(unittest.TestCase):
    """모든 루트 파이썬 파일을 임시 복사하여 실제 CLI를 검증한다."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.app = self.root / "application"
        self.app.mkdir()
        self.work = self.root / "unrelated-cwd"
        self.work.mkdir()
        # 새 의존 모듈이 생겨도 누락되지 않도록 루트의 .py를 모두 복사한다.
        sources = sorted(ROOT.glob("*.py"))
        self.assertTrue(sources)
        for source in sources:
            shutil.copy2(source, self.app / source.name)
        self.assertEqual({p.name for p in self.app.glob("*.py")}, {p.name for p in sources})

    def run_cli(self, text, cwd=None):
        """닫힌 표준입력을 명시하여 EOF가 즉시 전달되도록 실행한다."""
        environment = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1",
                           PYTHONDONTWRITEBYTECODE="1")
        result = subprocess.run(
            [sys.executable, str(self.app / "main.py")], input=text,
            capture_output=True, text=True, encoding="utf-8",
            cwd=cwd or self.app, env=environment, timeout=10,
        )
        self.assertEqual(result.returncode, 0,
                         f"stdout={result.stdout!r}\nstderr={result.stderr!r}")
        self.assertEqual(result.stderr, "")
        self.assertNotIn("Traceback", result.stdout)
        return result.stdout

    def test_cli_empty_stdin_eof_saves_defaults(self):
        """input=''의 진짜 EOF에서 즉시 안전 종료하고 초기 상태를 저장한다."""
        output = self.run_cli("")
        self.assertIn("안전하게 마칩니다", output)
        self.assertIn("저장 완료", output)
        state = load_state(self.app / "state.json")
        self.assertEqual(len(state["quizzes"]), 8)
        self.assertEqual(state["history"], [])
        self.assertFalse(state["has_played"])

    def test_cli_invalid_menu_then_exit(self):
        """빈칸·문자·범위 오류 뒤 0번을 받아 정상 종료한다."""
        output = self.run_cli("\n \nabc\n-1\n7\n0\n")
        self.assertEqual(output.count("입력이 비어 있습니다"), 2)
        self.assertIn("숫자로 입력", output)
        self.assertEqual(output.count("0~6 범위"), 2)
        self.assertIn("게임을 종료합니다", output)
        self.assertNotIn("안전하게 마칩니다", output)
        self.assertTrue((self.app / "state.json").exists())

    def test_cli_state_path_is_module_relative_not_cwd(self):
        """다른 CWD의 동명 파일은 건드리지 않고 코드 옆 파일만 저장한다."""
        decoy = self.work / "state.json"
        decoy.write_bytes(b"unrelated project state must stay untouched")
        original = decoy.read_bytes()
        self.run_cli("0\n", cwd=self.work)
        self.assertEqual(decoy.read_bytes(), original)
        self.assertEqual(len(load_state(self.app / "state.json")["quizzes"]), 8)
        self.assertEqual(set(self.work.iterdir()), {decoy})

    def test_cli_eof_during_play_persists_interrupted_history(self):
        """메뉴·문제 수만 입력한 뒤 EOF가 오면 미완료 판을 실제 파일에 남긴다."""
        output = self.run_cli("1\n1\n")
        state = load_state(self.app / "state.json")
        self.assertEqual(len(state["history"]), 1)
        record = state["history"][0]
        self.assertEqual((record["question_count"], record["answered_count"], record["score"]), (1, 0, 0))
        self.assertFalse(record["completed"])
        self.assertFalse(state["has_played"])
        self.assertEqual(state["best_score"], 0)
        self.assertIn("중단", output)
        self.assertIn("안전하게 마칩니다", output)


class PythonCompatibilityTests(unittest.TestCase):
    """실행기 버전과 별도로 전체 소스의 Python 3.10 문법을 확인한다."""

    def test_all_application_and_test_sources_parse_as_python_310(self):
        """루트 코드와 기존·신규 테스트를 모두 3.10 문법 규칙으로 파싱한다."""
        sources = sorted(ROOT.glob("*.py")) + sorted((ROOT / "tests").rglob("*.py"))
        self.assertTrue(sources)
        for source in sources:
            with self.subTest(source=source.relative_to(ROOT)):
                ast.parse(source.read_text(encoding="utf-8"), filename=str(source),
                          feature_version=(3, 10))


if __name__ == "__main__":
    unittest.main()
