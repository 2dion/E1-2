#!/bin/bash
# 로그인된 macOS 터미널에서 실행한다. 인증 토큰을 출력하거나 파일로 복사하지 않는다.
# gh는 기존 보안 저장소를 사용하고, Git 인증 설정은 각 명령에만 적용한다.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export GH_CONFIG_DIR="$ROOT/.tools/gh-config"
GH="$ROOT/.tools/gh"
CLONE="/Users/leedongin/.aside/u/0/projects/codyssey-all-in-one/clone-practice/E1-2"
LOG="$ROOT/docs/evidence/git-remote-practice.txt"

# 실제 실행 출력만 기록한다. 토큰을 가져오는 gh auth token 명령은 사용하지 않는다.
exec > >(tee "$LOG") 2>&1
printf 'E1-2 원격 업로드·clone·pull 실제 실행\n'
date '+%Y-%m-%d %H:%M:%S %Z'

account="$($GH api user --jq .login)"
repository="$($GH repo view 2dion/E1-2 --json nameWithOwner --jq .nameWithOwner)"
if [ "$account" != '2dion' ] || [ "$repository" != '2dion/E1-2' ]; then
    printf '예상한 계정·저장소가 아니므로 중단합니다.\n'
    exit 1
fi
printf '계정: %s\n저장소: %s\n' "$account" "$repository"

# 기존 osxkeychain helper와 섞지 않고, 이 명령만 gh 인증을 쓰게 한다.
git_auth() {
    git -c credential.helper= -c "credential.helper=!\"$GH\" auth git-credential" "$@"
}

# 사용자 변경이 있으면 덮어쓰지 않는다. 새 로그 파일은 아직 추적되지 않아도 된다.
git diff --quiet
git diff --cached --quiet
if [ -e "$CLONE" ]; then
    printf '복제 목적지가 이미 존재해 자동 덮어쓰지 않습니다: %s\n' "$CLONE"
    exit 1
fi

# GitHub에서 병합한 PR 등 원격에 먼저 올라간 커밋을 받아 둔다. 뒤처진 채 push하면 거부된다.
printf '\n$ git pull --ff-only origin main (시작 전 동기화)\n'
git_auth pull --ff-only origin main

author_name="$(git config user.name)"
author_email="$(git config user.email)"
printf '\n$ git push origin main feature/quiz-play\n'
git_auth push origin main feature/quiz-play
printf '\n업로드 후 main 해시 확인\n'
local_head="$(git rev-parse HEAD)"
remote_head="$(git_auth ls-remote origin refs/heads/main | cut -f1)"
[ "$local_head" = "$remote_head" ]
printf '로컬·원격 일치: %s\n' "$local_head"

mkdir -p "$(dirname "$CLONE")"
printf '\n$ git clone https://github.com/2dion/E1-2.git %s\n' "$CLONE"
git_auth clone https://github.com/2dion/E1-2.git "$CLONE"
git -C "$CLONE" config user.name "$author_name"
git -C "$CLONE" config user.email "$author_email"

# 실습을 위한 실제 문서 개선을 복제본에서만 만들고 커밋한다.
printf '\n## 복제·동기화 실습 확인\n\n별도 원격 복제본에서 이 안내를 추가해 commit·push하고, 원래 작업 폴더에서 pull로 받아 동기화를 확인했다.\n' >> "$CLONE/README.md"
printf '\n$ git add README.md && git commit (복제본)\n'
git -C "$CLONE" add README.md
git -C "$CLONE" commit -m 'Docs: 원격 복제본에서 동기화 실습 안내 추가'
printf '\n$ git push origin main (복제본)\n'
git_auth -C "$CLONE" push origin main

printf '\n$ git pull --ff-only origin main (원본)\n'
git_auth pull --ff-only origin main
printf '\n$ grep 복제·동기화 README.md\n'
grep '복제·동기화' README.md
printf '\n최종 로컬·원격 main 해시 비교\n'
local_head="$(git rev-parse HEAD)"
remote_head="$(git_auth ls-remote origin refs/heads/main | cut -f1)"
[ "$local_head" = "$remote_head" ]
printf '동기화 완료: %s\n' "$local_head"
printf '\n$ git log --oneline --graph --all\n'
git log --oneline --graph --all
printf '\nE1-2_REMOTE_PRACTICE_SUCCESS\n'
