"""
테스트 3: 포트폴리오 평가액 계산 (_calculate_portfolio_value)
- 환율 적용/미적용 분기
- 현재가 조회 실패 시 fallback
- CASH 처리 (이자 반영)
"""
import pytest
from unittest.mock import patch


class TestCalculatePortfolioValue:
    """_calculate_portfolio_value: (purchase_data, cash_invested, cash_value) → (invested, value)"""

    @patch('streamlit_app.utils.price_fetcher.get_multiple_prices')
    @patch('streamlit_app.utils.price_fetcher.get_current_price')
    def test_us_stock_with_exchange_rate(self, mock_price, mock_prices):
        """미국 주식: USD 가격 × 환율"""
        import streamlit_app.data_loader as dl

        mock_price.return_value = 1430.0  # KRW=X 환율
        mock_prices.return_value = {'SPY': 610.0}  # USD 가격

        purchase_data = [('SPY', 0.3632, 300_000)]

        invested, value = dl._calculate_portfolio_value(purchase_data, 0, 0)

        expected_value = int(0.3632 * 610.0 * 1430.0)
        assert invested == 300_000
        assert value == expected_value

    @patch('streamlit_app.utils.price_fetcher.get_multiple_prices')
    @patch('streamlit_app.utils.price_fetcher.get_current_price')
    def test_korean_stock_no_exchange(self, mock_price, mock_prices):
        """한국 주식: KRW 가격 그대로 (환율 미적용)"""
        import streamlit_app.data_loader as dl

        mock_price.return_value = 1430.0
        mock_prices.return_value = {'069500.KS': 36000.0}

        purchase_data = [('069500.KS', 14.2857, 500_000)]

        invested, value = dl._calculate_portfolio_value(purchase_data, 0, 0)

        expected_value = int(14.2857 * 36000.0)  # 환율 미적용
        assert invested == 500_000
        assert value == expected_value

    @patch('streamlit_app.utils.price_fetcher.get_multiple_prices')
    @patch('streamlit_app.utils.price_fetcher.get_current_price')
    def test_price_fetch_failure_fallback(self, mock_price, mock_prices):
        """현재가 조회 실패 시 → 원금으로 fallback"""
        import streamlit_app.data_loader as dl

        mock_price.return_value = 1430.0
        mock_prices.return_value = {}  # 조회 실패

        purchase_data = [('SPY', 0.3632, 300_000)]

        invested, value = dl._calculate_portfolio_value(purchase_data, 0, 0)

        # 조회 실패 → 원금을 평가액으로 사용
        assert invested == 300_000
        assert value == 300_000

    @patch('streamlit_app.utils.price_fetcher.get_multiple_prices')
    @patch('streamlit_app.utils.price_fetcher.get_current_price')
    def test_cash_added_separately(self, mock_price, mock_prices):
        """CASH: invested와 value가 별도 (이자 반영)"""
        import streamlit_app.data_loader as dl

        mock_price.return_value = 1430.0
        mock_prices.return_value = {'SPY': 610.0}

        purchase_data = [('SPY', 0.3632, 300_000)]
        cash_invested = 100_000
        cash_value = 102_000  # 이자 2,000원

        invested, value = dl._calculate_portfolio_value(purchase_data, cash_invested, cash_value)

        assert invested == 400_000  # 300,000 + 100,000
        spy_value = int(0.3632 * 610.0 * 1430.0)
        assert value == spy_value + 102_000  # SPY 평가액 + CASH 이자 포함

    @patch('streamlit_app.utils.price_fetcher.get_multiple_prices')
    @patch('streamlit_app.utils.price_fetcher.get_current_price')
    def test_cash_interest_affects_return(self, mock_price, mock_prices):
        """CASH 이자가 수익률에 반영되는지"""
        import streamlit_app.data_loader as dl

        mock_price.return_value = 1430.0
        mock_prices.return_value = {}

        # 주식 없이 CASH만
        purchase_data = []
        cash_invested = 1_000_000
        cash_value = 1_020_000  # 이자 2만원

        invested, value = dl._calculate_portfolio_value(purchase_data, cash_invested, cash_value)

        assert invested == 1_000_000
        assert value == 1_020_000
        return_rate = (value - invested) / invested * 100
        assert return_rate == pytest.approx(2.0)

    @patch('streamlit_app.utils.price_fetcher.get_multiple_prices')
    @patch('streamlit_app.utils.price_fetcher.get_current_price')
    def test_mixed_stocks(self, mock_price, mock_prices):
        """미국 + 한국 주식 혼합"""
        import streamlit_app.data_loader as dl

        mock_price.return_value = 1430.0
        mock_prices.return_value = {
            'SPY': 610.0,
            '069500.KS': 36000.0,
        }

        purchase_data = [
            ('SPY', 0.3632, 300_000),
            ('069500.KS', 14.2857, 500_000),
        ]

        invested, value = dl._calculate_portfolio_value(purchase_data, 100_000, 100_000)

        spy_value = int(0.3632 * 610.0 * 1430.0)
        kodex_value = int(14.2857 * 36000.0)
        expected_value = spy_value + kodex_value + 100_000

        assert invested == 900_000
        assert value == expected_value

    @patch('streamlit_app.utils.price_fetcher.get_multiple_prices')
    @patch('streamlit_app.utils.price_fetcher.get_current_price')
    def test_empty_portfolio(self, mock_price, mock_prices):
        """빈 포트폴리오"""
        import streamlit_app.data_loader as dl

        mock_price.return_value = 1430.0
        mock_prices.return_value = {}

        invested, value = dl._calculate_portfolio_value([], 0, 0)

        assert invested == 0
        assert value == 0

    @patch('streamlit_app.utils.price_fetcher.get_multiple_prices')
    @patch('streamlit_app.utils.price_fetcher.get_current_price')
    def test_exchange_rate_failure_uses_default(self, mock_price, mock_prices):
        """환율 조회 실패 시 기본값 1450 사용"""
        import streamlit_app.data_loader as dl

        mock_price.return_value = None  # 환율 조회 실패
        mock_prices.return_value = {'SPY': 610.0}

        purchase_data = [('SPY', 0.3632, 300_000)]

        invested, value = dl._calculate_portfolio_value(purchase_data, 0, 0)

        # 기본 환율 1450 적용 (DEFAULT_EXCHANGE_RATE)
        expected_value = int(0.3632 * 610.0 * 1450)
        assert value == expected_value

    @patch('streamlit_app.utils.price_fetcher.get_multiple_prices')
    @patch('streamlit_app.utils.price_fetcher.get_current_price')
    def test_zero_price_uses_invested(self, mock_price, mock_prices):
        """현재가가 0이면 원금 사용"""
        import streamlit_app.data_loader as dl

        mock_price.return_value = 1430.0
        mock_prices.return_value = {'SPY': 0}

        purchase_data = [('SPY', 0.3632, 300_000)]

        invested, value = dl._calculate_portfolio_value(purchase_data, 0, 0)

        assert value == 300_000  # 원금 fallback