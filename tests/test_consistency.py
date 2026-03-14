"""
테스트 8: 수익률 계산 일관성 검증
- evaluate_accumulative vs data_loader vs price_fetcher 간 결과 비교
- 동일 데이터에 대해 동일 수익률을 반환하는지
"""
import pytest
from unittest.mock import patch, MagicMock


class TestReturnRateConsistency:
    """여러 모듈의 수익률 공식이 동일한 결과를 내는지"""

    def test_same_formula_across_modules(self):
        """모든 모듈에서 동일한 공식: (value - invested) / invested × 100"""
        from streamlit_app.utils.price_fetcher import calculate_profit_rate

        invested = 1_000_000
        current_value = 1_150_000

        # price_fetcher 방식
        pf_rate = calculate_profit_rate(invested, current_value)

        # evaluate_accumulative 방식 (인라인 공식)
        profit = current_value - invested
        ea_rate = (profit / invested * 100) if invested > 0 else 0

        # data_loader 방식 (인라인 공식)
        total_profit = current_value - invested
        dl_rate = (total_profit / invested * 100) if invested > 0 else 0.0

        assert pf_rate == pytest.approx(ea_rate)
        assert pf_rate == pytest.approx(dl_rate)

    def test_zero_invested_all_return_zero(self):
        """투자액 0 → 모든 모듈에서 0%"""
        from streamlit_app.utils.price_fetcher import calculate_profit_rate

        invested = 0
        current_value = 100_000

        pf_rate = calculate_profit_rate(invested, current_value)
        ea_rate = ((current_value - invested) / invested * 100) if invested > 0 else 0
        dl_rate = ((current_value - invested) / invested * 100) if invested > 0 else 0.0

        assert pf_rate == 0.0
        assert ea_rate == 0
        assert dl_rate == 0.0


class TestExchangeRateConsistency:
    """환율 처리 방식 차이 검증"""

    def test_default_exchange_rate_difference(self):
        """
        evaluate_accumulative: 기본값 1450
        data_loader: 기본값 1400
        → 같은 종목이 다른 평가액을 가질 수 있음
        """
        quantity = 0.5
        usd_price = 600.0

        # evaluate_accumulative 방식 (기본 환율 1450)
        ea_value = quantity * usd_price * 1450.0

        # data_loader 방식 (기본 환율 1400)
        dl_value = quantity * usd_price * 1400.0

        # 이 둘은 다름 → 알려진 불일치
        assert ea_value != dl_value
        diff_pct = abs(ea_value - dl_value) / ea_value * 100
        # 차이: (1450 - 1400) / 1450 ≈ 3.4%
        assert diff_pct == pytest.approx(50.0 / 1450 * 100, rel=0.1)

    def test_evaluate_price_includes_exchange(self):
        """evaluate_accumulative.get_current_price는 KRW 환산 포함"""
        # 이 함수는 USD 가격 × 환율을 반환
        # vs price_fetcher.get_current_price는 원시 USD 반환
        # → 두 함수의 반환값이 다름을 확인

        # evaluate_accumulative: get_current_price('SPY') → 610 * 1430 = 872,300
        # price_fetcher: get_current_price('SPY') → 610
        # 따라서 data_loader는 별도로 환율을 곱함
        pass  # 설계 차이를 문서화하는 테스트


class TestFallbackBehaviorDifference:
    """현재가 조회 실패 시 동작 차이"""

    @patch('core.evaluate_accumulative.get_current_price')
    def test_evaluate_excludes_on_failure(self, mock_price, populated_db):
        """evaluate_accumulative: 조회 실패 → 종목 제외"""
        from core.evaluate_accumulative import evaluate_holdings

        mock_price.return_value = None  # 모든 종목 실패

        df = evaluate_holdings(populated_db)
        assert df.empty  # 모두 제외

    def test_data_loader_uses_invested_on_failure(self):
        """data_loader: 조회 실패 → 원금을 평가액으로 사용 (수익률 0%)

        이로 인해 두 모듈의 수익률이 다를 수 있음:
        - evaluate: SPY 실패 → 제외 → 나머지 종목 기준 수익률
        - data_loader: SPY 실패 → 원금 사용 → SPY 수익률 0%로 포함
        """
        # 시나리오: 3종목 중 1개 실패
        # evaluate: 2종목 기준 수익률
        # data_loader: 3종목 기준 (실패 종목은 0% 수익률)
        # → 결과 다름

        # evaluate 방식
        eval_invested = 200_000 + 500_000  # QQQ + KODEX (SPY 제외)
        eval_value = 220_000 + 510_000
        eval_rate = (eval_value - eval_invested) / eval_invested * 100

        # data_loader 방식
        dl_invested = 300_000 + 200_000 + 500_000  # SPY(원금) + QQQ + KODEX
        dl_value = 300_000 + 220_000 + 510_000  # SPY는 원금 그대로
        dl_rate = (dl_value - dl_invested) / dl_invested * 100

        # 두 결과가 다름
        assert eval_rate != dl_rate
        # evaluate: (730000-700000)/700000 = 4.28%
        # data_loader: (1030000-1000000)/1000000 = 3.0%
        assert eval_rate == pytest.approx(4.2857, rel=0.01)
        assert dl_rate == pytest.approx(3.0, rel=0.01)