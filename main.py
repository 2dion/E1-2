"""Python 개발 기초 퀴즈의 실행 시작점. python3 main.py로 실행한다."""

from input_utils import read_int


def main() -> None:
    """먼저 메뉴 흐름을 만들고, 완성한 기능을 차례로 연결한다."""
    try:
        while True:
            print("\n=== Python·개발 기초 퀴즈 ===")
            print("1. 퀴즈 풀기\n2. 퀴즈 추가\n3. 퀴즈 목록\n4. 점수 확인\n0. 종료")
            choice = read_int("메뉴 번호: ", 0, 4)
            if choice == 0:
                print("퀴즈 게임을 종료합니다.")
                break
            print("이 기능은 다음 개발 단계에서 연결합니다.")
    except (EOFError, KeyboardInterrupt):
        # 입력 종료를 프로그램 오류의 긴 추적 메시지로 보여 주지 않는다.
        print("\n입력이 종료되어 프로그램을 안전하게 마칩니다.")


if __name__ == "__main__":
    # 다른 모듈에서 import할 때에는 게임을 자동 시작하지 않는다.
    main()
