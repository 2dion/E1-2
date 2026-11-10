# E1-2 요구사항과 검증 대응

미션 상세의 최종 결과물·기능 요구사항·보너스·제약을 2026-11-10에 다시 확인했다. 공식 미션은 [Codyssey 학습 맵](https://usr.codyssey.kr/daejeon/learning/learningMap?projectNo=154005)에서 확인할 수 있다.

## 1. 최종 결과물

- Python 콘솔 프로그램: `python3 main.py`.
- 메뉴 선택에 따라 퀴즈 풀기·추가·목록·점수·종료 동작.
- 주제: Python·개발 기초, 기본 문제 8개, 각 선택지 4개.
- `Quiz`와 `QuizGame`으로 책임 분리, 입력과 저장은 별도 모듈로 분리.
- 루트 `state.json`에 UTF-8로 저장, 별도 실행 프로세스에서 유지 확인.
- GitHub 주소: https://github.com/2dion/E1-2 . **원격 반영과 clone/pull 완료 여부는 README의 현재 상태를 확인한다. 로컬 구현 완료가 곧 원격 업로드 완료는 아니다.**

## 2. 기능 요구사항

| 요구사항 | 구현 위치 | 검증 |
| --- | --- | --- |
| 메뉴·선택·종료 | `QuizGame.show_menu`, `run`, `main.main` | 메뉴 / EOF / Ctrl+C 실제 로그, `test_main.py` |
| 공백·빈 입력·변환 실패·범위 초과 | `input_utils`, `ask_answer` | `test_input_utils.py`, `test_quiz_game.py`, invalid-input 로그 |
| Quiz 속성 question/choices/answer | `Quiz.__init__` | `test_quiz.py` |
| 보기 출력과 정답 판정 | `Quiz.display`, `is_correct` | 모델 테스트, play 로그 |
| 기본 퀴즈 5개 이상과 인스턴스 생성 | `defaults.create_default_quizzes` | 기본 8개, 독립 인스턴스 검증 |
| 추가 브랜치에서 플레이 후 병합 | `feature/quiz-play` | Git graph, 실제 merge 커밋 |
| 플레이와 빈 퀴즈 처리 | `QuizGame.play` | 게임 단위 테스트, play 로그 |
| 퀴즈 추가와 입력 검사·저장 | `add_quiz` | 추가·재시작 테스트, add-quiz / restart 로그 |
| 목록·빈 목록 | `list_quizzes` | 게임 테스트, list 로그 |
| 최고 점수 갱신·저장·미플레이 | `update_best_score`, `show_score`, `finish_session` | 미플레이와 0점 구분, 낮은 기록 유지, score 로그 |
| QuizGame 속성과 기능별 메서드 | `quiz_game.py` | 책임별 메서드 및 주석, README 목표 설명 |
| 파일 저장·불러오기 | `state_io`, `QuizGame.load_state/save_state` | UTF-8·원자적 교체·재시작 테스트 |
| 없는 파일은 기본 퀴즈 | `load_state` | 임시 폴더 테스트 |
| 손상 파일은 안내·기본값 복구 | `load_state`와 손상 원본 백업 | JSON/인코딩/스키마 오류 테스트, corrupt-recovery 로그 |
| 읽기/쓰기 오류 | `load_state/save_state`, `state_io.save_state` | PermissionError/OSError 주입, 원본 보존 테스트 |
| EOF/Ctrl+C 시 안내·가능한 저장·종료 | `main.main`, `play`, `save_state` | 실제 SIGINT / EOF 로그, 중단 기록과 저장 중단 테스트 |
| README 필수 항목 | 루트 `README.md` | 개요·선정 이유·실행·기능·구조·데이터 설명 |
| clone 후 변경·commit·push, 원래 폴더 pull | 원격 인증 후 수행 | **원격 반영·실습 완료 전에는 통과로 표시하지 않음** |

## 3. 보너스 5개

| 보너스 | 구현 | 확인 기준 |
| --- | --- | --- |
| 랜덤 출제 | `rng.sample` | 중복 없이 선택, 원본 목록 순서 보존, 고정 시드 테스트 |
| 문제 수 선택 | `play`의 `read_int` | 1~현재 퀴즈 수, 빈 입력·잘못된 수 재입력 |
| 힌트 | `Quiz.hint`, `ask_answer` | h로 표시, 문제당 한 번 차감, 힌트 없음은 차감 없음 |
| 삭제 | `delete_quiz` | 번호 선택·확인·취소, 삭제 저장, 전부 삭제 후 재시작 |
| 점수 히스토리 | `finish_session`, `show_history` | 날짜/시각·선택/실제 풀이 수·정답·힌트·점수, 완료/중단 구분과 영속성 |

## 4. 제약·제출

- Python 3.10 이상 문법, 실행 검증은 Python 3.13.12에서 수행. Python 3.10 문법은 AST로 별도 검사했으며 3.10 실행기에서 전체 테스트한 것은 아니다.
- 실행·테스트·증거 도구 모두 표준 라이브러리만 사용.
- 최소 2개 클래스와 기능별 메서드 분리.
- 데이터 파일은 코드 위치 기준 프로젝트 루트 `state.json`.
- 최소 10개 의미 있는 커밋과 브랜치 생성/병합 기록: 실제 Git 로그로 확인.
- Git 7개 명령의 의미는 README에 설명. 실패한 push와 아직 하지 못한 clone/pull을 성공으로 계산하지 않는다.
- 환경 / 추가 / 목록 / 플레이 / 점수 / Git graph 캡처: `docs/screenshots/`.
- 캡처는 **실제 CLI 출력 로그를 브라우저에서 표시한 화면**이다. 에디터나 네이티브 터미널 화면으로 위장하지 않는다. 평가자가 네이티브 터미널·에디터 캡처를 별도로 요구하면 로컬 터미널에서 재촬영한다.

## 5. 평가 범위와 학습자 확인

코드와 문서는 AI 도움으로 구현·검증했다. 자동 테스트 통과는 학습자가 과제 목표를 스스로 설명할 수 있다는 증거까지 대신하지 않는다. README의 목표별 설명을 읽고 코드를 직접 실행·변경하며 이해를 확인한다. 초기 데이터·실제 사용 데이터·테스트 데이터의 차이와 원격 미완료 상태를 숨기지 않는다.
