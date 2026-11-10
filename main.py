"""실행 시작점. 게임·입력·저장 책임을 각 모듈에 맡기고 종료를 조율한다."""

from quiz_game import QuizGame


def main() -> None:
    """입력 끝과 Ctrl+C에서 안내하고, 가능한 범위에서 상태를 저장한다."""
    game = None
    try:
        game = QuizGame()
        game.run()
    except (EOFError, KeyboardInterrupt):
        print("\n입력이 종료되어 프로그램을 안전하게 마칩니다.")
    finally:
        # 저장 실패는 save_state가 안내한다. 실패를 성공으로 표시하지 않는다.
        if game is not None:
            game.save_state()


if __name__ == "__main__":
    # import는 정의만 가져오고, 직접 실행한 경우에만 게임을 시작한다.
    main()
