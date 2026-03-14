"""
테스트 1: 수익률 계산 순수 함수 (calculate_profit_rate)
- 정상 케이스, 엣지 케이스, 경계값
"""
import pytest
from streamlit_app.utils.price_fetcher import calculate_profit_rate


class TestCalculateProfitRate:
    """수익률 = (현재가치 - 투자액) / 투자액 × 100"""

    def test_positive_return(self):
        """양수 수익률"""
        result = calculate_profit_rate(1_000_000, 1_100_000)
        assert result == pytest.approx(10.0)

    def test_negative_return(self):
        """음수 수익률 (손실)"""
        result = calculate_profit_rate(1_000_000, 900_000)
        assert result == pytest.approx(-10.0)

    def test_zero_return(self):
        """수익률 0% (본전)"""
        result = calculate_profit_rate(500_000, 500_000)
        assert result == pytest.approx(0.0)

    def test_double_return(self):
        """100% 수익 (2배)"""
        result = calculate_profit_rate(1_000_000, 2_000_000)
        assert result == pytest.approx(100.0)

    def test_total_loss(self):
        """전액 손실 (-100%)"""
        result = calculate_profit_rate(1_000_000, 0)
        assert result == pytest.approx(-100.0)

    def test_zero_invested(self):
        """투자액 0원 → 0% (division by zero 방지)"""
        result = calculate_profit_rate(0, 100_000)
        assert result == 0.0

    def test_negative_invested(self):
        """투자액 음수 → 0% (비정상 입력 방어)"""
        result = calculate_profit_rate(-100_000, 50_000)
        assert result == 0.0

    def test_small_return(self):
        """소수점 수익률"""
        result = calculate_profit_rate(1_000_000, 1_005_000)
        assert result == pytest.approx(0.5)

    def test_large_return(self):
        """큰 수익률 (10배)"""
        result = calculate_profit_rate(100_000, 1_000_000)
        assert result == pytest.approx(900.0)

    def test_float_precision(self):
        """부동소수점 정밀도"""
        # 300,000원 투자 → 300,001원 → 아주 작은 수익률
        result = calculate_profit_rate(300_000, 300_001)
        assert result == pytest.approx(1 / 300_000 * 100, rel=1e-6)
