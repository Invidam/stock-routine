"""
숫자 및 날짜 포맷팅 유틸리티
"""
from datetime import datetime, timedelta
from calendar import monthrange


def format_currency(value: float, currency: str = '원') -> str:
    """
    금액 포맷팅 (천 단위 콤마)

    Args:
        value: 금액
        currency: 통화 단위

    Returns:
        포맷팅된 문자열 (예: '1,234,567원')
    """
    return f"{int(value):,}{currency}"


def format_percent(value: float, decimals: int = 1, include_sign: bool = False) -> str:
    """
    퍼센트 포맷팅

    Args:
        value: 퍼센트 값 (5.0 = 5%)
        decimals: 소수점 자릿수
        include_sign: +/- 부호 포함 여부

    Returns:
        포맷팅된 문자열 (예: '+5.0%', '5.0%')
    """
    if include_sign:
        return f"{value:+.{decimals}f}%"
    else:
        return f"{value:.{decimals}f}%"


def format_shares(value: float, decimals: int = 2) -> str:
    """
    주식 수량 포맷팅

    Args:
        value: 수량
        decimals: 소수점 자릿수

    Returns:
        포맷팅된 문자열 (예: '1.23주')
    """
    return f"{value:.{decimals}f}주"


def format_compact_number(value: float) -> str:
    """
    숫자 간략 표시 (K, M, B 단위)

    Args:
        value: 숫자

    Returns:
        간략 표시 (예: 1.2M, 500K)
    """
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}B"
    elif value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    elif value >= 1_000:
        return f"{value / 1_000:.1f}K"
    else:
        return f"{value:.0f}"


def format_year_month(year_month: str, format_str: str = '%Y년 %m월') -> str:
    """
    year_month 문자열 포맷팅

    Args:
        year_month: 'YYYY-MM' 형식
        format_str: strftime 포맷

    Returns:
        포맷팅된 문자열 (예: '2025년 12월')
    """
    try:
        dt = datetime.strptime(year_month, '%Y-%m')
        return dt.strftime(format_str)
    except:
        return year_month


def get_previous_month(year_month: str) -> str:
    """
    이전 달 year_month 반환

    Args:
        year_month: 'YYYY-MM'

    Returns:
        이전 달 'YYYY-MM' (예: '2025-12' -> '2025-11')
    """
    try:
        dt = datetime.strptime(year_month, '%Y-%m')
        # 해당 월의 1일로 이동
        first_day = dt.replace(day=1)
        # 1일 전으로 이동 (이전 달의 마지막 날)
        prev_month_last_day = first_day - timedelta(days=1)
        # 이전 달의 1일로
        prev_month_first_day = prev_month_last_day.replace(day=1)
        return prev_month_first_day.strftime('%Y-%m')
    except:
        return year_month


def get_next_month(year_month: str) -> str:
    """
    다음 달 year_month 반환

    Args:
        year_month: 'YYYY-MM'

    Returns:
        다음 달 'YYYY-MM'
    """
    try:
        dt = datetime.strptime(year_month, '%Y-%m')
        # 해당 월의 마지막 날 계산
        last_day = monthrange(dt.year, dt.month)[1]
        last_day_dt = dt.replace(day=last_day)
        # 1일 후 (다음 달 첫째 날)
        next_month = last_day_dt + timedelta(days=1)
        return next_month.strftime('%Y-%m')
    except:
        return year_month
