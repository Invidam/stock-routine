"""
테스트 6: 현재가 조회 로직
- evaluate_accumulative.get_current_price: 환율 적용 포함
- price_fetcher.get_current_price: 원시 USD 가격 반환
- 두 함수의 차이점 검증
"""
import pytest
from unittest.mock import patch, MagicMock


class TestEvaluateGetCurrentPrice:
    """core/evaluate_accumulative.py의 get_current_price (KRW 환산 포함)"""

    @patch('core.evaluate_accumulative.yf')
    def test_us_stock_applies_exchange_rate(self, mock_yf):
        """미국 주식: USD × 환율 → KRW"""
        from core.evaluate_accumulative import get_current_price

        mock_spy = MagicMock()
        mock_spy.info = {'currentPrice': 610.0}
        mock_krw = MagicMock()
        mock_krw.info = {'regularMarketPrice': 1430.0}

        def ticker_factory(symbol):
            if symbol == 'KRW=X':
                return mock_krw
            return mock_spy

        mock_yf.Ticker.side_effect = ticker_factory

        price = get_current_price('SPY')
        assert price == pytest.approx(610.0 * 1430.0)

    @patch('core.evaluate_accumulative.yf')
    def test_korean_stock_no_exchange(self, mock_yf):
        """한국 주식: KRW 그대로"""
        from core.evaluate_accumulative import get_current_price

        mock_ticker = MagicMock()
        mock_ticker.info = {'currentPrice': 36000.0}
        mock_yf.Ticker.return_value = mock_ticker

        price = get_current_price('069500.KS')
        assert price == pytest.approx(36000.0)

    @patch('core.evaluate_accumulative.yf')
    def test_korean_kosdaq_stock(self, mock_yf):
        """코스닥 주식(.KQ)도 환율 미적용"""
        from core.evaluate_accumulative import get_current_price

        mock_ticker = MagicMock()
        mock_ticker.info = {'currentPrice': 15000.0}
        mock_yf.Ticker.return_value = mock_ticker

        price = get_current_price('247540.KQ')
        assert price == pytest.approx(15000.0)

    @patch('core.evaluate_accumulative.yf')
    def test_fallback_price_fields(self, mock_yf):
        """currentPrice 없으면 regularMarketPrice → previousClose 순서"""
        from core.evaluate_accumulative import get_current_price

        mock_ticker = MagicMock()
        mock_ticker.info = {
            'currentPrice': None,
            'regularMarketPrice': 605.0,
        }
        mock_krw = MagicMock()
        mock_krw.info = {'regularMarketPrice': 1430.0}

        def ticker_factory(symbol):
            if symbol == 'KRW=X':
                return mock_krw
            return mock_ticker

        mock_yf.Ticker.side_effect = ticker_factory

        price = get_current_price('SPY')
        assert price == pytest.approx(605.0 * 1430.0)

    @patch('core.evaluate_accumulative.yf')
    def test_all_fields_none_returns_none(self, mock_yf):
        """모든 가격 필드 None → None"""
        from core.evaluate_accumulative import get_current_price

        mock_ticker = MagicMock()
        mock_ticker.info = {
            'currentPrice': None,
            'regularMarketPrice': None,
            'previousClose': None,
        }
        mock_yf.Ticker.return_value = mock_ticker

        price = get_current_price('SPY')
        assert price is None

    @patch('core.evaluate_accumulative.yf')
    def test_yfinance_exception_returns_none(self, mock_yf):
        """yfinance 예외 → None"""
        from core.evaluate_accumulative import get_current_price

        mock_yf.Ticker.side_effect = Exception("Network Error")

        price = get_current_price('SPY')
        assert price is None

    @patch('core.evaluate_accumulative.yf')
    def test_exchange_rate_failure_uses_default(self, mock_yf):
        """환율 조회 실패 시 기본값 1450"""
        from core.evaluate_accumulative import get_current_price

        mock_spy = MagicMock()
        mock_spy.info = {'currentPrice': 610.0}
        mock_krw = MagicMock()
        mock_krw.info = {}  # regularMarketPrice 없음

        call_count = [0]

        def ticker_factory(symbol):
            if symbol == 'KRW=X':
                call_count[0] += 1
                if call_count[0] == 1:
                    # get 은 기본값 1450.0 반환
                    return mock_krw
                raise Exception("fail")
            return mock_spy

        mock_yf.Ticker.side_effect = ticker_factory

        price = get_current_price('SPY')
        # info.get('regularMarketPrice', 1450.0) → 1450.0
        assert price == pytest.approx(610.0 * 1450.0)


class TestPriceFetcherGetCurrentPrice:
    """streamlit_app/utils/price_fetcher.py의 get_current_price (원시 가격)"""

    @patch('streamlit_app.utils.price_fetcher.st')
    @patch('streamlit_app.utils.price_fetcher.yf')
    def test_fast_info_priority(self, mock_yf, mock_st):
        """fast_info.last_price 우선"""
        mock_st.cache_data = lambda **kwargs: lambda f: f

        # 직접 함수 정의 (캐시 우회)
        from streamlit_app.utils.price_fetcher import get_current_price

        mock_ticker = MagicMock()
        mock_ticker.fast_info.get = lambda key, default=None: 610.5 if key == 'last_price' else default
        mock_yf.Ticker.return_value = mock_ticker

        # 캐시가 적용된 함수 직접 호출
        price = get_current_price.__wrapped__('SPY') if hasattr(get_current_price, '__wrapped__') else get_current_price('SPY')
        assert price == pytest.approx(610.5)

    @patch('streamlit_app.utils.price_fetcher.st')
    @patch('streamlit_app.utils.price_fetcher.yf')
    def test_returns_none_for_other(self, mock_yf, mock_st):
        """OTHER 티커 → None"""
        mock_st.cache_data = lambda **kwargs: lambda f: f
        from streamlit_app.utils.price_fetcher import get_current_price

        fn = get_current_price.__wrapped__ if hasattr(get_current_price, '__wrapped__') else get_current_price
        result = fn('OTHER')
        assert result is None

    @patch('streamlit_app.utils.price_fetcher.st')
    @patch('streamlit_app.utils.price_fetcher.yf')
    def test_returns_none_for_empty(self, mock_yf, mock_st):
        """빈 문자열 → None"""
        mock_st.cache_data = lambda **kwargs: lambda f: f
        from streamlit_app.utils.price_fetcher import get_current_price

        fn = get_current_price.__wrapped__ if hasattr(get_current_price, '__wrapped__') else get_current_price
        result = fn('')
        assert result is None
        result2 = fn(None)
        assert result2 is None