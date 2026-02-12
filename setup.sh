#!/bin/bash
# stock-routine 초기 셋업 스크립트
# iCloud에 monthly 파일을 동기화하고 심볼릭 링크를 설정합니다.

set -e

ICLOUD_DIR="$HOME/Library/Mobile Documents/com~apple~CloudDocs/stock-routine-private/monthly"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
MONTHLY_DIR="$PROJECT_DIR/monthly"

echo "=== stock-routine setup ==="

# 1. iCloud 디렉토리 생성
if [ ! -d "$ICLOUD_DIR" ]; then
    echo "[1/3] iCloud 디렉토리 생성: $ICLOUD_DIR"
    mkdir -p "$ICLOUD_DIR"
else
    echo "[1/3] iCloud 디렉토리 이미 존재"
fi

# 2. 기존 monthly 파일을 iCloud로 이동 (최초 1회)
if [ -d "$MONTHLY_DIR" ] && [ ! -L "$MONTHLY_DIR" ]; then
    echo "[2/3] 기존 monthly 파일을 iCloud로 이동"
    # yaml 파일만 이동 (example, README는 git에서 관리)
    for f in "$MONTHLY_DIR"/*.yaml "$MONTHLY_DIR"/*.yml; do
        [ -f "$f" ] || continue
        filename=$(basename "$f")
        # example 파일은 건너뛰기 (git에서 관리)
        if [[ "$filename" == example-* ]]; then
            continue
        fi
        if [ ! -f "$ICLOUD_DIR/$filename" ]; then
            cp "$f" "$ICLOUD_DIR/$filename"
            echo "  복사: $filename"
        else
            echo "  이미 존재 (건너뜀): $filename"
        fi
    done
    # 기존 디렉토리에서 private yaml 삭제 후 디렉토리 제거
    for f in "$MONTHLY_DIR"/*.yaml "$MONTHLY_DIR"/*.yml; do
        [ -f "$f" ] || continue
        filename=$(basename "$f")
        if [[ "$filename" != example-* ]]; then
            rm "$f"
        fi
    done
    # git-tracked 파일(example, README)을 임시로 보관
    TEMP_DIR=$(mktemp -d)
    for f in "$MONTHLY_DIR"/*; do
        [ -f "$f" ] && cp "$f" "$ICLOUD_DIR/"
    done
    rm -rf "$MONTHLY_DIR"
else
    echo "[2/3] 이동할 파일 없음 (이미 심볼릭 링크이거나 디렉토리 없음)"
fi

# 3. 심볼릭 링크 생성
if [ -L "$MONTHLY_DIR" ]; then
    echo "[3/3] 심볼릭 링크 이미 존재"
else
    echo "[3/3] 심볼릭 링크 생성: monthly -> iCloud"
    ln -s "$ICLOUD_DIR" "$MONTHLY_DIR"
fi

echo ""
echo "=== 완료 ==="
echo "monthly/ -> $ICLOUD_DIR"
echo "iCloud 동기화로 다른 Mac에서도 자동 공유됩니다."