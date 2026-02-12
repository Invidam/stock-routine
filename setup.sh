#!/bin/bash
# stock-routine 초기 셋업 스크립트
# iCloud에 monthly 파일을 동기화하고 심볼릭 링크를 설정합니다.
# git-tracked 파일(example-*, README.md)은 프로젝트에 유지됩니다.

set -e

ICLOUD_DIR="$HOME/Library/Mobile Documents/com~apple~CloudDocs/stock-routine-private/monthly"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
MONTHLY_DIR="$PROJECT_DIR/monthly"
GIT_FILES_DIR="$PROJECT_DIR/monthly-git"

echo "=== stock-routine setup ==="

# 1. iCloud 디렉토리 생성
if [ ! -d "$ICLOUD_DIR" ]; then
    echo "[1/4] iCloud 디렉토리 생성: $ICLOUD_DIR"
    mkdir -p "$ICLOUD_DIR"
else
    echo "[1/4] iCloud 디렉토리 이미 존재"
fi

# 2. 기존 monthly 파일 분리 (최초 1회)
if [ -d "$MONTHLY_DIR" ] && [ ! -L "$MONTHLY_DIR" ]; then
    echo "[2/4] 기존 monthly 파일 분리"

    # private yaml → iCloud로 복사
    for f in "$MONTHLY_DIR"/*.yaml "$MONTHLY_DIR"/*.yml; do
        [ -f "$f" ] || continue
        filename=$(basename "$f")
        # example 파일은 건너뛰기 (git에서 관리)
        if [[ "$filename" == example-* ]]; then
            continue
        fi
        if [ ! -f "$ICLOUD_DIR/$filename" ]; then
            cp "$f" "$ICLOUD_DIR/$filename"
            echo "  → iCloud: $filename"
        else
            echo "  이미 존재 (건너뜀): $filename"
        fi
    done

    # git-tracked 파일(example-*, README.md) → 임시 보관
    TEMP_DIR=$(mktemp -d)
    for f in "$MONTHLY_DIR"/example-* "$MONTHLY_DIR"/README.md; do
        [ -f "$f" ] && cp "$f" "$TEMP_DIR/"
    done

    # 기존 monthly 디렉토리 제거
    rm -rf "$MONTHLY_DIR"

    # 심볼릭 링크 생성
    ln -s "$ICLOUD_DIR" "$MONTHLY_DIR"
    echo "[3/4] 심볼릭 링크 생성: monthly -> iCloud"

    # git-tracked 파일을 iCloud(=심볼릭 링크 대상)에 복원
    for f in "$TEMP_DIR"/*; do
        [ -f "$f" ] && cp "$f" "$MONTHLY_DIR/"
    done
    rm -rf "$TEMP_DIR"
    echo "[4/4] git-tracked 파일 복원 (example-*, README.md)"
else
    if [ -L "$MONTHLY_DIR" ]; then
        echo "[2/4] 이미 심볼릭 링크 설정됨 — 건너뜀"
    else
        echo "[2/4] monthly 디렉토리 없음"
        ln -s "$ICLOUD_DIR" "$MONTHLY_DIR"
        echo "[3/4] 심볼릭 링크 생성: monthly -> iCloud"
    fi
    echo "[4/4] 완료"
fi

echo ""
echo "=== 완료 ==="
echo "monthly/ -> $ICLOUD_DIR"
echo "iCloud 동기화로 다른 Mac에서도 자동 공유됩니다."
echo ""
echo "포함된 파일:"
ls -1 "$MONTHLY_DIR"