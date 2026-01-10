"""
실시간 가격 조회 유틸리티
"""
import yfinance as yf
import pandas as pd
from typing import Dict, Optional
import streamlit as st


@st.cache_data(ttl=300)  # 5분 캐싱
def get_current_price(ticker: str) -> Optional[float]:
    """
    yfinance를 통해 현재 가격 조회

    Args:
        ticker: 티커 심볼 (예: 'AAPL', '005930.KS')

    Returns:
        현재가 (없으면 None)
    """
    if not ticker or ticker.upper() == 'OTHER':
        return None

    try:
        stock = yf.Ticker(ticker)
        # fast_info 또는 info에서 현재가 가져오기
        try:
            current_price = stock.fast_info.get('last_price')
            if current_price and current_price > 0:
                return float(current_price)
        except:
            pass

        # fast_info가 없으면 info 사용
        info = stock.info

        # 현재가 필드 여러 개 시도
        for price_field in ['regularMarketPrice', 'currentPrice', 'previousClose', 'price']:
            if price_field in info and info[price_field]:
                price = info[price_field]
                if price and price > 0:
                    return float(price)

        return None
    except Exception as e:
        # 조용히 실패 (로그는 남기지 않음)
        return None


@st.cache_data(ttl=300)  # 5분 캐싱
def get_multiple_prices(tickers: list) -> Dict[str, Optional[float]]:
    """
    여러 티커의 현재 가격을 일괄 조회

    Args:
        tickers: 티커 심볼 리스트

    Returns:
        {ticker: price} 딕셔너리
    """
    prices = {}

    # 유효한 티커만 필터링
    valid_tickers = [t for t in tickers if t and t.upper() != 'OTHER']

    if not valid_tickers:
        return prices

    try:
        # yfinance download 사용 (더 빠름)
        data = yf.download(
            tickers=valid_tickers,
            period='1d',
            interval='1d',
            progress=False,
            show_errors=False
        )

        if len(valid_tickers) == 1:
            # 단일 티커인 경우
            if not data.empty and 'Close' in data.columns:
                prices[valid_tickers[0]] = float(data['Close'].iloc[-1])
        else:
            # 여러 티커인 경우
            if not data.empty and 'Close' in data.columns:
                close_data = data['Close']
                for ticker in valid_tickers:
                    try:
                        if ticker in close_data.columns:
                            price = close_data[ticker].iloc[-1]
                            if pd.notna(price) and price > 0:
                                prices[ticker] = float(price)
                    except:
                        pass
    except Exception as e:
        # 일괄 조회 실패 시 개별 조회로 폴백
        for ticker in valid_tickers:
            price = get_current_price(ticker)
            if price:
                prices[ticker] = price

    return prices


def calculate_profit_rate(invested_amount: float, current_value: float) -> float:
    """
    수익률 계산

    Args:
        invested_amount: 투자 금액
        current_value: 현재 가치

    Returns:
        수익률 (%)
    """
    if invested_amount <= 0:
        return 0.0

    return ((current_value - invested_amount) / invested_amount) * 100