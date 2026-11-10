"""게임 진행을 조율한다. 개별 문제의 정답 판정은 Quiz에게 요청한다."""

from pathlib import Path

from defaults import create_default_quizzes
from input_utils import read_int


class QuizGame:
    """메뉴와 진행 상태를 관리하고 각 기능을 메서드로 나눈다."""

    def __init__(self, state_path: Path | None = None) -> None:
        # 실행한 위치가 아니라 코드 위치를 기준으로 데이터 파일을 찾는다.
        self.state_path = Path(state_path) if state_path else Path(__file__).with_name("state.json")
        self.quizzes = create_default_quizzes()
        self.best_score = 0
        self.has_played = False

    def show_menu(self) -> None:
        print("\n=== Python·개발 기초 퀴즈 ===")
        print("1. 퀴즈 풀기\n2. 퀴즈 추가\n3. 퀴즈 목록\n4. 점수 확인\n0. 종료")

    def run(self) -> None:
        """사용자가 종료를 고를 때까지 메뉴를 반복한다."""
        while True:
            self.show_menu()
            choice = read_int("메뉴 번호: ", 0, 4)
            if choice == 0:
                print("퀴즈 게임을 종료합니다.")
                return
            if choice == 1:
                self.play()
            else:
                print("이 기능은 다음 개발 단계에서 연결합니다.")

    def play(self) -> None:
        """모든 문제를 한 번씩 출제하고 Quiz에게 정답 여부를 묻는다."""
        if not self.quizzes:
            print("등록된 퀴즈가 없습니다. 먼저 퀴즈를 추가해 주세요.")
            return
        correct_count = 0
        for number, quiz in enumerate(self.quizzes, start=1):
            print(f"\n[문제 {number}/{len(self.quizzes)}]")
            quiz.display()
            selected = read_int("정답 번호 (1~4): ", 1, 4)
            if quiz.is_correct(selected):
                correct_count += 1
                print("정답입니다! (+2점)")
            else:
                print(f"오답입니다. 정답은 {quiz.answer}번입니다.")
        score = correct_count * 2
        self.best_score = max(self.best_score, score)
        self.has_played = True
        print(f"결과: {correct_count}/{len(self.quizzes)}개 정답, {score}점")
