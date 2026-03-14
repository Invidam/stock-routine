"""
테스트 2: 수량 계산 (calculate_quantity)
- 투자액 → 수량 변환 정확성
- 환율 적용 여부
- 과거 주가 조회 실패 시 폴백
"""
import pytest
from unittest.mock import patch, MagicMock
from data.import_monthly_purchases import (
    calculate_quantity,
    get_historical_price,
    get_exchange_rate,
)


class TestCalculateQuantity:
    """quantity = input_amount / price_krw"""

    @patch('data.import_monthly_purchases.get_exchange_rate')
    @patch('data.import_monthly_purchases.get_historical_price')
    def test_us_stock_quantity(self, mock_hist, mock_exrate, initialized_db):
        """미국 주식: 투자액 / (USD가격 × 환율) = 수량"""
        mock_hist.return_value = ('2025-01-26', 590.0, 'USD')
        mock_exrate.return_value = 1400.0

        result = calculate_quantity(
            ticker='SPY',
            input_amount=300_000,
            year_month='2025-01',
            purchase_day=26,
            db_path=initialized_db
        )

        expected_price_krw = 590.0 * 1400.0  # 826,000
        expected_qty = 300_000 / expected_price_krw  # 0.3632...

        assert result['quantity'] == pytest.approx(expected_qty, rel=1e-4)
        assert result['price_krw'] == pytest.approx(expected_price_krw)
        assert result['currency'] == 'USD'
        assert result['exchange_rate'] == 1400.0
        assert result['purchase_date'] == '2025-01-26'

    @patch('data.import_monthly_purchases.get_historical_price')
    def test_korean_stock_quantity(self, mock_hist, initialized_db):
        """한국 주식: 투자액 / KRW가격 = 수량 (환율 없음)"""
        mock_hist.return_value = ('2025-01-26', 35000.0, 'KRW')

        result = calculate_quantity(
            ticker='069500.KS',
            input_amount=500_000,
            year_month='2025-01',
            purchase_day=26,
            db_path=initialized_db
        )

        expected_qty = 500_000 / 35_000  # 14.2857...
        assert result['quantity'] == pytest.approx(expected_qty, rel=1e-4)
        assert result['price_krw'] == 35000.0
        assert result['currency'] == 'KRW'
        assert result['exchange_rate'] is None

    @patch('data.import_monthly_purchases.get_price_from_db')
    @patch('data.import_monthly_purchases.get_historical_price')
    def test_yfinance_fail_fallback_to_db(self, mock_hist, mock_db_price, populated_db):
        """yfinance 실패 시 DB에서 과거 주가 조회"""
        mock_hist.return_value = None  # yfinance 실패
        mock_db_price.return_value = 826000.0  # DB에서 KRW 가격 반환

        result = calculate_quantity(
            ticker='SPY',
            input_amount=300_000,
            year_month='2025-01',
            purchase_day=26,
            db_path=populated_db
        )

        expected_qty = 300_000 / 826_000
        assert result['quantity'] == pytest.approx(expected_qty, rel=1e-4)
        assert result['currency'] == 'KRW'  # DB 폴백 시 KRW로 처리

    @patch('data.import_monthly_purchases.get_price_from_db')
    @patch('data.import_monthly_purchases.get_historical_price')
    def test_all_price_sources_fail(self, mock_hist, mock_db_price, initialized_db):
        """모든 가격 소스 실패 시 ValueError"""
        mock_hist.return_value = None
        mock_db_price.return_value = None

        with pytest.raises(ValueError, match="주가를 찾을 수 없습니다"):
            calculate_quantity(
                ticker='UNKNOWN',
                input_amount=100_000,
                year_month='2025-01',
                purchase_day=26,
                db_path=initialized_db
            )

    @patch('data.import_monthly_purchases.get_exchange_rate')
    @patch('data.import_monthly_purchases.get_historical_price')
    def test_leftover_calculation(self, mock_hist, mock_exrate, initialized_db):
        """잔돈 계산: 투자액 - (정수 수량 × 주가)"""
        mock_hist.return_value = ('2025-01-26', 100.0, 'USD')
        mock_exrate.return_value = 1400.0

        # 주당 140,000원, 투자액 300,000원 → 2주 + 잔돈 20,000원
        result = calculate_quantity(
            ticker='SPY',
            input_amount=300_000,
            year_month='2025-01',
            purchase_day=26,
            db_path=initialized_db
        )

        price_krw = 100.0 * 1400.0  # 140,000
        expected_leftover = 300_000 - (int(300_000 / price_krw) * price_krw)
        assert result['leftover'] == int(expected_leftover)


class TestGetHistoricalPrice:
    """과거 주가 조회"""

    @patch('yfinance.Ticker')
    def test_returns_tuple_format(self, mock_ticker_cls):
        """반환값 형식: (날짜, 종가, 통화)"""
        import pandas as pd

        mock_ticker = MagicMock()
        mock_ticker_cls.return_value = mock_ticker

        mock_hist = pd.DataFrame(
            {'Close': [590.5]},
            index=pd.to_datetime(['2025-01-24'])
        )
        mock_ticker.history.return_value = mock_hist

        result = get_historical_price('SPY', '2025-01-26')

        assert result is not None
        date, price, currency = result
        assert date == '2025-01-24'
        assert price == pytest.approx(590.5)
        assert currency == 'USD'

    @patch('yfinance.Ticker')
    def test_korean_stock_currency(self, mock_ticker_cls):
        """한국 주식은 KRW 통화"""
        import pandas as pd

        mock_ticker = MagicMock()
        mock_ticker_cls.return_value = mock_ticker

        mock_hist = pd.DataFrame(
            {'Close': [35000.0]},
            index=pd.to_datetime(['2025-01-24'])
        )
        mock_ticker.history.return_value = mock_hist

        result = get_historical_price('069500.KS', '2025-01-26')

        assert result is not None
        _, _, currency = result
        assert currency == 'KRW'

    @patch('yfinance.Ticker')
    def test_empty_history_returns_none(self, mock_ticker_cls):
        """데이터 없으면 None"""
        import pandas as pd

        mock_ticker = MagicMock()
        mock_ticker_cls.return_value = mock_ticker
        mock_ticker.history.return_value = pd.DataFrame()

        result = get_historical_price('INVALID', '2025-01-26')
        assert result is None

    @patch('yfinance.Ticker')
    def test_exception_returns_none(self, mock_ticker_cls):
        """예외 발생 시 None"""
        mock_ticker_cls.side_effect = Exception("API Error")

        result = get_historical_price('SPY', '2025-01-26')
        assert result is None


class TestGetExchangeRate:
    """환율 조회"""

    @patch('yfinance.Ticker')
    def test_returns_float(self, mock_ticker_cls):
        """환율은 float"""
        import pandas as pd

        mock_ticker = MagicMock()
        mock_ticker_cls.return_value = mock_ticker

        mock_hist = pd.DataFrame(
            {'Close': [1430.5]},
            index=pd.to_datetime(['2025-01-25'])
        )
        mock_ticker.history.return_value = mock_hist

        result = get_exchange_rate('2025-01-26')
        assert isinstance(result, float)
        assert result == pytest.approx(1430.5)

    @patch('yfinance.Ticker')
    def test_fallback_default_rate(self, mock_ticker_cls):
        """조회 실패 시 기본값 1450"""
        mock_ticker_cls.side_effect = Exception("API Error")

        result = get_exchange_rate('2025-01-26')
        assert result == 1450.0
