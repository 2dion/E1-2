"""실행 시작점. 직접 실행할 때만 게임을 시작한다."""

from quiz_game import QuizGame


def main() -> None:
    """입력 끝과 Ctrl+C는 사용자 종료 요청으로 처리한다."""
    game = QuizGame()
    try:
        game.run()
    except (EOFError, KeyboardInterrupt):
        print("\n입력이 종료되어 프로그램을 안전하게 마칩니다.")


if __name__ == "__main__":
    main()
