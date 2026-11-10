"""문제의 내용과 정답 판정을 책임지는 퀴즈 클래스를 정의한다."""


class Quiz:
    """문제 한 개를 보관하고, 보기 출력과 정답 판정을 담당한다."""

    def __init__(
        self, question: str, choices: list[str], answer: int, hint: str = ""
    ) -> None:
        """입력값을 검사하고 문자열 양끝의 공백을 제거해 저장한다."""
        if not isinstance(question, str) or not question.strip():
            raise ValueError("질문은 공백이 아닌 문자열이어야 합니다.")
        if type(choices) is not list or len(choices) != 4:
            raise ValueError("보기는 정확히 네 개를 담은 리스트여야 합니다.")
        if any(not isinstance(choice, str) or not choice.strip() for choice in choices):
            raise ValueError("각 보기는 공백이 아닌 문자열이어야 합니다.")
        # bool은 int의 하위 타입이므로 정확한 타입을 검사한다.
        if type(answer) is not int or not 1 <= answer <= 4:
            raise ValueError("정답 번호는 1부터 4 사이의 정수여야 합니다.")
        if not isinstance(hint, str):
            raise ValueError("힌트는 문자열이어야 합니다.")

        self.question = question.strip()
        # 새 리스트에 저장해 호출자가 원본 보기를 바꾸어도 영향을 받지 않는다.
        self.choices = [choice.strip() for choice in choices]
        self.answer = answer
        self.hint = hint.strip()

    def is_correct(self, selected: int) -> bool:
        """유효한 선택이 정답인지 반환하며, 잘못된 선택은 False로 처리한다."""
        if type(selected) is not int or not 1 <= selected <= 4:
            return False
        return selected == self.answer

    def display(self) -> None:
        """질문과 1번부터 시작하는 보기를 차례로 출력한다."""
        print(self.question)
        for number, choice in enumerate(self.choices, start=1):
            print(f"{number}. {choice}")

    def to_dict(self) -> dict:
        """저장에 쓸 딕셔너리를 만들며 보기 리스트도 복사한다."""
        return {
            "question": self.question,
            "choices": self.choices.copy(),
            "answer": self.answer,
            "hint": self.hint,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Quiz":
        """필수 항목을 확인한 뒤 생성자의 검증을 거쳐 퀴즈를 복원한다."""
        if type(data) is not dict:
            raise ValueError("퀴즈 데이터는 딕셔너리여야 합니다.")
        if not all(key in data for key in ("question", "choices", "answer")):
            raise ValueError("질문, 보기, 정답 항목이 모두 필요합니다.")
        # 검증 규칙은 생성자 한곳에 두어 복원할 때도 같은 규칙을 적용한다.
        return cls(data["question"], data["choices"], data["answer"], data.get("hint", ""))
