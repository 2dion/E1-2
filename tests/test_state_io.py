"""상태 검증, JSON 입출력, 원자적 저장의 실패 경로를 검증한다."""

import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from quiz import Quiz
from state_io import load_state, save_state, validate_state


def quiz_data():
    """힌트가 없는 구버전 한국어 문제 데이터를 만든다."""
    return {"question": " 수도는? ", "choices": [" 서울 ", "부산", "대구", "인천"], "answer": 1}


def state_data():
    """최소 필수 항목만 담은 독립적인 상태를 만든다."""
    return {"quizzes": [quiz_data()], "best_score": 0}


def history_data(**changes):
    """정상 완료 기록을 만들고 요청한 항목을 바꾼다."""
    record = {
        "played_at": "2026-11-10T18:00:00+09:00", "question_count": 3,
        "answered_count": 3, "correct_count": 2, "hints_used": 1,
        "score": 3, "completed": True,
    }
    record.update(changes)
    return record


class StateValidationTests(unittest.TestCase):
    """호출자의 데이터를 바꾸지 않는 엄격한 스키마 검증을 확인한다."""

    def test_minimal_legacy_defaults_and_normalization(self):
        result = validate_state(state_data())
        self.assertEqual(result["schema_version"], 1)
        self.assertFalse(result["has_played"])
        self.assertEqual(result["history"], [])
        self.assertEqual(result["quizzes"][0]["question"], "수도는?")
        self.assertEqual(result["quizzes"][0]["choices"][0], "서울")
        self.assertEqual(result["quizzes"][0]["hint"], "")

    def test_outer_dictionary_and_required_fields(self):
        class DictSubclass(dict):
            pass
        for data in (None, [], "{}", DictSubclass(state_data()), {}, {"quizzes": []}, {"best_score": 0}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                validate_state(data)

    def test_schema_integer_types_and_ranges(self):
        for field, values in (
            ("best_score", [True, False, -1, 1.0, "1", None]),
            ("schema_version", [True, False, 0, 2, -1, 1.0, "1", None]),
        ):
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    validate_state(dict(state_data(), **{field: value}))

    def test_optional_boolean_and_list_types(self):
        for field, values in (
            ("has_played", [0, 1, "true", None, []]),
            ("history", [None, {}, (), "history"]),
            ("quizzes", [None, {}, (), "quizzes"]),
        ):
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    validate_state(dict(state_data(), **{field: value}))

    def test_empty_quizzes_and_legacy_highest_score(self):
        result = validate_state({"quizzes": [], "best_score": 1000000})
        self.assertEqual(result["quizzes"], [])
        self.assertEqual(result["best_score"], 1000000)
        self.assertTrue(result["has_played"])

    def test_quiz_validation_and_mutated_class_fields(self):
        broken = Quiz.from_dict(quiz_data())
        broken.answer = True
        for quiz in (None, {}, broken.to_dict(), dict(quiz_data(), choices=["a"]),
                     dict(quiz_data(), question=" "), dict(quiz_data(), hint=1)):
            with self.subTest(quiz=quiz), self.assertRaises(ValueError):
                validate_state({"quizzes": [quiz], "best_score": 0})
        broken.answer = 1
        broken.choices[0] = ""
        with self.assertRaises(ValueError):
            validate_state({"quizzes": [broken.to_dict()], "best_score": 0})

    def test_new_nested_values_unknown_keys_and_original_unchanged(self):
        data = dict(state_data(), extra="삭제", history=[history_data(extra="삭제")])
        data["quizzes"][0]["extra"] = "삭제"
        original = copy.deepcopy(data)
        result = validate_state(data)
        self.assertEqual(data, original)
        self.assertNotIn("extra", result)
        self.assertNotIn("extra", result["quizzes"][0])
        self.assertNotIn("extra", result["history"][0])
        result["quizzes"][0]["choices"][0] = "변경"
        result["history"][0]["score"] = 0
        self.assertEqual(data, original)
        self.assertIsNot(result, data)

    def test_completed_records_imply_played_even_with_zero_score(self):
        record = history_data(correct_count=0, hints_used=3, score=0)
        for explicit in ({}, {"has_played": False}, {"has_played": True}):
            with self.subTest(explicit=explicit):
                result = validate_state(dict(state_data(), history=[record], **explicit))
                self.assertTrue(result["has_played"])

    def test_interrupted_and_unanswered_history(self):
        records = [
            history_data(answered_count=0, correct_count=0, hints_used=0, score=0, completed=False),
            history_data(answered_count=1, correct_count=1, hints_used=0, score=2, completed=False),
            history_data(correct_count=0, hints_used=3, score=0, completed=False),
        ]
        result = validate_state(dict(state_data(), history=records))
        self.assertFalse(result["has_played"])
        self.assertEqual(result["history"], records)

    def test_history_required_fields_and_record_types(self):
        for record in (None, [], "record", 1):
            with self.subTest(record=record), self.assertRaises(ValueError):
                validate_state(dict(state_data(), history=[record]))
        for field in history_data():
            record = history_data()
            del record[field]
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_state(dict(state_data(), history=[record]))

    def test_history_integer_types_and_bounds(self):
        invalid = {
            "question_count": [0, -1], "answered_count": [-1, 4],
            "correct_count": [-1, 4], "hints_used": [-1, 4], "score": [-1, 2, 4],
        }
        for field, values in invalid.items():
            for value in values + [True, False, 1.0, "1", None]:
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    validate_state(dict(state_data(), history=[history_data(**{field: value})]))
        with self.assertRaises(ValueError):
            validate_state(dict(state_data(), history=[history_data(
                answered_count=1, correct_count=2, completed=False)]))

    def test_completion_boolean_and_answer_count(self):
        for value in (0, 1, "true", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_state(dict(state_data(), history=[history_data(completed=value)]))
        with self.assertRaises(ValueError):
            validate_state(dict(state_data(), history=[history_data(answered_count=2)]))

    def test_history_datetime_formats_and_timezones(self):
        for value in (None, 123, "", "not-a-date", "2026-11-10", "2026-11-10T18:00:00", "2026-13-10T18:00:00+09:00"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_state(dict(state_data(), history=[history_data(played_at=value)]))
        for value in ("2026-11-10T09:00:00Z", "2026-11-10T09:00:00+00:00", "2026-11-10T08:00:00.123-01:00"):
            with self.subTest(value=value):
                result = validate_state(dict(state_data(), history=[history_data(played_at=value)]))
                self.assertEqual(result["history"][0]["played_at"], value)

    def test_all_history_records_preserved_and_late_invalid_rejected(self):
        records = [history_data() for _ in range(1500)]
        self.assertEqual(len(validate_state(dict(state_data(), history=records))["history"]), 1500)
        records[-1]["score"] = True
        with self.assertRaises(ValueError):
            validate_state(dict(state_data(), history=records))


class StateFileTests(unittest.TestCase):
    """프로젝트 파일 대신 임시 디렉터리만 사용해 입출력을 검사한다."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.path = self.root / "상태.json"

    def test_full_roundtrip_utf8_pretty_json_and_newline(self):
        data = dict(state_data(), history=[history_data()], best_score=99, has_played=True)
        save_state(self.path, data)
        self.assertEqual(load_state(self.path), validate_state(data))
        raw = self.path.read_bytes()
        self.assertIn("수도는?".encode("utf-8"), raw)
        self.assertNotIn(b"\\u", raw)
        self.assertTrue(raw.endswith(b"\n"))
        self.assertIn(b'\n  "schema_version": 1', raw)
        self.assertEqual(set(self.root.iterdir()), {self.path})

    def test_load_missing_and_unreadable_errors(self):
        with self.assertRaises(FileNotFoundError):
            load_state(self.path)
        error = PermissionError("읽기 거부")
        with mock.patch.object(Path, "open", side_effect=error):
            with self.assertRaises(PermissionError) as caught:
                load_state(self.path)
        self.assertIs(caught.exception, error)
        with mock.patch.object(Path, "open", side_effect=OSError("읽기 오류")):
            with self.assertRaises(OSError):
                load_state(self.path)

    def test_load_malformed_empty_json_and_invalid_utf8(self):
        for text in ("", "{", "not-json"):
            with self.subTest(text=text):
                self.path.write_text(text, encoding="utf-8")
                with self.assertRaises(json.JSONDecodeError):
                    load_state(self.path)
        self.path.write_bytes(b"\xff\xfe")
        with self.assertRaises(UnicodeDecodeError):
            load_state(self.path)

    def test_load_valid_json_with_bad_schema(self):
        for data in ([], {}, dict(state_data(), best_score=True)):
            with self.subTest(data=data):
                self.path.write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_state(self.path)

    def test_invalid_save_validates_before_file_operations(self):
        original = b"\x00old state\r\n"
        self.path.write_bytes(original)
        invalid = dict(state_data(), history=[history_data(score=999)])
        with mock.patch("state_io.tempfile.NamedTemporaryFile") as create:
            with self.assertRaises(ValueError):
                save_state(self.path, invalid)
            create.assert_not_called()
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(set(self.root.iterdir()), {self.path})

    def test_replace_failure_preserves_previous_bytes_and_cleans_temp(self):
        original = b"old file\x00\r\n"
        self.path.write_bytes(original)
        observed = []

        def fail_replace(source, destination):
            """교체 직전 임시 파일 위치와 완성된 JSON 내용을 확인한다."""
            observed.append(Path(source))
            self.assertEqual(Path(source).parent, self.root)
            self.assertEqual(destination, self.path)
            self.assertEqual(load_state(Path(source)), validate_state(state_data()))
            raise OSError("교체 실패")

        with mock.patch("state_io.os.replace", side_effect=fail_replace):
            with self.assertRaisesRegex(OSError, "교체 실패"):
                save_state(self.path, state_data())
        self.assertEqual(len(observed), 1)
        self.assertFalse(observed[0].exists())
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(set(self.root.iterdir()), {self.path})

    def test_fsync_and_serialization_failures_preserve_and_cleanup(self):
        self.path.write_bytes(b"original")
        for target in ("state_io.os.fsync", "state_io.json.dump"):
            with self.subTest(target=target), mock.patch(target, side_effect=OSError("쓰기 실패")):
                with self.assertRaises(OSError):
                    save_state(self.path, state_data())
            self.assertEqual(self.path.read_bytes(), b"original")
            self.assertEqual(set(self.root.iterdir()), {self.path})

    def test_missing_or_non_directory_parent_not_created(self):
        missing = self.root / "없는폴더"
        with self.assertRaises(FileNotFoundError):
            save_state(missing / "state.json", state_data())
        self.assertFalse(missing.exists())
        self.path.write_bytes(b"file")
        with self.assertRaises(OSError):
            save_state(self.path / "state.json", state_data())
        self.assertEqual(self.path.read_bytes(), b"file")

    def test_flush_and_fsync_happen_before_replace(self):
        events = []
        real_fsync = os.fsync
        real_replace = os.replace

        def check_fsync(fd):
            """fsync 전에 버퍼가 비워져 파일 내용이 보이는지 확인한다."""
            temporary = list(self.root.iterdir())
            self.assertEqual(len(temporary), 1)
            self.assertTrue(temporary[0].read_bytes().endswith(b"\n"))
            events.append("fsync")
            real_fsync(fd)

        def check_replace(source, destination):
            events.append("replace")
            real_replace(source, destination)

        with mock.patch("state_io.os.fsync", side_effect=check_fsync), mock.patch("state_io.os.replace", side_effect=check_replace):
            save_state(self.path, state_data())
        self.assertEqual(events, ["fsync", "replace"])
        self.assertEqual(load_state(self.path), validate_state(state_data()))


if __name__ == "__main__":
    unittest.main()
