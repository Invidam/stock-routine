"""
테스트 공통 픽스처
인메모리 SQLite DB와 yfinance mock을 제공
"""
import sqlite3
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def db_path(tmp_path):
    """임시 DB 파일 경로"""
    return str(tmp_path / "test_portfolio.db")


@pytest.fixture
def initialized_db(db_path):
    """초기화된 빈 DB"""
    from data.init_db import init_database
    init_database(db_path)
    return db_path


@pytest.fixture
def populated_db(initialized_db):
    """
    테스트 데이터가 들어간 DB
    - 2개 월 (2025-01, 2025-02)
    - 2개 계좌 (ISA, 연금저축)
    - 미국 주식(SPY, QQQ), 한국 주식(069500.KS), CASH
    """
    db_path = initialized_db
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # months
    cursor.execute("INSERT INTO months (year_month) VALUES ('2025-01')")
    month1_id = cursor.lastrowid
    cursor.execute("INSERT INTO months (year_month) VALUES ('2025-02')")
    month2_id = cursor.lastrowid

    # accounts - month 1
    cursor.execute(
        "INSERT INTO accounts (month_id, name, type, broker, fee) VALUES (?, 'ISA', '중개형ISA', '한투', 0.0)",
        (month1_id,))
    acc1_m1 = cursor.lastrowid
    cursor.execute(
        "INSERT INTO accounts (month_id, name, type, broker, fee) VALUES (?, '연금저축', '연금저축', '한투', 0.0)",
        (month1_id,))
    acc2_m1 = cursor.lastrowid

    # accounts - month 2
    cursor.execute(
        "INSERT INTO accounts (month_id, name, type, broker, fee) VALUES (?, 'ISA', '중개형ISA', '한투', 0.0)",
        (month2_id,))
    acc1_m2 = cursor.lastrowid
    cursor.execute(
        "INSERT INTO accounts (month_id, name, type, broker, fee) VALUES (?, '연금저축', '연금저축', '한투', 0.0)",
        (month2_id,))
    acc2_m2 = cursor.lastrowid

    # holdings (CASH 포함)
    cursor.execute(
        "INSERT INTO holdings (account_id, name, ticker_mapping, amount, target_ratio, asset_type) "
        "VALUES (?, 'SPY', 'SPY', 300000, 50.0, 'STOCK')", (acc1_m1,))
    cursor.execute(
        "INSERT INTO holdings (account_id, name, ticker_mapping, amount, target_ratio, asset_type) "
        "VALUES (?, 'QQQ', 'QQQ', 200000, 30.0, 'STOCK')", (acc1_m1,))
    cursor.execute(
        "INSERT INTO holdings (account_id, name, ticker_mapping, amount, target_ratio, asset_type) "
        "VALUES (?, 'CMA', 'CMA', 100000, 20.0, 'CASH')", (acc1_m1,))

    cursor.execute(
        "INSERT INTO holdings (account_id, name, ticker_mapping, amount, target_ratio, asset_type) "
        "VALUES (?, 'KODEX200', '069500.KS', 500000, 100.0, 'STOCK')", (acc2_m1,))

    # holdings - month 2
    cursor.execute(
        "INSERT INTO holdings (account_id, name, ticker_mapping, amount, target_ratio, asset_type) "
        "VALUES (?, 'SPY', 'SPY', 350000, 50.0, 'STOCK')", (acc1_m2,))
    cursor.execute(
        "INSERT INTO holdings (account_id, name, ticker_mapping, amount, target_ratio, asset_type) "
        "VALUES (?, 'QQQ', 'QQQ', 250000, 30.0, 'STOCK')", (acc1_m2,))
    cursor.execute(
        "INSERT INTO holdings (account_id, name, ticker_mapping, amount, target_ratio, asset_type) "
        "VALUES (?, 'CMA', 'CMA', 150000, 20.0, 'CASH')", (acc1_m2,))

    # purchase_history - month 1
    # SPY: 300,000원, 주당 590 USD, 환율 1400 → 주당 826,000원 → 0.3632주
    cursor.execute("""
        INSERT INTO purchase_history
        (ticker, asset_type, year_month, purchase_date, quantity, input_amount,
         price_at_purchase, currency, exchange_rate, account_id)
        VALUES ('SPY', 'STOCK', '2025-01', '2025-01-26', 0.3632, 300000,
                826000.0, 'USD', 1400.0, ?)
    """, (acc1_m1,))

    # QQQ: 200,000원, 주당 500 USD, 환율 1400 → 주당 700,000원 → 0.2857주
    cursor.execute("""
        INSERT INTO purchase_history
        (ticker, asset_type, year_month, purchase_date, quantity, input_amount,
         price_at_purchase, currency, exchange_rate, account_id)
        VALUES ('QQQ', 'STOCK', '2025-01', '2025-01-26', 0.2857, 200000,
                700000.0, 'USD', 1400.0, ?)
    """, (acc1_m1,))

    # KODEX200: 500,000원, 주당 35,000원 → 14.2857주
    cursor.execute("""
        INSERT INTO purchase_history
        (ticker, asset_type, year_month, purchase_date, quantity, input_amount,
         price_at_purchase, currency, exchange_rate, account_id)
        VALUES ('069500.KS', 'STOCK', '2025-01', '2025-01-26', 14.2857, 500000,
                35000.0, 'KRW', NULL, ?)
    """, (acc2_m1,))

    # purchase_history - month 2
    # SPY 추가 매수: 350,000원, 주당 600 USD, 환율 1420 → 주당 852,000원 → 0.4108주
    cursor.execute("""
        INSERT INTO purchase_history
        (ticker, asset_type, year_month, purchase_date, quantity, input_amount,
         price_at_purchase, currency, exchange_rate, account_id)
        VALUES ('SPY', 'STOCK', '2025-02', '2025-02-26', 0.4108, 350000,
                852000.0, 'USD', 1420.0, ?)
    """, (acc1_m2,))

    # QQQ 추가 매수: 250,000원
    cursor.execute("""
        INSERT INTO purchase_history
        (ticker, asset_type, year_month, purchase_date, quantity, input_amount,
         price_at_purchase, currency, exchange_rate, account_id)
        VALUES ('QQQ', 'STOCK', '2025-02', '2025-02-26', 0.3472, 250000,
                720000.0, 'USD', 1420.0, ?)
    """, (acc1_m2,))

    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def mock_yfinance():
    """yfinance를 mock하여 외부 API 호출 없이 테스트"""
    with patch('yfinance.Ticker') as mock_ticker_cls:
        def create_ticker(symbol):
            mock = MagicMock()
            prices = {
                'SPY': {'currentPrice': 610.0, 'regularMarketPrice': 610.0},
                'QQQ': {'currentPrice': 520.0, 'regularMarketPrice': 520.0},
                '069500.KS': {'currentPrice': 36000.0, 'regularMarketPrice': 36000.0},
                'KRW=X': {'regularMarketPrice': 1430.0, 'currentPrice': 1430.0},
            }
            mock.info = prices.get(symbol, {})
            mock.fast_info = MagicMock()
            fast_prices = {
                'SPY': 610.0,
                'QQQ': 520.0,
                '069500.KS': 36000.0,
                'KRW=X': 1430.0,
            }
            mock.fast_info.get = lambda key, default=None: fast_prices.get(symbol, default) if key == 'last_price' else default
            return mock

        mock_ticker_cls.side_effect = create_ticker
        yield mock_ticker_cls


@pytest.fixture
def mock_yf_download():
    """yfinance.download를 mock"""
    import pandas as pd
    import numpy as np
    from datetime import datetime

    with patch('yfinance.download') as mock_dl:
        def fake_download(tickers, **kwargs):
            prices = {
                'SPY': 610.0,
                'QQQ': 520.0,
                '069500.KS': 36000.0,
            }
            if isinstance(tickers, str):
                tickers = [tickers]

            if len(tickers) == 1:
                ticker = tickers[0]
                price = prices.get(ticker, 0)
                return pd.DataFrame(
                    {'Close': [price]},
                    index=[datetime(2025, 3, 14)]
                )
            else:
                data = {}
                for t in tickers:
                    data[t] = prices.get(t, 0)
                df = pd.DataFrame(
                    {'Close': data},
                    index=[datetime(2025, 3, 14)]
                )
                return df

        mock_dl.side_effect = fake_download
        yield mock_dl