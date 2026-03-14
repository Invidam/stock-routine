"""
공통 포트폴리오 데이터 조회 레이어

CLI(matplotlib)와 Web(streamlit/plotly) 양쪽에서 사용하는
데이터 조회 로직을 한 곳에서 관리합니다.
"""
import sqlite3
from typing import Dict, List, Optional, Tuple
import pandas as pd
from core.interest_calculator import calc_cash_current_value

DEFAULT_EXCHANGE_RATE = 1450


# ---------------------------------------------------------------------------
# 기본 조회
# ---------------------------------------------------------------------------

def get_month_id(year_month: str, db_path: str) -> Optional[int]:
    """year_month로 month_id 조회"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM months WHERE year_month = ?", (year_month,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


def get_available_months(db_path: str) -> List[str]:
    """사용 가능한 월 목록 (내림차순)"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT year_month FROM months ORDER BY year_month DESC")
    months = [row[0] for row in cursor.fetchall()]
    conn.close()
    return months


def get_latest_month(db_path: str) -> Optional[str]:
    """최신 월 반환"""
    months = get_available_months(db_path)
    return months[0] if months else None


# ---------------------------------------------------------------------------
# CASH 이자 계산 (공통)
# ---------------------------------------------------------------------------

def calc_cash_value(db_path: str, month_id: Optional[int] = None,
                    up_to_month: Optional[str] = None) -> Tuple[int, float]:
    """
    CASH 자산의 투자원금 합계와 이자 반영 평가액 계산

    Args:
        db_path: DB 경로
        month_id: 특정 월 ID로 필터 (accounts.month_id 기준)
        up_to_month: 해당 월까지 누적 (year_month <= 기준)

    Returns:
        (cash_invested, cash_current_value)
    """
    conn = sqlite3.connect(db_path)

    if month_id is not None:
        records = pd.read_sql_query("""
            SELECT ph.input_amount, ph.purchase_date, ph.interest_rate, ph.interest_type
            FROM purchase_history ph
            JOIN accounts a ON ph.account_id = a.id
            WHERE a.month_id = ? AND ph.asset_type = 'CASH'
        """, conn, params=(month_id,))
    elif up_to_month is not None:
        records = pd.read_sql_query("""
            SELECT input_amount, purchase_date, interest_rate, interest_type
            FROM purchase_history
            WHERE asset_type = 'CASH' AND year_month <= ?
        """, conn, params=(up_to_month,))
    else:
        records = pd.read_sql_query("""
            SELECT input_amount, purchase_date, interest_rate, interest_type
            FROM purchase_history
            WHERE asset_type = 'CASH'
        """, conn)

    conn.close()

    if records.empty:
        return 0, 0.0

    total_invested = int(records['input_amount'].sum())
    total_value = 0.0
    for _, rec in records.iterrows():
        rate = rec['interest_rate'] if pd.notna(rec['interest_rate']) else None
        itype = rec['interest_type'] if pd.notna(rec['interest_type']) else 'simple'
        total_value += calc_cash_current_value(
            principal=int(rec['input_amount']),
            annual_rate=rate,
            purchase_date=rec['purchase_date'],
            interest_type=itype,
        )

    return total_invested, total_value


# ---------------------------------------------------------------------------
# 자산 배분 (analyzed_holdings 기반)
# ---------------------------------------------------------------------------

def get_asset_allocation(month_id: int, db_path: str) -> dict:
    """
    자산유형별 배분 (analyzed_holdings 기반)

    Returns:
        {'total': int, 'by_type': {'STOCK': int, 'BOND': int, 'CASH': int}}
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT asset_type, SUM(my_amount) as total_amount
        FROM analyzed_holdings
        WHERE month_id = ? AND account_id IS NULL
        GROUP BY asset_type
    """, (month_id,))

    results = cursor.fetchall()
    conn.close()

    data = {}
    total = 0
    for asset_type, amount in results:
        data[asset_type] = amount
        total += amount

    return {'total': total, 'by_type': data}


# ---------------------------------------------------------------------------
# 섹터 분포
# ---------------------------------------------------------------------------

def get_sector_distribution(month_id: int, db_path: str, limit: int = 10) -> pd.DataFrame:
    """
    섹터별 비중 (상위 N개)

    Returns:
        DataFrame: [sector_name, asset_type, amount]
    """
    conn = sqlite3.connect(db_path)

    df = pd.read_sql_query("""
        SELECT sector_name, asset_type, SUM(my_amount) as amount
        FROM analyzed_sectors
        WHERE month_id = ? AND account_id IS NULL
        GROUP BY sector_name, asset_type
        ORDER BY amount DESC
        LIMIT ?
    """, conn, params=(month_id, limit))

    conn.close()
    return df


# ---------------------------------------------------------------------------
# 상위 보유종목
# ---------------------------------------------------------------------------

def get_top_holdings(month_id: int, db_path: str, limit: int = 50) -> pd.DataFrame:
    """
    상위 보유종목 (OTHER 제외)

    Returns:
        DataFrame: [display_name, stock_name, stock_symbol, asset_type, source_tickers, amount]
    """
    conn = sqlite3.connect(db_path)

    df = pd.read_sql_query("""
        SELECT
            CASE
                WHEN asset_type IN ('STOCK', 'BOND') THEN stock_symbol
                ELSE stock_name
            END as display_name,
            MAX(stock_name) as stock_name,
            stock_symbol,
            asset_type,
            GROUP_CONCAT(DISTINCT source_ticker) as source_tickers,
            SUM(my_amount) as amount
        FROM analyzed_holdings
        WHERE month_id = ? AND account_id IS NULL
        GROUP BY
            CASE
                WHEN asset_type IN ('STOCK', 'BOND') THEN stock_symbol
                ELSE stock_name
            END,
            asset_type
        ORDER BY
            CASE WHEN stock_symbol = 'OTHER' THEN 1 ELSE 0 END,
            amount DESC
        LIMIT ?
    """, conn, params=(month_id, limit))

    conn.close()

    # OTHER 제외
    df = df[df['stock_symbol'] != 'OTHER']

    return df


# ---------------------------------------------------------------------------
# 누적 자산 (purchase_history 기반, 실시간 시세)
# ---------------------------------------------------------------------------

def get_cumulative_value(up_to_month: str, db_path: str) -> dict:
    """
    해당 월까지의 누적 자산 계산 (purchase_history + 실시간 시세)

    Returns:
        {
            'total_invested': int,
            'total_current': int,
            'profit': int,
            'return_rate': float,
            'total': int,
            'by_type': {
                'STOCK': {'invested': int, 'current': int, 'profit': int, 'percentage': float},
                ...
            }
        }
    """
    import yfinance as yf

    conn = sqlite3.connect(db_path)

    # purchase_history에서 투자금액 및 수량 누적 (CASH 제외)
    holdings_df = pd.read_sql_query("""
        SELECT
            ticker, asset_type,
            SUM(quantity) as total_quantity,
            SUM(input_amount) as invested,
            AVG(exchange_rate) as avg_exchange_rate
        FROM purchase_history
        WHERE year_month <= ?
        GROUP BY ticker, asset_type
    """, conn, params=(up_to_month,))

    conn.close()

    # CASH 이자 반영
    cash_invested, cash_value = calc_cash_value(db_path, up_to_month=up_to_month)

    if cash_invested > 0:
        cash_row = pd.DataFrame([{
            'ticker': 'CASH',
            'asset_type': 'CASH',
            'total_quantity': 0.0,
            'invested': cash_invested,
            'avg_exchange_rate': None,
        }])
        holdings_df = pd.concat([holdings_df, cash_row], ignore_index=True)

    if holdings_df.empty:
        return {
            'total_invested': 0, 'total_current': 0,
            'profit': 0, 'return_rate': 0, 'total': 0, 'by_type': {}
        }

    # 환율 조회
    try:
        exchange_rate = yf.Ticker("KRW=X").fast_info['last_price']
    except:
        exchange_rate = DEFAULT_EXCHANGE_RATE

    # 각 ticker별 현재가 조회
    holdings_df['current_value'] = 0.0

    for idx, row in holdings_df.iterrows():
        ticker = row['ticker']
        quantity = row['total_quantity']
        asset_type = row['asset_type']
        invested = row['invested']

        if asset_type == 'CASH' or ticker == 'CASH':
            holdings_df.at[idx, 'current_value'] = cash_value if cash_value > 0 else invested
        else:
            try:
                stock = yf.Ticker(ticker)
                current_price = stock.fast_info['last_price']

                is_korean = ticker.endswith(('.KS', '.KQ'))
                if is_korean:
                    current_value = quantity * current_price
                else:
                    current_value = quantity * current_price * exchange_rate

                holdings_df.at[idx, 'current_value'] = current_value

            except Exception as e:
                print(f"⚠️  {ticker} 현재가 조회 실패, 투자금액 사용: {e}")
                holdings_df.at[idx, 'current_value'] = invested

    # asset_type별 집계
    by_type_df = holdings_df.groupby('asset_type').agg({
        'invested': 'sum',
        'current_value': 'sum'
    }).reset_index()

    result = {'by_type': {}}
    total_invested = by_type_df['invested'].sum()
    total_current = by_type_df['current_value'].sum()

    for _, row in by_type_df.iterrows():
        asset_type = row['asset_type']
        invested = row['invested']
        current = row['current_value']

        result['by_type'][asset_type] = {
            'invested': invested,
            'current': current,
            'profit': current - invested,
            'percentage': (current / total_current * 100) if total_current > 0 else 0
        }

    result['total_invested'] = total_invested
    result['total_current'] = total_current
    result['profit'] = total_current - total_invested
    result['return_rate'] = ((total_current - total_invested) / total_invested * 100) if total_invested > 0 else 0
    result['total'] = total_current

    return result


# ---------------------------------------------------------------------------
# 자산 추이
# ---------------------------------------------------------------------------

def get_asset_trend(db_path: str, months: int = 12) -> pd.DataFrame:
    """
    월별 투자원금/평가금액 추이

    Returns:
        DataFrame: [year_month, invested, current_value]
    """
    conn = sqlite3.connect(db_path)

    # 투자원금 추이
    invested_df = pd.read_sql_query("""
        SELECT
            year_month,
            SUM(input_amount) as monthly_invested
        FROM purchase_history
        GROUP BY year_month
        ORDER BY year_month
    """, conn)

    # 분석된 평가금액 추이
    current_df = pd.read_sql_query("""
        SELECT
            m.year_month,
            SUM(ah.my_amount) as current_value
        FROM analyzed_holdings ah
        JOIN months m ON ah.month_id = m.id
        WHERE ah.account_id IS NULL
        GROUP BY m.year_month
        ORDER BY m.year_month
    """, conn)

    conn.close()

    if invested_df.empty:
        return pd.DataFrame(columns=['year_month', 'invested', 'current_value'])

    # 누적 투자원금 계산
    invested_df['invested'] = invested_df['monthly_invested'].cumsum()

    # 병합
    result = pd.merge(
        invested_df[['year_month', 'invested']],
        current_df,
        on='year_month',
        how='left'
    )

    # 최근 N개월만
    if len(result) > months:
        result = result.tail(months)

    return result
