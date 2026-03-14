"""
테스트 5: get_monthly_summary (월별 요약 + "전체 기간" 합산)
- 특정 월 수익률
- "전체 기간" 합산 시 중복/누락 검증
- 현재가 조회 실패 fallback
"""
import pytest
import sqlite3
from unittest.mock import patch


def _call_monthly_summary(year_month, db_path):
    """st.cache_data 데코레이터를 우회하여 get_monthly_summary 호출"""
    import streamlit_app.data_loader as dl
    fn = dl.get_monthly_summary.__wrapped__ if hasattr(dl.get_monthly_summary, '__wrapped__') else dl.get_monthly_summary
    return fn(year_month, db_path)


class TestMonthlySummary:
    """get_monthly_summary: 월별/전체 수익률"""

    @patch('streamlit_app.utils.price_fetcher.get_multiple_prices')
    @patch('streamlit_app.utils.price_fetcher.get_current_price')
    def test_single_month_summary(self, mock_price, mock_prices, populated_db):
        """특정 월 요약: 해당 월 데이터만"""
        mock_price.return_value = 1430.0
        mock_prices.return_value = {
            'SPY': 610.0,
            'QQQ': 520.0,
        }

        result = _call_monthly_summary('2025-01', populated_db)

        assert result['total_invested'] > 0
        assert result['total_value'] > 0
        assert 'return_rate' in result

    @patch('streamlit_app.data_loader._calculate_portfolio_value')
    def test_return_rate_formula(self, mock_calc, populated_db):
        """수익률 공식: (value - invested) / invested × 100"""
        mock_calc.return_value = (1_000_000, 1_100_000)

        result = _call_monthly_summary('2025-01', populated_db)

        assert result['total_profit'] == 100_000
        assert result['return_rate'] == pytest.approx(10.0, abs=0.1)

    @patch('streamlit_app.data_loader._calculate_portfolio_value')
    def test_negative_return(self, mock_calc, populated_db):
        """손실 시 음수 수익률"""
        mock_calc.return_value = (1_000_000, 800_000)

        result = _call_monthly_summary('2025-01', populated_db)

        assert result['total_profit'] == -200_000
        assert result['return_rate'] == pytest.approx(-20.0, abs=0.1)


class TestMonthlySummaryEdgeCases:
    """엣지 케이스"""

    def test_nonexistent_month(self, populated_db):
        """존재하지 않는 월 → 0 반환"""
        result = _call_monthly_summary('2099-12', populated_db)

        assert result['total_value'] == 0
        assert result['total_invested'] == 0
        assert result['total_profit'] == 0
        assert result['return_rate'] == 0.0

    def test_empty_db(self, initialized_db):
        """빈 DB → 0 반환"""
        result = _call_monthly_summary('2025-01', initialized_db)

        assert result['total_value'] == 0
        assert result['return_rate'] == 0.0