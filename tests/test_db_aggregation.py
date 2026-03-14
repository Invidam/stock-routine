"""
테스트 7: DB 집계 로직
- purchase_history의 SUM(quantity), SUM(input_amount) 정확성
- 여러 월/계좌에 걸친 같은 종목 합산
- current_holdings_summary 뷰
"""
import sqlite3
import pytest


class TestPurchaseHistoryAggregation:
    """purchase_history 집계 쿼리"""

    def test_sum_quantity_by_ticker(self, populated_db):
        """종목별 수량 합산"""
        conn = sqlite3.connect(populated_db)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ticker, SUM(quantity) as total_qty, SUM(input_amount) as total_invested
            FROM purchase_history
            GROUP BY ticker
            ORDER BY ticker
        """)
        rows = {r[0]: (r[1], r[2]) for r in cursor.fetchall()}
        conn.close()

        # SPY: 0.3632 + 0.4108 = 0.7740
        assert rows['SPY'][0] == pytest.approx(0.3632 + 0.4108, rel=1e-3)
        assert rows['SPY'][1] == 650_000

        # QQQ: 0.2857 + 0.3472 = 0.6329
        assert rows['QQQ'][0] == pytest.approx(0.2857 + 0.3472, rel=1e-3)
        assert rows['QQQ'][1] == 450_000

        # KODEX200: 14.2857 (1개월만)
        assert rows['069500.KS'][0] == pytest.approx(14.2857, rel=1e-3)
        assert rows['069500.KS'][1] == 500_000

    def test_avg_price_calculation(self, populated_db):
        """평단가 = SUM(투자액) / SUM(수량)"""
        conn = sqlite3.connect(populated_db)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                ticker,
                SUM(input_amount) / NULLIF(SUM(quantity), 0) as avg_price
            FROM purchase_history
            GROUP BY ticker
        """)
        rows = {r[0]: r[1] for r in cursor.fetchall()}
        conn.close()

        # SPY 평단가: 650,000 / 0.7740 ≈ 839,793원
        spy_avg = 650_000 / (0.3632 + 0.4108)
        assert rows['SPY'] == pytest.approx(spy_avg, rel=1e-2)

    def test_group_by_ticker_and_asset_type(self, populated_db):
        """ticker + asset_type으로 그룹핑"""
        conn = sqlite3.connect(populated_db)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ticker, asset_type, COUNT(*) as cnt
            FROM purchase_history
            GROUP BY ticker, asset_type
        """)
        rows = cursor.fetchall()
        conn.close()

        # 모든 종목이 고유한 (ticker, asset_type) 조합
        tickers = [(r[0], r[1]) for r in rows]
        assert ('SPY', 'STOCK') in tickers
        assert ('QQQ', 'STOCK') in tickers
        assert ('069500.KS', 'STOCK') in tickers

    def test_filter_by_month(self, populated_db):
        """월별 필터링"""
        conn = sqlite3.connect(populated_db)
        cursor = conn.cursor()

        # 2025-01만
        cursor.execute("""
            SELECT ticker, SUM(quantity), SUM(input_amount)
            FROM purchase_history
            WHERE year_month = '2025-01'
            GROUP BY ticker
        """)
        jan = {r[0]: (r[1], r[2]) for r in cursor.fetchall()}

        assert 'SPY' in jan
        assert jan['SPY'][0] == pytest.approx(0.3632, rel=1e-3)
        assert jan['SPY'][1] == 300_000

        # 2025-02만
        cursor.execute("""
            SELECT ticker, SUM(quantity), SUM(input_amount)
            FROM purchase_history
            WHERE year_month = '2025-02'
            GROUP BY ticker
        """)
        feb = {r[0]: (r[1], r[2]) for r in cursor.fetchall()}

        assert 'SPY' in feb
        assert feb['SPY'][0] == pytest.approx(0.4108, rel=1e-3)
        assert '069500.KS' not in feb  # 1월에만 매수

        conn.close()

    def test_filter_by_account(self, populated_db):
        """계좌별 필터링"""
        conn = sqlite3.connect(populated_db)
        cursor = conn.cursor()

        # ISA 계좌의 종목들
        cursor.execute("""
            SELECT ph.ticker, SUM(ph.quantity)
            FROM purchase_history ph
            JOIN accounts a ON ph.account_id = a.id
            WHERE a.name = 'ISA'
            GROUP BY ph.ticker
        """)
        isa = {r[0]: r[1] for r in cursor.fetchall()}

        assert 'SPY' in isa
        assert 'QQQ' in isa
        assert '069500.KS' not in isa  # 연금저축 계좌

        # 연금저축
        cursor.execute("""
            SELECT ph.ticker, SUM(ph.quantity)
            FROM purchase_history ph
            JOIN accounts a ON ph.account_id = a.id
            WHERE a.name = '연금저축'
            GROUP BY ph.ticker
        """)
        pension = {r[0]: r[1] for r in cursor.fetchall()}

        assert '069500.KS' in pension
        assert 'SPY' not in pension

        conn.close()


class TestCurrentHoldingsSummaryView:
    """current_holdings_summary 뷰"""

    def test_view_exists(self, populated_db):
        """뷰가 정상 생성되었는지"""
        conn = sqlite3.connect(populated_db)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master WHERE type='view' AND name='current_holdings_summary'
        """)
        result = cursor.fetchone()
        conn.close()

        assert result is not None

    def test_view_aggregation(self, populated_db):
        """뷰의 집계 결과"""
        conn = sqlite3.connect(populated_db)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM current_holdings_summary ORDER BY ticker")
        rows = cursor.fetchall()
        conn.close()

        # (ticker, asset_type, total_quantity, total_invested, avg_price)
        data = {r[0]: r for r in rows}

        assert '069500.KS' in data
        assert data['069500.KS'][2] == pytest.approx(14.2857, rel=1e-3)  # quantity
        assert data['069500.KS'][3] == 500_000  # invested

        assert 'SPY' in data
        assert data['SPY'][2] == pytest.approx(0.7740, rel=1e-2)
        assert data['SPY'][3] == 650_000


class TestPurchaseHistoryWithNullAccountId:
    """account_id가 NULL인 경우 (잠재 버그)"""

    def test_null_account_id_record(self, initialized_db):
        """account_id가 NULL인 레코드 → JOIN 시 누락될 수 있음"""
        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()

        # account_id 없이 삽입
        cursor.execute("""
            INSERT INTO purchase_history
            (ticker, asset_type, year_month, purchase_date, quantity, input_amount)
            VALUES ('SPY', 'STOCK', '2025-01', '2025-01-26', 0.5, 400000)
        """)
        conn.commit()

        # account_id로 JOIN하면 누락됨
        cursor.execute("""
            SELECT SUM(quantity)
            FROM purchase_history ph
            JOIN accounts a ON ph.account_id = a.id
            WHERE ph.ticker = 'SPY'
        """)
        join_result = cursor.fetchone()[0]

        # account_id 없이 직접 조회하면 포함됨
        cursor.execute("""
            SELECT SUM(quantity)
            FROM purchase_history
            WHERE ticker = 'SPY'
        """)
        direct_result = cursor.fetchone()[0]

        conn.close()

        # JOIN 결과는 None (누락), 직접 조회는 0.5
        assert join_result is None
        assert direct_result == pytest.approx(0.5)