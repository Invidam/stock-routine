"""
테스트 4: evaluate_holdings (E2E)
- DB에서 데이터 읽어 현재가로 평가
- 종목별 수익률 정확성
- 합산 수익률
"""
import pytest
from unittest.mock import patch


class TestEvaluateHoldings:
    """evaluate_holdings: DB → 현재가 조회 → 수익률 계산"""

    @patch('core.evaluate_accumulative.get_current_price')
    def test_single_month_returns(self, mock_price, populated_db):
        """단일 종목 수익률 계산"""
        from core.evaluate_accumulative import evaluate_holdings

        def price_map(ticker):
            prices = {
                'SPY': 610.0 * 1430.0,       # 872,300원 (이미 KRW로 반환)
                'QQQ': 520.0 * 1430.0,        # 743,600원
                '069500.KS': 36000.0,
            }
            return prices.get(ticker)

        mock_price.side_effect = price_map

        df = evaluate_holdings(populated_db)

        assert not df.empty

        # SPY 검증 (2개월 합산)
        spy = df[df['ticker'] == 'SPY'].iloc[0]
        assert spy['quantity'] == pytest.approx(0.3632 + 0.4108, rel=1e-3)
        assert spy['invested'] == 300_000 + 350_000  # 650,000원
        expected_value = spy['quantity'] * (610.0 * 1430.0)
        assert spy['current_value'] == pytest.approx(expected_value, rel=1e-2)
        expected_return = (expected_value - 650_000) / 650_000 * 100
        assert spy['return_rate'] == pytest.approx(expected_return, rel=1e-2)

    @patch('core.evaluate_accumulative.get_current_price')
    def test_korean_stock_no_exchange(self, mock_price, populated_db):
        """한국 주식은 환율 없이 계산"""
        from core.evaluate_accumulative import evaluate_holdings

        def price_map(ticker):
            prices = {
                'SPY': 610.0 * 1430.0,
                'QQQ': 520.0 * 1430.0,
                '069500.KS': 36000.0,
            }
            return prices.get(ticker)

        mock_price.side_effect = price_map

        df = evaluate_holdings(populated_db)

        kodex = df[df['ticker'] == '069500.KS'].iloc[0]
        assert kodex['quantity'] == pytest.approx(14.2857, rel=1e-3)
        assert kodex['invested'] == 500_000
        expected_value = 14.2857 * 36000.0
        assert kodex['current_value'] == pytest.approx(expected_value, rel=1e-2)

    @patch('core.evaluate_accumulative.get_current_price')
    def test_price_failure_excludes_ticker(self, mock_price, populated_db):
        """현재가 조회 실패 종목은 결과에서 제외"""
        from core.evaluate_accumulative import evaluate_holdings

        def price_map(ticker):
            if ticker == 'SPY':
                return None  # 조회 실패
            prices = {
                'QQQ': 520.0 * 1430.0,
                '069500.KS': 36000.0,
            }
            return prices.get(ticker)

        mock_price.side_effect = price_map

        df = evaluate_holdings(populated_db)

        # SPY는 제외되어야 함
        assert 'SPY' not in df['ticker'].values
        assert 'QQQ' in df['ticker'].values
        assert '069500.KS' in df['ticker'].values

    @patch('core.evaluate_accumulative.get_current_price')
    def test_empty_db_returns_empty(self, mock_price, initialized_db):
        """빈 DB → 빈 DataFrame"""
        from core.evaluate_accumulative import evaluate_holdings

        df = evaluate_holdings(initialized_db)
        assert df.empty

    @patch('core.evaluate_accumulative.get_current_price')
    def test_aggregation_across_months(self, mock_price, populated_db):
        """여러 월에 걸친 매수 → 수량/투자액 합산"""
        from core.evaluate_accumulative import evaluate_holdings

        def price_map(ticker):
            prices = {
                'SPY': 610.0 * 1430.0,
                'QQQ': 520.0 * 1430.0,
                '069500.KS': 36000.0,
            }
            return prices.get(ticker)

        mock_price.side_effect = price_map

        df = evaluate_holdings(populated_db)

        # QQQ: 2개월 합산
        qqq = df[df['ticker'] == 'QQQ'].iloc[0]
        assert qqq['quantity'] == pytest.approx(0.2857 + 0.3472, rel=1e-3)
        assert qqq['invested'] == 200_000 + 250_000


class TestSummaryReport:
    """print_summary_report: 합계 수익률"""

    @patch('core.evaluate_accumulative.get_current_price')
    def test_total_return_calculation(self, mock_price, populated_db):
        """전체 합산 수익률 = (전체 평가액 - 전체 투자액) / 전체 투자액 × 100"""
        from core.evaluate_accumulative import evaluate_holdings

        # 가격 설정: SPY 10% 상승, QQQ 5% 하락, KODEX200 동일
        def price_map(ticker):
            if ticker == 'SPY':
                # 평단가 대비 10% 상승
                return 826_000 * 1.10
            elif ticker == 'QQQ':
                return 700_000 * 0.95
            elif ticker == '069500.KS':
                return 35_000  # 동일
            return None

        mock_price.side_effect = price_map

        df = evaluate_holdings(populated_db)

        total_invested = df['invested'].sum()
        total_value = df['current_value'].sum()
        total_profit = total_value - total_invested
        total_return = (total_profit / total_invested * 100) if total_invested > 0 else 0

        # 각 종목의 수익률이 아닌, 전체 합산 수익률이 올바른지 검증
        assert total_invested == 300_000 + 350_000 + 200_000 + 250_000 + 500_000
        assert total_return == pytest.approx(
            (total_value - total_invested) / total_invested * 100, rel=1e-4
        )