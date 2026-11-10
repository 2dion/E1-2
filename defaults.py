"""처음 실행할 때 제공할 Python·개발 기초 퀴즈. 실행 데이터와 분리해 복구에 사용한다."""

from quiz import Quiz


# 객체지향·JSON·인코딩·입력 처리 등 이번 사전 질문에서 공부한 내용을 복습한다.
# 정답 번호는 화면과 똑같이 1~4로 관리하고, 리스트 인덱스와 혼동하지 않는다.
DEFAULT_QUIZZES = [
    {"question": "Python에서 정수를 나타내는 자료형은?",
     "choices": ["str", "int", "list", "dict"], "answer": 2,
     "hint": "integer의 앞부분을 생각해 보세요."},
    {"question": "같은 종류의 값을 순서대로 담고 수정할 수 있는 자료형은?",
     "choices": ["bool", "int", "list", "None"], "answer": 3,
     "hint": "대괄호 [ ]로 표현하는 자료형입니다."},
    {"question": "조건에 따라 실행할 코드를 나누는 구문은?",
     "choices": ["if / elif / else", "import", "return만 사용", "class만 사용"], "answer": 1,
     "hint": "만약이라는 뜻의 영어 단어로 시작합니다."},
    {"question": "인스턴스 메서드에서 self가 가리키는 것은?",
     "choices": ["모든 객체의 목록", "클래스 이름 문자열", "사용자의 입력값", "지금 그 일을 하는 객체 자신"], "answer": 4,
     "hint": "self.answer는 내 정답이라고 읽을 수 있습니다."},
    {"question": "JSON의 설명으로 가장 알맞은 것은?",
     "choices": ["Python 전용 실행 파일", "텍스트 기반 데이터 교환 형식", "이미지 압축 형식", "암호화 알고리즘"], "answer": 2,
     "hint": "사람도 읽고 여러 언어의 프로그램도 해석할 수 있습니다."},
    {"question": "UTF-8은 무엇을 정하는 규칙인가?",
     "choices": ["퀴즈의 점수", "Git 브랜치 이름", "유니코드 문자를 바이트로 표현하는 방식", "파일의 접근 권한"], "answer": 3,
     "hint": "문자를 파일에 저장하고 다시 읽는 과정과 관련됩니다."},
    {"question": "input()이 더 읽을 입력 없이 입력의 끝을 만나면 발생하는 예외는?",
     "choices": ["EOFError", "KeyError", "IndexError", "ImportError"], "answer": 1,
     "hint": "End Of File의 약자가 들어 있습니다."},
    {"question": "같은 시드와 호출 순서에서 결과를 재현할 수 있는 기본 random의 성질은?",
     "choices": ["모든 결과가 항상 다르다", "보안 토큰에 반드시 적합하다", "오직 현재 시간만 사용한다", "결정적인 의사 난수를 만든다"], "answer": 4,
     "hint": "알고리즘이 내부 상태를 갱신해 수열을 만듭니다."},
]


def create_default_quizzes() -> list[Quiz]:
    """게임마다 새 객체를 만들어 다른 게임의 수정이 기본 데이터에 번지지 않게 한다."""
    return [Quiz.from_dict(item) for item in DEFAULT_QUIZZES]
