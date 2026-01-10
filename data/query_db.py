"""
SQLite DB 데이터 조회 및 검증 스크립트
"""
import sqlite3
from typing import List, Tuple


def query_all_months(db_path: str = "portfolio.db") -> List[Tuple]:
    """
    DB에 저장된 모든 월 데이터를 조회합니다.

    Args:
        db_path: SQLite DB 파일 경로

    Returns:
        (id, year_month, created_at) 튜플 리스트
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM months ORDER BY year_month DESC")
    results = cursor.fetchall()

    conn.close()
    return results


def query_month_summary(year_month: str, db_path: str = "portfolio.db"):
    """
    특정 월의 포트폴리오 요약 정보를 조회하고 출력합니다.

    Args:
        year_month: 조회할 년-월 (예: '2025-12')
        db_path: SQLite DB 파일 경로
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # 컬럼명으로 접근 가능
    cursor = conn.cursor()

    # 1. 월 정보 조회
    cursor.execute("SELECT * FROM months WHERE year_month = ?", (year_month,))
    month = cursor.fetchone()

    if not month:
        print(f"❌ {year_month} 데이터를 찾을 수 없습니다.")
        conn.close()
        return

    month_id = month['id']
    exchange_rate = month['exchange_rate'] if 'exchange_rate' in month.keys() else None

    print(f"\n📅 {year_month} 포트폴리오 요약")
    if exchange_rate:
        print(f"💱 환율: 1 USD = {exchange_rate:,.2f} KRW")
    print("=" * 80)

    # 2. 계좌별 정보 조회
    cursor.execute(
        """
        SELECT id, name, type, broker, fee
        FROM accounts
        WHERE month_id = ?
        ORDER BY id
        """,
        (month_id,)
    )
    accounts = cursor.fetchall()

    total_amount = 0
    account_count = 0

    for account in accounts:
        account_id = account['id']
        account_count += 1

        print(f"\n📂 계좌 #{account_count}: {account['name']}")
        print(f"   유형: {account['type']} | 증권사: {account['broker']} | 운영수수료: {account['fee']:.2%}")
        print(f"   {'종목명':<30} {'티커':<10} {'금액':>12} {'목표비중':>8}")
        print(f"   {'-' * 70}")

        # 3. 보유 종목 조회
        cursor.execute(
            """
            SELECT name, ticker_mapping, amount, target_ratio
            FROM holdings
            WHERE account_id = ?
            ORDER BY amount DESC
            """,
            (account_id,)
        )
        holdings = cursor.fetchall()

        account_total = 0
        for holding in holdings:
            account_total += holding['amount']
            total_amount += holding['amount']
            print(
                f"   {holding['name']:<30} "
                f"{holding['ticker_mapping']:<10} "
                f"{holding['amount']:>12,}원 "
                f"{holding['target_ratio']:>7.1%}"
            )

        print(f"   {'-' * 70}")
        print(f"   계좌 합계: {account_total:,}원\n")

    print("=" * 80)
    print(f"💰 전체 포트폴리오 합계: {total_amount:,}원")
    print(f"📊 총 계좌 수: {account_count}개")

    conn.close()


def query_ticker_aggregation(year_month: str, db_path: str = "portfolio.db"):
    """
    특정 월의 티커별 집계 정보를 조회합니다.

    Args:
        year_month: 조회할 년-월 (예: '2025-12')
        db_path: SQLite DB 파일 경로
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 월 ID 조회
    cursor.execute("SELECT id FROM months WHERE year_month = ?", (year_month,))
    month = cursor.fetchone()

    if not month:
        print(f"❌ {year_month} 데이터를 찾을 수 없습니다.")
        conn.close()
        return

    month_id = month['id']

    # 티커별 집계 쿼리
    cursor.execute(
        """
        SELECT
            h.ticker_mapping,
            SUM(h.amount) as total_amount,
            SUM(h.target_ratio) as total_ratio,
            COUNT(*) as count
        FROM holdings h
        INNER JOIN accounts a ON h.account_id = a.id
        WHERE a.month_id = ?
        GROUP BY h.ticker_mapping
        ORDER BY total_amount DESC
        """,
        (month_id,)
    )
    results = cursor.fetchall()

    print(f"\n📊 {year_month} 티커별 집계")
    print("=" * 60)
    print(f"{'티커':<10} {'총 투자금액':>15} {'총 목표비중':>12} {'보유 건수':>8}")
    print("-" * 60)

    total = 0
    for row in results:
        total += row['total_amount']
        print(
            f"{row['ticker_mapping']:<10} "
            f"{row['total_amount']:>14,}원 "
            f"{row['total_ratio']:>11.1%} "
            f"{row['count']:>8}건"
        )

    print("-" * 60)
    print(f"{'합계':<10} {total:>14,}원")
    print("=" * 60)

    conn.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SQLite DB 데이터 조회")
    parser.add_argument("--db", default="portfolio.db", help="SQLite DB 파일 경로")
    parser.add_argument("--list", action="store_true", help="저장된 모든 월 목록 조회")
    parser.add_argument("--month", help="조회할 년-월 (예: 2025-12)")
    parser.add_argument("--ticker", action="store_true", help="티커별 집계 조회 (--month와 함께 사용)")

    args = parser.parse_args()

    if args.list:
        # 모든 월 목록 조회
        months = query_all_months(args.db)
        if months:
            print("\n📋 저장된 월 데이터 목록:")
            print("-" * 50)
            for month in months:
                print(f"  • {month[1]} (생성일: {month[2]})")
            print()
        else:
            print("❌ 저장된 데이터가 없습니다.")

    elif args.month:
        # 특정 월 요약 조회
        query_month_summary(args.month, args.db)

        # 티커별 집계 조회
        if args.ticker:
            query_ticker_aggregation(args.month, args.db)

    else:
        parser.print_help()