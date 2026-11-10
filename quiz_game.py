"""게임 진행을 조율한다. 개별 문제의 정답 판정은 Quiz에게 요청한다."""

from datetime import datetime
from pathlib import Path
import random

from defaults import create_default_quizzes
from input_utils import read_int, read_text
from quiz import Quiz


class QuizGame:
    """메뉴와 진행 상태를 관리하고 각 기능을 메서드로 나눈다."""

    def __init__(self, state_path: Path | None = None, rng: random.Random | None = None) -> None:
        # 실행한 위치가 아니라 코드 위치를 기준으로 데이터 파일을 찾는다.
        self.state_path = Path(state_path) if state_path else Path(__file__).with_name("state.json")
        self.quizzes = create_default_quizzes()
        self.best_score = 0
        self.has_played = False
        self.history = []
        self.dirty = False
        # 기본 실행은 매번 다른 시드, 테스트는 Random(고정값)을 주입해 재현한다.
        self.rng = rng if rng is not None else random.Random()

    def show_menu(self) -> None:
        print("\n=== Python·개발 기초 퀴즈 ===")
        print("1. 퀴즈 풀기\n2. 퀴즈 추가\n3. 퀴즈 목록\n4. 점수 확인\n5. 퀴즈 삭제\n6. 점수 히스토리\n0. 종료")

    def run(self) -> None:
        """사용자가 종료를 고를 때까지 메뉴를 반복한다."""
        while True:
            self.show_menu()
            choice = read_int("메뉴 번호: ", 0, 6)
            if choice == 0:
                print("퀴즈 게임을 종료합니다.")
                return
            if choice == 1:
                self.play()
            elif choice == 2:
                self.add_quiz()
            elif choice == 3:
                self.list_quizzes()
            elif choice == 4:
                self.show_score()
            elif choice == 5:
                self.delete_quiz()
            elif choice == 6:
                self.show_history()

    def play(self) -> None:
        """문제를 중복 없이 뽑고, 중단된 판도 별도 상태로 기록한다."""
        if not self.quizzes:
            print("등록된 퀴즈가 없습니다. 먼저 퀴즈를 추가해 주세요.")
            return
        count = read_int(f"몇 문제를 풀까요? (1~{len(self.quizzes)}): ", 1, len(self.quizzes))
        # sample은 원본 순서를 바꾸지 않으면서 중복 없는 새 목록을 만든다.
        selected_quizzes = self.rng.sample(self.quizzes, k=count)
        session = {"question_count": count, "answered_count": 0,
                   "correct_count": 0, "hints_used": 0}
        print("정답 +2점, 힌트 사용 -1점. 최종 점수는 0점 미만이 되지 않습니다.")
        try:
            for number, quiz in enumerate(selected_quizzes, start=1):
                print(f"\n[문제 {number}/{count}]")
                quiz.display()
                selected = self.ask_answer(quiz, session)
                session['answered_count'] += 1
                # 게임은 퀴즈의 정답 판정 방법을 복제하지 않고 요청만 한다.
                if quiz.is_correct(selected):
                    session['correct_count'] += 1
                    print("정답입니다! (+2점)")
                else:
                    print(f"오답입니다. 정답은 {quiz.answer}번입니다.")
        except (EOFError, KeyboardInterrupt):
            self.finish_session(session, completed=False)
            raise  # 가장 바깥 실행 흐름에서 안내하고 안전 저장·종료한다.
        else:
            self.finish_session(session, completed=True)

    def ask_answer(self, quiz: Quiz, session: dict) -> int:
        """힌트는 한 문제에서 한 번만 차감하고, 정답 번호는 1~4만 받는다."""
        hint_shown = False
        while True:
            text = input("정답 번호 (1~4, 힌트 h): ").strip()
            if text.lower() == "h":
                if not quiz.hint:
                    print("이 문제에는 힌트가 없습니다. 점수는 차감되지 않습니다.")
                elif hint_shown:
                    print(f"이미 사용한 힌트입니다: {quiz.hint} (추가 차감 없음)")
                else:
                    hint_shown = True
                    session['hints_used'] += 1
                    print(f"힌트 (-1점): {quiz.hint}")
                continue
            if not text:
                print("입력이 비어 있습니다. 번호를 입력해 주세요.")
                continue
            try:
                number = int(text)
            except ValueError:
                print("1~4의 숫자 또는 힌트 h를 입력해 주세요.")
                continue
            if 1 <= number <= 4:
                return number
            print("1~4 범위의 번호를 입력해 주세요.")

    def finish_session(self, session: dict, completed: bool) -> None:
        """게임 기록을 확정하고, 완료한 판만 최고 점수와 비교한다."""
        score = max(0, session['correct_count'] * 2 - session['hints_used'])
        record = {**session, "score": score, "completed": completed,
                  "played_at": datetime.now().astimezone().isoformat(timespec="seconds")}
        self.history.append(record)
        self.dirty = True
        if completed:
            self.update_best_score(score)
        status = "완료" if completed else "중단 (최고 점수 반영 안 함)"
        print(f"결과 [{status}]: {session['correct_count']}/{session['answered_count']}개 정답, "
              f"힌트 {session['hints_used']}회, {score}점")

    def add_quiz(self) -> None:
        """모든 항목을 받은 뒤 등록해, 입력 중단으로 미완성 문제가 남지 않게 한다."""
        question = read_text("문제: ")
        choices = [read_text(f"선택지 {number}: ") for number in range(1, 5)]
        answer = read_int("정답 번호 (1~4): ", 1, 4)
        hint = input("힌트 (없으면 Enter): ").strip()
        # 모든 입력을 마친 뒤에만 목록에 반영한다.
        quiz = Quiz(question, choices, answer, hint)
        self.quizzes.append(quiz)
        self.dirty = True
        print(f"퀴즈를 추가했습니다. 현재 {len(self.quizzes)}개입니다.")

    def list_quizzes(self) -> None:
        """등록 번호와 문제 내용을 보여 준다. 정답은 목록에서 공개하지 않는다."""
        if not self.quizzes:
            print("등록된 퀴즈가 없습니다.")
            return
        print(f"\n=== 퀴즈 목록 ({len(self.quizzes)}개) ===")
        for number, quiz in enumerate(self.quizzes, start=1):
            print(f"{number}. {quiz.question}")

    def update_best_score(self, score: int) -> None:
        """기존 기록보다 낮은 점수로 최고 점수를 덮어쓰지 않는다."""
        self.best_score = max(self.best_score, score)
        self.has_played = True

    def show_score(self) -> None:
        """0점으로 끝낸 경우와 아직 한 판도 끝내지 않은 경우를 구분한다."""
        if not self.has_played:
            print("아직 완료한 퀴즈 풀이가 없습니다.")
            return
        print(f"최고 점수: {self.best_score}점 (완료한 판의 총점, 정답 +2 / 힌트 -1)")

    def delete_quiz(self) -> None:
        """번호와 확인을 받은 뒤 삭제한다. 취소하면 상태를 바꾸지 않는다."""
        if not self.quizzes:
            print("삭제할 퀴즈가 없습니다.")
            return
        self.list_quizzes()
        number = read_int("삭제할 번호 (취소 0): ", 0, len(self.quizzes))
        if number == 0:
            print("삭제를 취소했습니다.")
            return
        quiz = self.quizzes[number - 1]
        confirm = read_int(f"{quiz.question} / 삭제 1 / 취소 0: ", 0, 1)
        if confirm == 0:
            print("삭제를 취소했습니다.")
            return
        self.quizzes.pop(number - 1)
        self.dirty = True
        print("퀴즈를 삭제했습니다.")

    def show_history(self) -> None:
        """날짜·시각·풀이 수·점수·중단 여부를 저장된 순서로 보여 준다."""
        if not self.history:
            print("아직 게임 기록이 없습니다.")
            return
        print("\n=== 점수 히스토리 ===")
        for number, record in enumerate(self.history, start=1):
            status = "완료" if record['completed'] else "중단"
            print(f"{number}. {record['played_at']} | {status} | "
                  f"{record['answered_count']}/{record['question_count']}문제 풀이 | "
                  f"정답 {record['correct_count']}개 | 힌트 {record['hints_used']}회 | "
                  f"{record['score']}점")
