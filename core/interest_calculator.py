"""
적금 이자 계산 유틸리티

적립식 적금의 이자를 단리/복리로 계산하는 함수를 제공합니다.
각 월별 납입액에 대해 경과 개월수를 기준으로 이자를 계산합니다.
"""
from datetime import datetime
from typing import Optional


def calc_months_elapsed(purchase_date: str, eval_date: Optional[str] = None) -> int:
    """
    매수일로부터 평가일까지 경과 개월수 계산

    Args:
        purchase_date: 매수 날짜 (YYYY-MM-DD)
        eval_date: 평가 날짜 (YYYY-MM-DD), None이면 오늘

    Returns:
        경과 개월수 (최소 0)
    """
    purchase = datetime.strptime(purchase_date, '%Y-%m-%d')
    if eval_date:
        today = datetime.strptime(eval_date, '%Y-%m-%d')
    else:
        today = datetime.now()

    months = (today.year - purchase.year) * 12 + (today.month - purchase.month)
    return max(0, months)


def calc_deposit_interest(
    principal: int,
    annual_rate: float,
    months_elapsed: int,
    interest_type: str = 'simple'
) -> float:
    """
    적금 납입액 1건에 대한 이자 계산

    Args:
        principal: 납입 원금 (원)
        annual_rate: 연이율 (예: 0.035 = 3.5%)
        months_elapsed: 경과 개월수
        interest_type: 'simple'(단리) 또는 'compound'(복리)

    Returns:
        이자 금액 (원)
    """
    if annual_rate <= 0 or months_elapsed <= 0:
        return 0.0

    if interest_type == 'compound':
        monthly_rate = annual_rate / 12
        return principal * ((1 + monthly_rate) ** months_elapsed - 1)
    else:
        # 단리: 원금 × 연이율 × (경과월수 / 12)
        return principal * annual_rate * (months_elapsed / 12)


def calc_cash_current_value(
    principal: int,
    annual_rate: Optional[float],
    purchase_date: str,
    interest_type: str = 'simple',
    eval_date: Optional[str] = None,
) -> float:
    """
    적금 1건의 현재 평가액(원금 + 이자) 계산

    Args:
        principal: 납입 원금
        annual_rate: 연이율 (None이면 이자 없이 원금 반환)
        purchase_date: 매수일 (YYYY-MM-DD)
        interest_type: 'simple' 또는 'compound'
        eval_date: 평가 기준일 (None이면 오늘)

    Returns:
        평가액 (원금 + 이자)
    """
    if not annual_rate or annual_rate <= 0:
        return float(principal)

    months = calc_months_elapsed(purchase_date, eval_date)
    interest = calc_deposit_interest(principal, annual_rate, months, interest_type)
    return float(principal + interest)
