"""
SQLite 데이터베이스 초기화 스크립트
테이블 생성 및 스키마 설정
"""
import sqlite3
from pathlib import Path


def init_database(db_path: str = "portfolio.db"):
    """
    SQLite 데이터베이스를 초기화하고 테이블을 생성합니다.

    Args:
        db_path: 데이터베이스 파일 경로 (기본값: portfolio.db)
    """
    # 데이터베이스 연결
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 1. months 테이블 생성
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS months (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year_month TEXT NOT NULL UNIQUE,
                exchange_rate REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. accounts 테이블 생성
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                broker TEXT NOT NULL,
                fee REAL NOT NULL DEFAULT 0.0,
                FOREIGN KEY (month_id) REFERENCES months(id) ON DELETE CASCADE
            )
        """)

        # 3. holdings 테이블 생성
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS holdings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                ticker_mapping TEXT NOT NULL,
                amount INTEGER NOT NULL,
                target_ratio REAL NOT NULL,
                asset_type TEXT DEFAULT 'STOCK',
                interest_rate REAL,
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
            )
        """)

        # 4. analyzed_holdings 테이블 생성 (ETF 구성 종목)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analyzed_holdings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month_id INTEGER NOT NULL,
                account_id INTEGER,
                source_ticker TEXT NOT NULL,
                stock_symbol TEXT NOT NULL,
                stock_name TEXT NOT NULL,
                holding_percent REAL NOT NULL,
                my_amount INTEGER NOT NULL,
                asset_type TEXT DEFAULT 'STOCK',
                analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (month_id) REFERENCES months(id) ON DELETE CASCADE,
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
            )
        """)

        # 5. analyzed_sectors 테이블 생성 (섹터별 비중)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analyzed_sectors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month_id INTEGER NOT NULL,
                account_id INTEGER,
                source_ticker TEXT NOT NULL,
                sector_name TEXT NOT NULL,
                sector_percent REAL NOT NULL,
                my_amount INTEGER NOT NULL,
                asset_type TEXT DEFAULT 'STOCK',
                analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (month_id) REFERENCES months(id) ON DELETE CASCADE,
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
            )
        """)

        # 6. analysis_metadata 테이블 생성 (분석 메타데이터)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analysis_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month_id INTEGER NOT NULL,
                ticker TEXT NOT NULL,
                status TEXT NOT NULL,
                error_message TEXT,
                holdings_count INTEGER DEFAULT 0,
                sectors_count INTEGER DEFAULT 0,
                analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (month_id) REFERENCES months(id) ON DELETE CASCADE
            )
        """)

        # 7. purchase_history 테이블 생성 (적립식 투자 매수 이력)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS purchase_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                asset_type TEXT NOT NULL,
                year_month TEXT NOT NULL,
                quantity REAL NOT NULL,
                input_amount INTEGER NOT NULL,
                purchase_date TEXT NOT NULL,
                price_at_purchase REAL,
                currency TEXT DEFAULT 'USD',
                exchange_rate REAL,
                account_id INTEGER,
                note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
            )
        """)

        # 8. current_holdings_summary 뷰 생성 (종목별 보유 수량 집계)
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS current_holdings_summary AS
            SELECT
                ticker,
                asset_type,
                SUM(quantity) as total_quantity,
                SUM(input_amount) as total_invested,
                CASE
                    WHEN SUM(quantity) > 0 THEN SUM(input_amount) / SUM(quantity)
                    ELSE 0
                END as avg_price
            FROM purchase_history
            GROUP BY ticker, asset_type
        """)

        # 인덱스 생성 (조회 성능 향상)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_accounts_month
            ON accounts(month_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_holdings_account
            ON holdings(account_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_holdings_asset_type
            ON holdings(asset_type)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_months_year_month
            ON months(year_month)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_analyzed_holdings_month
            ON analyzed_holdings(month_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_analyzed_holdings_stock
            ON analyzed_holdings(stock_symbol)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_analyzed_holdings_account
            ON analyzed_holdings(account_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_analyzed_holdings_asset_type
            ON analyzed_holdings(asset_type)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_analyzed_sectors_month
            ON analyzed_sectors(month_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_analyzed_sectors_account
            ON analyzed_sectors(account_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_analyzed_sectors_asset_type
            ON analyzed_sectors(asset_type)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_analysis_metadata_month
            ON analysis_metadata(month_id)
        """)

        # 변경사항 저장
        conn.commit()
        print(f"✅ 데이터베이스 초기화 완료: {db_path}")
        print("   - months 테이블 생성")
        print("   - accounts 테이블 생성")
        print("   - holdings 테이블 생성")
        print("   - analyzed_holdings 테이블 생성")
        print("   - analyzed_sectors 테이블 생성")
        print("   - analysis_metadata 테이블 생성")
        print("   - purchase_history 테이블 생성")
        print("   - current_holdings_summary 뷰 생성")
        print("   - 인덱스 생성 완료")

    except sqlite3.Error as e:
        print(f"❌ 데이터베이스 초기화 실패: {e}")
        conn.rollback()
        raise

    finally:
        # 연결 종료
        conn.close()


if __name__ == "__main__":
    # 스크립트 직접 실행 시 DB 초기화
    init_database()