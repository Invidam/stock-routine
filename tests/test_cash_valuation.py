"""
테스트: CASH 자산 평가금액 계산 (월별 필터링)

버그 배경:
- CASH 투자원금은 해당 월 1회분만 표시 (holdings.amount)
- 평가금액은 purchase_history 전체 기간을 합산
- → 수익률이 비정상적으로 높게 표시 (예: +306%)

수정 후:
- 특정 월 선택 시 → 해당 월 purchase_history만으로 평가
- "전체 기간" 선택 시 → 전체 purchase_history 합산
"""
import sqlite3
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime


@pytest.fixture
def cash_db(initialized_db):
    """
    CASH 자산이 여러 월에 걸쳐 있는 DB

    - 2025-01, 2025-02, 2025-03: 3개월
    - 저축 계좌: 일반적금(300,000/월, 연 3.5% 단리), 주택청약(50,000/월, 연 2.3% 단리)
    """
    db_path = initialized_db
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    months = ['2025-01', '2025-02', '2025-03']
    month_ids = []
    account_ids = []

    for ym in months:
        cursor.execute("INSERT INTO months (year_month) VALUES (?)", (ym,))
        mid = cursor.lastrowid
        month_ids.append(mid)

        cursor.execute(
            "INSERT INTO accounts (month_id, name, type, broker, fee) "
            "VALUES (?, '저축 계좌', '일반', '일반은행', 0.0)", (mid,))
        aid = cursor.lastrowid
        account_ids.append(aid)

        # holdings - 매월 동일
        cursor.execute(
            "INSERT INTO holdings (account_id, name, ticker_mapping, amount, target_ratio, asset_type, interest_rate) "
            "VALUES (?, '일반적금', '일반적금', 300000, 85.7, 'CASH', 0.035)", (aid,))
        cursor.execute(
            "INSERT INTO holdings (account_id, name, ticker_mapping, amount, target_ratio, asset_type, interest_rate) "
            "VALUES (?, '주택청약종합저축', '주택청약종합저축', 50000, 14.3, 'CASH', 0.023)", (aid,))

    # purchase_history - 매월 납입
    for i, (ym, aid) in enumerate(zip(months, account_ids)):
        day = 18
        cursor.execute("""
            INSERT INTO purchase_history
            (ticker, asset_type, year_month, purchase_date, quantity, input_amount,
             price_at_purchase, currency, exchange_rate, account_id, interest_rate, interest_type)
            VALUES ('일반적금', 'CASH', ?, ?, 300000, 300000,
                    1.0, 'KRW', NULL, ?, 0.035, 'simple')
        """, (ym, f"{ym}-{day:02d}", aid))

        cursor.execute("""
            INSERT INTO purchase_history
            (ticker, asset_type, year_month, purchase_date, quantity, input_amount,
             price_at_purchase, currency, exchange_rate, account_id, interest_rate, interest_type)
            VALUES ('주택청약종합저축', 'CASH', ?, ?, 50000, 50000,
                    1.0, 'KRW', NULL, ?, 0.023, 'simple')
        """, (ym, f"{ym}-{day:02d}", aid))

    conn.commit()
    conn.close()
    return db_path


def _call_get_account_holdings(year_month, account_id, db_path):
    """st.cache_data 데코레이터를 우회하여 get_account_holdings 호출"""
    import streamlit_app.data_loader as dl
    fn = dl.get_account_holdings.__wrapped__ if hasattr(dl.get_account_holdings, '__wrapped__') else dl.get_account_holdings
    return fn(year_month, account_id, db_path)


class TestCashMonthlyFiltering:
    """CASH 자산의 월별 평가금액 필터링 테스트"""

    @patch('streamlit_app.utils.price_fetcher.get_multiple_prices')
    @patch('streamlit_app.utils.price_fetcher.get_current_price')
    def test_specific_month_cash_value_matches_principal(self, mock_price, mock_prices, cash_db):
        """특정 월 선택 시 CASH 평가금액은 해당 월 원금 + 이자만 반영"""
        mock_price.return_value = 1430.0
        mock_prices.return_value = {}

        # 2025-01 월의 account_id 조회
        conn = sqlite3.connect(cash_db)
        acc_id = conn.execute(
            "SELECT a.id FROM accounts a JOIN months m ON a.month_id = m.id "
            "WHERE m.year_month = '2025-01' AND a.name = '저축 계좌'"
        ).fetchone()[0]
        conn.close()

        df = _call_get_account_holdings('2025-01', acc_id, cash_db)

        # 일반적금 행 확인
        savings = df[df['종목명'] == '일반적금']
        assert len(savings) == 1

        row = savings.iloc[0]
        invested = row['투자원금']
        value = row['평가금액']

        # 투자원금: 300,000원 (해당 월 1회분)
        assert invested == 300_000

        # 평가금액: 원금 + 이자 (해당 월 1건만이므로 원금과 큰 차이 없어야 함)
        # 최대 1년치 이자 = 300,000 * 0.035 = 10,500원
        # 수익률은 절대 100%를 넘을 수 없음
        assert value < invested * 2, f"평가금액({value:,})이 투자원금({invested:,})의 2배를 초과: 월별 필터링 실패"

        # 수익률 검증: 적금 수익률은 연 3.5% 이하여야 함
        return_rate = row['수익률(%)']
        assert return_rate < 10, f"수익률({return_rate}%)이 비정상적으로 높음"

    @patch('streamlit_app.utils.price_fetcher.get_multiple_prices')
    @patch('streamlit_app.utils.price_fetcher.get_current_price')
    def test_specific_month_not_accumulating_other_months(self, mock_price, mock_prices, cash_db):
        """특정 월 선택 시 다른 월의 납입액이 포함되지 않아야 함"""
        mock_price.return_value = 1430.0
        mock_prices.return_value = {}

        # 2025-03 (3번째 월) - 이전 2개월 납입이 포함되면 안 됨
        conn = sqlite3.connect(cash_db)
        acc_id = conn.execute(
            "SELECT a.id FROM accounts a JOIN months m ON a.month_id = m.id "
            "WHERE m.year_month = '2025-03' AND a.name = '저축 계좌'"
        ).fetchone()[0]
        conn.close()

        df = _call_get_account_holdings('2025-03', acc_id, cash_db)

        savings = df[df['종목명'] == '일반적금']
        value = savings.iloc[0]['평가금액']

        # 3개월 전체 합산 시: 300,000 * 3 + 이자 ≈ 900,000 이상
        # 1개월만 반영 시: 300,000 + 약간의 이자 ≈ 300,000~310,500
        assert value < 600_000, (
            f"평가금액({value:,})이 너무 큼: 다른 월 데이터가 포함된 것으로 보임"
        )

    @patch('streamlit_app.utils.price_fetcher.get_multiple_prices')
    @patch('streamlit_app.utils.price_fetcher.get_current_price')
    def test_all_months_accumulates_all(self, mock_price, mock_prices, cash_db):
        """'전체 기간' 선택 시 모든 월의 CASH가 합산됨"""
        mock_price.return_value = 1430.0
        mock_prices.return_value = {}

        # 전체 기간은 latest month의 account_id 사용
        conn = sqlite3.connect(cash_db)
        acc_id = conn.execute(
            "SELECT a.id FROM accounts a JOIN months m ON a.month_id = m.id "
            "WHERE m.year_month = '2025-03' AND a.name = '저축 계좌'"
        ).fetchone()[0]
        conn.close()

        df = _call_get_account_holdings('전체 기간', acc_id, cash_db)

        savings = df[df['종목명'] == '일반적금']
        row = savings.iloc[0]
        invested = row['투자원금']
        value = row['평가금액']

        # 전체 기간 투자원금: 300,000 * 3개월 = 900,000
        assert invested >= 900_000, (
            f"전체 기간 투자원금({invested:,})이 너무 작음: 전체 합산이 안 된 것으로 보임"
        )

        # 전체 기간 평가금액: 900,000 + 이자
        assert value >= 900_000, (
            f"전체 기간 평가금액({value:,})이 너무 작음: 전체 합산이 안 된 것으로 보임"
        )

        # 수익률은 합리적이어야 함 (투자원금과 평가금액 모두 합산되므로)
        return_rate = row['수익률(%)']
        assert return_rate < 10, (
            f"전체 기간 수익률({return_rate}%)이 비정상: "
            f"투자원금({invested:,})과 평가금액({value:,})의 불일치"
        )

    @patch('streamlit_app.utils.price_fetcher.get_multiple_prices')
    @patch('streamlit_app.utils.price_fetcher.get_current_price')
    def test_cash_profit_rate_reasonable(self, mock_price, mock_prices, cash_db):
        """CASH 수익률이 합리적인 범위 내인지 확인"""
        mock_price.return_value = 1430.0
        mock_prices.return_value = {}

        conn = sqlite3.connect(cash_db)
        acc_id = conn.execute(
            "SELECT a.id FROM accounts a JOIN months m ON a.month_id = m.id "
            "WHERE m.year_month = '2025-02' AND a.name = '저축 계좌'"
        ).fetchone()[0]
        conn.close()

        df = _call_get_account_holdings('2025-02', acc_id, cash_db)

        for _, row in df[df['자산유형'] == 'CASH'].iterrows():
            return_rate = row['수익률(%)']
            # 적금 수익률은 연 5% 이내가 정상
            assert -1 <= return_rate <= 5, (
                f"{row['종목명']} 수익률({return_rate}%)이 비정상: "
                f"투자원금={row['투자원금']:,}, 평가금액={row['평가금액']:,}"
            )

    @patch('streamlit_app.utils.price_fetcher.get_multiple_prices')
    @patch('streamlit_app.utils.price_fetcher.get_current_price')
    def test_multiple_cash_products_independent(self, mock_price, mock_prices, cash_db):
        """여러 CASH 종목이 서로 독립적으로 평가됨"""
        mock_price.return_value = 1430.0
        mock_prices.return_value = {}

        conn = sqlite3.connect(cash_db)
        acc_id = conn.execute(
            "SELECT a.id FROM accounts a JOIN months m ON a.month_id = m.id "
            "WHERE m.year_month = '2025-01' AND a.name = '저축 계좌'"
        ).fetchone()[0]
        conn.close()

        df = _call_get_account_holdings('2025-01', acc_id, cash_db)

        savings = df[df['종목명'] == '일반적금'].iloc[0]
        housing = df[df['종목명'] == '주택청약종합저축'].iloc[0]

        # 일반적금: 300,000원
        assert savings['투자원금'] == 300_000
        # 주택청약: 50,000원
        assert housing['투자원금'] == 50_000

        # 각각의 평가금액이 원금 근처여야 함
        assert savings['평가금액'] < 400_000, "일반적금 평가금액 비정상"
        assert housing['평가금액'] < 100_000, "주택청약 평가금액 비정상"