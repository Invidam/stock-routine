"""
월별 YAML 데이터를 SQLite DB에 임포트하는 스크립트
"""
import sqlite3
import yaml
from pathlib import Path
from typing import Dict, List, Any


def load_yaml(file_path: str) -> Dict[str, Any]:
    """
    YAML 파일을 읽어서 딕셔너리로 반환합니다.

    Args:
        file_path: YAML 파일 경로

    Returns:
        파싱된 데이터 딕셔너리
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def extract_year_month_from_filename(file_path: str) -> str:
    """
    파일명에서 년-월 정보를 추출합니다.
    예: 'monthly/2025-11.yaml' -> '2025-11'

    Args:
        file_path: YAML 파일 경로

    Returns:
        'YYYY-MM' 형식의 문자열
    """
    filename = Path(file_path).stem  # 확장자 제거
    return filename


def import_monthly_data(yaml_path: str, db_path: str = "portfolio.db", overwrite: bool = False):
    """
    월별 YAML 데이터를 SQLite DB에 임포트합니다.

    Args:
        yaml_path: 임포트할 YAML 파일 경로
        db_path: SQLite DB 파일 경로
        overwrite: True면 기존 데이터 삭제 후 재삽입
    """
    # 1. YAML 파일 읽기
    print(f"📂 YAML 파일 읽는 중: {yaml_path}")
    data = load_yaml(yaml_path)
    year_month = extract_year_month_from_filename(yaml_path)

    # 2. DB 연결
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 3. 기존 데이터 확인
        cursor.execute("SELECT id FROM months WHERE year_month = ?", (year_month,))
        existing_month = cursor.fetchone()

        if existing_month:
            if overwrite:
                print(f"⚠️  {year_month} 데이터가 이미 존재합니다. 삭제 후 재삽입합니다.")
                cursor.execute("DELETE FROM months WHERE year_month = ?", (year_month,))
            else:
                print(f"❌ {year_month} 데이터가 이미 존재합니다. --overwrite 옵션을 사용하세요.")
                return

        # 4. months 테이블에 삽입
        cursor.execute(
            "INSERT INTO months (year_month) VALUES (?)",
            (year_month,)
        )
        month_id = cursor.lastrowid
        print(f"✅ months 테이블 삽입: {year_month} (ID: {month_id})")

        # 5. accounts 및 holdings 삽입
        accounts = data.get('accounts', [])
        total_accounts = 0
        total_holdings = 0

        for account in accounts:
            # accounts 테이블 삽입
            cursor.execute(
                """
                INSERT INTO accounts (month_id, name, type, broker, fee)
                VALUES (?, ?, ?, ?, ?)
                """,
                (month_id, account['name'], account['type'], account['broker'], account.get('fee', 0.0))
            )
            account_id = cursor.lastrowid
            total_accounts += 1

            # holdings 테이블 삽입
            holdings_list = account.get('holdings', [])

            # 계좌별 총 금액 계산 (target_ratio 자동 계산용)
            total_amount = sum(h['amount'] for h in holdings_list)

            for holding in holdings_list:
                # asset_type 읽기 (기본값: 'STOCK')
                asset_type = holding.get('asset_type', 'STOCK')

                # interest_rate 읽기 (선택적)
                interest_rate = holding.get('interest_rate')

                # target_ratio 자동 계산
                target_ratio = holding['amount'] / total_amount if total_amount > 0 else 0.0

                cursor.execute(
                    """
                    INSERT INTO holdings
                    (account_id, name, ticker_mapping, amount, target_ratio, asset_type, interest_rate)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        account_id,
                        holding['name'],
                        holding['ticker_mapping'],
                        holding['amount'],
                        target_ratio,
                        asset_type,
                        interest_rate
                    )
                )
                total_holdings += 1

        # 6. 커밋
        conn.commit()
        print(f"✅ 데이터 임포트 완료!")
        print(f"   - 계좌: {total_accounts}개")
        print(f"   - 보유 종목: {total_holdings}개")

    except sqlite3.Error as e:
        print(f"❌ 데이터베이스 오류: {e}")
        conn.rollback()
        raise

    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        conn.rollback()
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="월별 YAML 데이터를 SQLite DB에 임포트")
    parser.add_argument("yaml_file", help="임포트할 YAML 파일 경로 (예: monthly/2025-11-purchase.yaml)")
    parser.add_argument("--db", default="portfolio.db", help="SQLite DB 파일 경로 (기본값: portfolio.db)")
    parser.add_argument("--overwrite", action="store_true", help="기존 데이터 덮어쓰기")

    args = parser.parse_args()

    # YAML 파일 존재 확인
    if not Path(args.yaml_file).exists():
        print(f"❌ 파일을 찾을 수 없습니다: {args.yaml_file}")
        exit(1)

    # 임포트 실행
    import_monthly_data(args.yaml_file, args.db, args.overwrite)