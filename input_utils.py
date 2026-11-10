"""메뉴와 퀴즈 등록에서 반복되는 입력 검사를 한곳에 모은다."""


def read_int(prompt: str, minimum: int, maximum: int) -> int:
    """정수가 들어올 때까지 반복한다. EOF/Ctrl+C는 바깥 종료 처리로 전달한다."""
    while True:
        # input은 문자열을 돌려주므로, 공백 제거와 숫자 변환을 순서대로 한다.
        text = input(prompt).strip()
        if not text:
            print("입력이 비어 있습니다. 번호를 입력해 주세요.")
            continue
        try:
            number = int(text)
        except ValueError:
            print("숫자로 입력해 주세요.")
            continue
        if minimum <= number <= maximum:
            return number
        print(f"{minimum}~{maximum} 범위의 번호를 입력해 주세요.")


def read_text(prompt: str) -> str:
    """문제·선택지는 공백뿐인 값으로 등록하지 못하게 한다."""
    while True:
        text = input(prompt).strip()
        if text:
            return text
        print("내용이 비어 있습니다. 다시 입력해 주세요.")
