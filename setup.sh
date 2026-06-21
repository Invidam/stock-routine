#!/bin/bash
# stock-routine 초기 셋업 스크립트
# iCloud에 monthly/personal 파일을 동기화하고 심볼릭 링크를 설정합니다.
# git-tracked 파일(example-*, README.md)은 프로젝트에 유지됩니다.

set -e

ICLOUD_BASE="$HOME/Library/Mobile Documents/com~apple~CloudDocs/stock-routine-private"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== stock-routine setup ==="

# 디렉토리를 iCloud에 연결하는 함수
# 인자: <로컬 디렉토리명> <git-tracked 파일 패턴(optional)>
setup_icloud_link() {
    local DIR_NAME="$1"
    local GIT_PATTERNS="${2:-}"  # 공백 구분 패턴 (예: "example-* README.md")
    local ICLOUD_DIR="$ICLOUD_BASE/$DIR_NAME"
    local LOCAL_DIR="$PROJECT_DIR/$DIR_NAME"

    echo ""
    echo "--- $DIR_NAME ---"

    # iCloud 디렉토리 생성
    if [ ! -d "$ICLOUD_DIR" ]; then
        echo "  iCloud 디렉토리 생성: $ICLOUD_DIR"
        mkdir -p "$ICLOUD_DIR"
    else
        echo "  iCloud 디렉토리 이미 존재"
    fi

    if [ -d "$LOCAL_DIR" ] && [ ! -L "$LOCAL_DIR" ]; then
        echo "  기존 파일 iCloud로 이동"

        # 모든 파일 iCloud로 복사
        for f in "$LOCAL_DIR"/*; do
            [ -f "$f" ] || continue
            filename=$(basename "$f")
            if [ ! -f "$ICLOUD_DIR/$filename" ]; then
                cp "$f" "$ICLOUD_DIR/$filename"
                echo "    → iCloud: $filename"
            else
                echo "    이미 존재 (건너뜀): $filename"
            fi
        done

        # git-tracked 파일 임시 보관
        TEMP_DIR=$(mktemp -d)
        if [ -n "$GIT_PATTERNS" ]; then
            for pattern in $GIT_PATTERNS; do
                for f in "$LOCAL_DIR"/$pattern; do
                    [ -f "$f" ] && cp "$f" "$TEMP_DIR/"
                done
            done
        fi

        rm -rf "$LOCAL_DIR"
        ln -s "$ICLOUD_DIR" "$LOCAL_DIR"
        echo "  심볼릭 링크 생성: $DIR_NAME -> iCloud"

        # git-tracked 파일 복원
        for f in "$TEMP_DIR"/*; do
            [ -f "$f" ] && cp "$f" "$LOCAL_DIR/"
        done
        rm -rf "$TEMP_DIR"
    elif [ -L "$LOCAL_DIR" ]; then
        echo "  이미 심볼릭 링크 설정됨 — 건너뜀"
    else
        echo "  디렉토리 없음, 심볼릭 링크 생성"
        ln -s "$ICLOUD_DIR" "$LOCAL_DIR"
    fi

    echo "  $DIR_NAME/ -> $ICLOUD_DIR"
}

setup_icloud_link "monthly" "example-* README.md"
setup_icloud_link "personal"

echo ""
echo "=== 완료 ==="
echo "iCloud 동기화로 다른 Mac에서도 자동 공유됩니다."