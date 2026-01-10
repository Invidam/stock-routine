"""
데이터 로딩 및 캐싱 모듈
"""
import sqlite3
from typing import List, Dict, Optional, Tuple
import pandas as pd
import streamlit as st
from streamlit_app.config import CACHE_TTL, DB_PATH
from streamlit_app.utils.formatters import get_previous_month


# ===== 기본 데이터 조회 =====

@st.cache_data(ttl=CACHE_TTL['static_data'])
def get_available_months(db_path: str = DB_PATH) -> List[str]:
    """
    사용 가능한 월 목록 조회 (내림차순)

    Returns:
        ['2025-12', '2025-11', ...]
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT year_month
        FROM months
        ORDER BY year_month DESC
    """)

    months = [row[0] for row in cursor.fetchall()]
    conn.close()

    return months


@st.cache_data(ttl=CACHE_TTL['static_data'])
def get_latest_month(db_path: str = DB_PATH) -> Optional[str]:
    """최신 월 반환"""
    months = get_available_months(db_path)
    return months[0] if months else None


def get_month_id(year_month: str, db_path: str = DB_PATH) -> Optional[int]:
    """year_month로 month_id 조회"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id FROM months WHERE year_month = ?
    """, (year_month,))

    result = cursor.fetchone()
    conn.close()

    return result[0] if result else None


# ===== 월별 요약 데이터 =====

def _calculate_portfolio_value(purchase_data: List[Tuple], cash_amount: float) -> Tuple[int, int]:
    """
    포트폴리오 평가액 계산 (공통 로직)

    Args:
        purchase_data: [(ticker, quantity, invested), ...]
        cash_amount: CASH 자산 금액
ㅌㅌ
    Returns:
        (total_invested, total_value)
    """
    from streamlit_app.utils.price_fetcher import get_multiple_prices, get_current_price

    # 1. 현재가 조회
    tickers = [row[0] for row in purchase_data]
    current_prices = get_multiple_prices(tickers) if tickers else {}

    # 환율 조회
    exchange_rate = get_current_price('KRW=X')
    if not exchange_rate or exchange_rate <= 0:
        exchange_rate = 1400  # 기본 환율

    # 2. 평가액 계산
    total_value = 0
    total_invested = 0

    for ticker, quantity, invested in purchase_data:
        total_invested += invested

        current_price_usd = current_prices.get(ticker, 0)

        if current_price_usd and current_price_usd > 0:
            # 한국 주식은 이미 KRW, 미국 주식은 USD → KRW 환산
            if ticker.endswith('.KS') or ticker.endswith('.KQ'):
                current_price_krw = current_price_usd
            else:
                current_price_krw = current_price_usd * exchange_rate

            value = quantity * current_price_krw
            total_value += value
        else:
            # 현재가 조회 실패 시 원금 사용 (fallback)
            total_value += invested

    # 3. CASH 추가
    total_value += cash_amount
    total_invested += cash_amount

    return int(total_invested), int(total_value)


@st.cache_data(ttl=CACHE_TTL['monthly_data'])
def get_monthly_summary(year_month: str, db_path: str = DB_PATH) -> Dict:
    """
    월별 요약 데이터 반환 (실시간 평가액)

    Returns:
        {
            'total_value': int,      # 총 자산 (실시간 평가액)
            'total_invested': int,   # 총 원금
            'total_profit': int,     # 총 수익
            'return_rate': float     # 수익률 (%)
        }
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # "전체 기간"인 경우
    if year_month == "전체 기간":
        # 모든 월의 데이터를 합산
        all_months = get_available_months(db_path)

        total_invested_sum = 0
        total_value_sum = 0

        for month in all_months:
            month_id = get_month_id(month, db_path)
            if not month_id:
                continue

            # STOCK/BOND: purchase_history에서 수량 조회
            cursor.execute("""
                SELECT
                    ph.ticker,
                    SUM(ph.quantity) as total_quantity,
                    SUM(ph.input_amount) as invested
                FROM purchase_history ph
                JOIN accounts a ON ph.account_id = a.id
                WHERE a.month_id = ? AND ph.asset_type IN ('STOCK', 'BOND')
                GROUP BY ph.ticker
            """, (month_id,))
            purchase_data = cursor.fetchall()

            # CASH: holdings에서 조회
            cursor.execute("""
                SELECT SUM(h.amount) as cash_amount
                FROM holdings h
                JOIN accounts a ON h.account_id = a.id
                WHERE a.month_id = ? AND h.asset_type = 'CASH'
            """, (month_id,))
            result = cursor.fetchone()
            cash_amount = result[0] if result and result[0] else 0

            # 월별 평가액 계산
            month_invested, month_value = _calculate_portfolio_value(purchase_data, cash_amount)

            total_invested_sum += month_invested
            total_value_sum += month_value

        conn.close()

        total_invested = total_invested_sum
        total_value = total_value_sum

    else:
        # 특정 월인 경우
        month_id = get_month_id(year_month, db_path)
        if not month_id:
            conn.close()
            return {
                'total_value': 0,
                'total_invested': 0,
                'total_profit': 0,
                'return_rate': 0.0
            }

        # STOCK/BOND: purchase_history에서 수량 조회
        cursor.execute("""
            SELECT
                ph.ticker,
                SUM(ph.quantity) as total_quantity,
                SUM(ph.input_amount) as invested
            FROM purchase_history ph
            JOIN accounts a ON ph.account_id = a.id
            WHERE a.month_id = ? AND ph.asset_type IN ('STOCK', 'BOND')
            GROUP BY ph.ticker
        """, (month_id,))
        purchase_data = cursor.fetchall()

        # CASH: holdings에서 조회
        cursor.execute("""
            SELECT SUM(h.amount) as cash_amount
            FROM holdings h
            JOIN accounts a ON h.account_id = a.id
            WHERE a.month_id = ? AND h.asset_type = 'CASH'
        """, (month_id,))
        result = cursor.fetchone()
        cash_amount = result[0] if result and result[0] else 0

        conn.close()

        # 평가액 계산
        total_invested, total_value = _calculate_portfolio_value(purchase_data, cash_amount)

    # 수익 및 수익률 계산
    total_profit = total_value - total_invested
    return_rate = (total_profit / total_invested * 100) if total_invested > 0 else 0.0

    return {
        'total_value': total_value,
        'total_invested': total_invested,
        'total_profit': total_profit,
        'return_rate': round(return_rate, 1)
    }


@st.cache_data(ttl=CACHE_TTL['monthly_data'])
def get_recent_months_data(current_month: str, num_months: int = 3, db_path: str = DB_PATH) -> pd.DataFrame:
    """
    최근 N개월 데이터를 테이블로 반환

    Returns:
        DataFrame with columns: ['월', '총 자산', '총 원금', '총 수익', '수익률']
    """
    all_months = get_available_months(db_path)

    # 현재 월부터 역순으로 N개월
    try:
        current_idx = all_months.index(current_month)
        selected_months = all_months[current_idx:current_idx + num_months]
    except ValueError:
        selected_months = all_months[:num_months]

    data = []
    for month in selected_months:
        summary = get_monthly_summary(month, db_path)
        data.append({
            '월': month,
            '총 자산': summary['total_value'],
            '총 원금': summary['total_invested'],
            '총 수익': summary['total_profit'],
            '수익률': summary['return_rate']
        })

    return pd.DataFrame(data)


# ===== 자산 유형별 데이터 =====

@st.cache_data(ttl=CACHE_TTL['monthly_data'])
def get_asset_type_summary(year_month: str, db_path: str = DB_PATH) -> Dict[str, int]:
    """
    자산 유형별 요약

    Returns:
        {'STOCK': int, 'BOND': int, 'CASH': int}
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # "전체 기간"인 경우 purchase_history에서 합산
    if year_month == "전체 기간":
        cursor.execute("""
            SELECT asset_type, SUM(input_amount) as total_amount
            FROM purchase_history
            GROUP BY asset_type
        """)
    else:
        month_id = get_month_id(year_month, db_path)
        if not month_id:
            conn.close()
            return {'STOCK': 0, 'BOND': 0, 'CASH': 0}

        cursor.execute("""
            SELECT asset_type, SUM(my_amount) as total_amount
            FROM analyzed_holdings
            WHERE month_id = ? AND account_id IS NULL
            GROUP BY asset_type
        """, (month_id,))

    results = cursor.fetchall()
    conn.close()

    summary = {'STOCK': 0, 'BOND': 0, 'CASH': 0}
    for asset_type, amount in results:
        if asset_type in summary:
            summary[asset_type] = int(amount)

    return summary


# ===== 계좌 데이터 =====

@st.cache_data(ttl=CACHE_TTL['monthly_data'])
def get_accounts(year_month: str, db_path: str = DB_PATH) -> List[Dict]:
    """
    해당 월의 모든 계좌 조회 (실시간 평가액)

    Returns:
        [
            {
                'id': int,
                'name': str,
                'type': str,
                'broker': str,
                'fee': float,
                'total_value': int  # 실시간 평가액
            },
            ...
        ]
    """
    from streamlit_app.utils.price_fetcher import get_multiple_prices, get_current_price

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # "전체 기간"인 경우
    if year_month == "전체 기간":
        cursor.execute("""
            SELECT
                MAX(a.id) as id,
                a.name,
                MAX(a.type) as type,
                MAX(a.broker) as broker,
                MAX(a.fee) as fee
            FROM accounts a
            GROUP BY a.name
            ORDER BY a.name
        """)
    else:
        month_id = get_month_id(year_month, db_path)
        if not month_id:
            conn.close()
            return []

        cursor.execute("""
            SELECT
                a.id,
                a.name,
                a.type,
                a.broker,
                a.fee
            FROM accounts a
            WHERE a.month_id = ?
            ORDER BY a.id
        """, (month_id,))

    accounts_basic = cursor.fetchall()

    # 환율 조회
    exchange_rate = get_current_price('KRW=X')
    if not exchange_rate or exchange_rate <= 0:
        exchange_rate = 1400

    accounts = []
    for row in accounts_basic:
        account_id = row[0]
        account_name = row[1]

        # 실시간 평가액 계산
        if year_month == "전체 기간":
            # 전체 기간: 계좌명으로 매칭
            cursor.execute("""
                SELECT
                    ph.ticker,
                    SUM(ph.quantity) as total_quantity,
                    SUM(ph.input_amount) as invested,
                    ph.asset_type
                FROM purchase_history ph
                JOIN accounts a ON ph.account_id = a.id
                WHERE a.name = ?
                GROUP BY ph.ticker, ph.asset_type
            """, (account_name,))
        else:
            # 특정 월: account_id로 매칭
            cursor.execute("""
                SELECT
                    ph.ticker,
                    SUM(ph.quantity) as total_quantity,
                    SUM(ph.input_amount) as invested,
                    ph.asset_type
                FROM purchase_history ph
                WHERE ph.account_id = ? AND ph.asset_type IN ('STOCK', 'BOND')
                GROUP BY ph.ticker, ph.asset_type
            """, (account_id,))

        purchase_data = cursor.fetchall()

        # CASH 조회
        if year_month == "전체 기간":
            # 전체 기간: 최신 월 holdings에서 CASH 조회
            latest_month = get_latest_month(db_path)
            latest_month_id = get_month_id(latest_month, db_path) if latest_month else None
            if latest_month_id:
                cursor.execute("""
                    SELECT SUM(h.amount)
                    FROM holdings h
                    JOIN accounts a ON h.account_id = a.id
                    WHERE a.name = ? AND a.month_id = ? AND h.asset_type = 'CASH'
                """, (account_name, latest_month_id))
            else:
                cash_amount = 0
        else:
            cursor.execute("""
                SELECT SUM(h.amount)
                FROM holdings h
                WHERE h.account_id = ? AND h.asset_type = 'CASH'
            """, (account_id,))

        result = cursor.fetchone()
        cash_amount = result[0] if result and result[0] else 0

        # 현재가 조회
        tickers = [row[0] for row in purchase_data]
        current_prices = get_multiple_prices(tickers) if tickers else {}

        # 평가액 계산
        total_value = 0
        for ticker, quantity, invested, asset_type in purchase_data:
            current_price_usd = current_prices.get(ticker, 0)

            if current_price_usd and current_price_usd > 0:
                # 한국 주식은 이미 KRW
                if ticker.endswith('.KS') or ticker.endswith('.KQ'):
                    current_price_krw = current_price_usd
                else:
                    current_price_krw = current_price_usd * exchange_rate

                value = quantity * current_price_krw
                total_value += value
            else:
                # 현재가 조회 실패 시 원금 사용
                total_value += invested

        # CASH 추가
        total_value += cash_amount

        accounts.append({
            'id': account_id,
            'name': account_name,
            'type': row[2],
            'broker': row[3],
            'fee': row[4],
            'total_value': int(total_value)
        })

    conn.close()
    return accounts


@st.cache_data(ttl=CACHE_TTL['monthly_data'])
def get_account_holdings(year_month: str, account_id: int, db_path: str = DB_PATH) -> pd.DataFrame:
    """
    계좌별 보유 종목 조회 (실시간 평가액)

    Returns:
        DataFrame with columns:
        - 종목명, 티커, 자산유형
        - 보유수량, 평균매입가
        - 투자원금, 현재가, 평가금액
        - 수익금액, 수익률(%), ratio
    """
    from streamlit_app.utils.price_fetcher import get_multiple_prices, get_current_price

    conn = sqlite3.connect(db_path)

    # "전체 기간"인 경우
    if year_month == "전체 기간":
        # purchase_history에서 조회
        query_ph = """
            SELECT
                ph.ticker as 티커,
                ph.ticker as 종목명,
                ph.asset_type as 자산유형,
                SUM(ph.quantity) as 보유수량,
                SUM(ph.input_amount) as 투자원금,
                CASE
                    WHEN ph.ticker = 'OTHER' THEN 1
                    ELSE 0
                END as is_other
            FROM purchase_history ph
            JOIN accounts a ON ph.account_id = a.id
            WHERE a.name = (SELECT name FROM accounts WHERE id = ?) AND ph.asset_type IN ('STOCK', 'BOND')
            GROUP BY ph.ticker, ph.asset_type
        """
        df = pd.read_sql_query(query_ph, conn, params=(account_id,))

        # CASH 추가 (최신 월 holdings에서)
        latest_month = get_latest_month(db_path)
        latest_month_id = get_month_id(latest_month, db_path) if latest_month else None
        if latest_month_id:
            query_cash = """
                SELECT
                    h.name as 종목명,
                    h.ticker_mapping as 티커,
                    h.asset_type as 자산유형,
                    0.0 as 보유수량,
                    h.amount as 투자원금,
                    0 as is_other
                FROM holdings h
                JOIN accounts a ON h.account_id = a.id
                WHERE a.name = (SELECT name FROM accounts WHERE id = ?)
                  AND a.month_id = ?
                  AND h.asset_type = 'CASH'
            """
            df_cash = pd.read_sql_query(query_cash, conn, params=(account_id, latest_month_id))
            df = pd.concat([df, df_cash], ignore_index=True)
    else:
        # 특정 월: holdings + purchase_history 병합
        month_id = get_month_id(year_month, db_path)
        if not month_id:
            conn.close()
            return pd.DataFrame()

        # STOCK/BOND: purchase_history에서 수량 조회
        query_ph = """
            SELECT
                h.name as 종목명,
                h.ticker_mapping as 티커,
                h.asset_type as 자산유형,
                COALESCE(SUM(ph.quantity), 0) as 보유수량,
                h.amount as 투자원금,
                CASE
                    WHEN h.ticker_mapping = 'OTHER' THEN 1
                    ELSE 0
                END as is_other
            FROM holdings h
            LEFT JOIN purchase_history ph ON h.account_id = ph.account_id
                AND h.ticker_mapping = ph.ticker
                AND h.asset_type = ph.asset_type
            WHERE h.account_id = ? AND h.asset_type IN ('STOCK', 'BOND')
            GROUP BY h.id, h.name, h.ticker_mapping, h.asset_type, h.amount
        """
        df_stock_bond = pd.read_sql_query(query_ph, conn, params=(account_id,))

        # CASH: holdings에서만 조회
        query_cash = """
            SELECT
                h.name as 종목명,
                h.ticker_mapping as 티커,
                h.asset_type as 자산유형,
                0.0 as 보유수량,
                h.amount as 투자원금,
                CASE
                    WHEN h.ticker_mapping = 'OTHER' THEN 1
                    ELSE 0
                END as is_other
            FROM holdings h
            WHERE h.account_id = ? AND h.asset_type = 'CASH'
        """
        df_cash = pd.read_sql_query(query_cash, conn, params=(account_id,))

        df = pd.concat([df_stock_bond, df_cash], ignore_index=True)

    conn.close()

    # 타입 변환
    df['보유수량'] = pd.to_numeric(df['보유수량'], errors='coerce').fillna(0)
    df['투자원금'] = pd.to_numeric(df['투자원금'], errors='coerce').fillna(0)

    # 현재가 조회
    stock_bond_df = df[df['자산유형'].isin(['STOCK', 'BOND'])]
    tickers = stock_bond_df['티커'].unique().tolist()
    current_prices = get_multiple_prices(tickers) if tickers else {}

    # 환율 조회
    exchange_rate = get_current_price('KRW=X')
    if not exchange_rate or exchange_rate <= 0:
        exchange_rate = 1400

    # 평균매입가 계산
    df['평균매입가'] = df.apply(
        lambda row: round(row['투자원금'] / row['보유수량']) if row['보유수량'] > 0 else 0,
        axis=1
    )

    # 현재가 계산 (원화)
    def get_current_price_krw(row):
        if row['자산유형'] == 'CASH':
            return row['투자원금']  # CASH는 그대로
        ticker = row['티커']
        price_usd = current_prices.get(ticker, 0)
        if price_usd and price_usd > 0:
            if ticker.endswith('.KS') or ticker.endswith('.KQ'):
                return price_usd
            else:
                return price_usd * exchange_rate
        return 0

    df['현재가'] = df.apply(get_current_price_krw, axis=1)

    # 평가금액 계산
    df['평가금액'] = df.apply(
        lambda row: round(row['보유수량'] * row['현재가']) if row['자산유형'] in ['STOCK', 'BOND'] and row['현재가'] > 0
                    else row['투자원금'],  # CASH 또는 현재가 없는 경우 원금
        axis=1
    )

    # 수익금액, 수익률 계산
    df['수익금액'] = df['평가금액'] - df['투자원금']
    df['수익률(%)'] = df.apply(
        lambda row: round((row['수익금액'] / row['투자원금']) * 100, 2) if row['투자원금'] > 0 else 0,
        axis=1
    )

    # 계좌 내 비중 계산 (평가금액 기준)
    total_value = df['평가금액'].sum()
    if total_value > 0:
        df['ratio'] = (df['평가금액'] / total_value * 100).round(1)
    else:
        df['ratio'] = 0.0

    # 정렬 (OTHER 제외, 평가금액 내림차순)
    df = df.sort_values(['is_other', '평가금액'], ascending=[True, False]).reset_index(drop=True)

    # is_other 컬럼 제거
    df = df.drop('is_other', axis=1)

    # 컬럼 순서 정리 (하위 호환성 위해 amount 추가)
    df['amount'] = df['평가금액']  # 기존 코드 호환용

    return df


@st.cache_data(ttl=CACHE_TTL['monthly_data'])
def get_account_sectors(year_month: str, account_id: int, db_path: str = DB_PATH) -> pd.DataFrame:
    """
    계좌별 섹터 비중 조회

    Returns:
        DataFrame with columns: ['sector_name', 'amount', 'percent']
    """
    # "전체 기간"인 경우 최신 월 데이터 사용 (ETF 구성은 최신 월 기준)
    if year_month == "전체 기간":
        year_month = get_latest_month(db_path)
        if not year_month:
            return pd.DataFrame()

    month_id = get_month_id(year_month, db_path)
    if not month_id:
        return pd.DataFrame()

    conn = sqlite3.connect(db_path)

    query = """
        SELECT
            sector_name,
            SUM(my_amount) as amount,
            SUM(sector_percent) as percent
        FROM analyzed_sectors
        WHERE month_id = ? AND account_id = ?
        GROUP BY sector_name
        ORDER BY amount DESC
    """

    df = pd.read_sql_query(query, conn, params=(month_id, account_id))
    conn.close()

    return df


@st.cache_data(ttl=CACHE_TTL['etf_data'])
def get_etf_lookthrough(year_month: str, account_id: int, top_n: int = 10, db_path: str = DB_PATH) -> pd.DataFrame:
    """
    ETF 투시 데이터 조회 (Top N만)

    Returns:
        DataFrame with columns: ['종목', 'holding_percent', 'my_amount', '출처 ETF']
    """
    # "전체 기간"인 경우 최신 월 데이터 사용 (ETF 구성은 최신 월 기준)
    if year_month == "전체 기간":
        year_month = get_latest_month(db_path)
        if not year_month:
            return pd.DataFrame()

    month_id = get_month_id(year_month, db_path)
    if not month_id:
        return pd.DataFrame()

    conn = sqlite3.connect(db_path)

    query = """
        SELECT
            CASE
                WHEN stock_symbol LIKE '%.KS' THEN stock_name || ' (' || stock_symbol || ')'
                ELSE stock_symbol
            END as 종목,
            stock_symbol,
            holding_percent,
            my_amount,
            source_ticker as '출처 ETF',
            CASE
                WHEN stock_symbol = 'OTHER' THEN 1
                ELSE 0
            END as is_other
        FROM analyzed_holdings
        WHERE month_id = ? AND account_id = ? AND asset_type = 'STOCK'
        ORDER BY is_other ASC, my_amount DESC
        LIMIT ?
    """

    df = pd.read_sql_query(query, conn, params=(month_id, account_id, top_n))
    conn.close()

    # 계좌 내 비중 재계산
    total_amount = df['my_amount'].sum()
    if total_amount > 0:
        df['ratio'] = (df['my_amount'] / total_amount * 100).round(1)
    else:
        df['ratio'] = df['holding_percent']

    # 불필요한 컬럼 제거
    df = df.drop(['is_other', 'stock_symbol'], axis=1)

    return df


# ===== 전체 포트폴리오 데이터 =====

@st.cache_data(ttl=CACHE_TTL['monthly_data'])
def get_total_sectors(year_month: str, top_n: int = 10, db_path: str = DB_PATH) -> pd.DataFrame:
    """
    통합 섹터 비중 (Top N)

    Returns:
        DataFrame with columns: ['sector_name', 'amount', 'percent']
    """
    # "전체 기간"인 경우 최신 월 데이터 사용
    if year_month == "전체 기간":
        year_month = get_latest_month(db_path)
        if not year_month:
            return pd.DataFrame()

    month_id = get_month_id(year_month, db_path)
    if not month_id:
        return pd.DataFrame()

    conn = sqlite3.connect(db_path)

    query = """
        SELECT
            sector_name,
            SUM(my_amount) as amount,
            SUM(my_amount) * 100.0 / (
                SELECT SUM(my_amount)
                FROM analyzed_holdings
                WHERE month_id = ? AND account_id IS NULL
            ) as percent
        FROM analyzed_sectors
        WHERE month_id = ? AND account_id IS NULL
        GROUP BY sector_name
        ORDER BY amount DESC
        LIMIT ?
    """
    df = pd.read_sql_query(query, conn, params=(month_id, month_id, top_n))

    conn.close()
    return df


@st.cache_data(ttl=CACHE_TTL['monthly_data'])
def get_total_top_holdings(year_month: str, top_n: int = 20, db_path: str = DB_PATH) -> pd.DataFrame:
    """
    통합 보유 종목 Top N

    Returns:
        DataFrame with columns: ['종목', '유형', 'amount', 'percent', '출처']
    """
    conn = sqlite3.connect(db_path)

    # "전체 기간"인 경우 purchase_history에서 직접 매수 종목만 조회
    # (ETF 내부 종목은 시간에 따라 변하므로 전체 기간에서는 의미 없음)
    if year_month == "전체 기간":
        query = """
            SELECT
                ticker as 종목,
                asset_type as 유형,
                SUM(input_amount) as amount,
                SUM(input_amount) * 100.0 / (
                    SELECT SUM(input_amount)
                    FROM purchase_history
                ) as percent,
                '직접매수' as 출처
            FROM purchase_history
            GROUP BY ticker, asset_type
            ORDER BY amount DESC
            LIMIT ?
        """
        df = pd.read_sql_query(query, conn, params=(top_n,))
    else:
        month_id = get_month_id(year_month, db_path)
        if not month_id:
            conn.close()
            return pd.DataFrame()

        query = """
            SELECT
                CASE
                    WHEN stock_name IS NOT NULL AND stock_name != '' THEN stock_name
                    ELSE stock_symbol
                END as 종목,
                asset_type as 유형,
                SUM(my_amount) as amount,
                SUM(my_amount) * 100.0 / (
                    SELECT SUM(my_amount)
                    FROM analyzed_holdings
                    WHERE month_id = ? AND account_id IS NULL
                ) as percent,
                GROUP_CONCAT(DISTINCT source_ticker) as 출처
            FROM analyzed_holdings
            WHERE month_id = ? AND account_id IS NULL
            GROUP BY
                CASE
                    WHEN stock_name IS NOT NULL AND stock_name != '' THEN stock_name
                    ELSE stock_symbol
                END,
                asset_type
            ORDER BY
                CASE WHEN stock_symbol = 'OTHER' THEN 1 ELSE 0 END,
                amount DESC
            LIMIT ?
        """
        df = pd.read_sql_query(query, conn, params=(month_id, month_id, top_n))

        # OTHER 제외
        df = df[df['종목'] != 'OTHER']

    conn.close()
    return df


@st.cache_data(ttl=CACHE_TTL['monthly_data'])
def get_hierarchical_portfolio_data(year_month: str, db_path: str = DB_PATH) -> pd.DataFrame:
    """
    Sunburst 차트용 계층 데이터

    Returns:
        DataFrame with columns: ['labels', 'parents', 'values', 'colors']
    """
    # 계층 구조: ROOT > 자산유형(STOCK/BOND/CASH) > 섹터 > 종목

    data = []

    # 1. ROOT
    asset_summary = get_asset_type_summary(year_month, db_path)
    total_value = sum(asset_summary.values())

    data.append({
        'labels': 'ROOT',
        'parents': '',
        'values': total_value,
        'colors': '#ffffff'
    })

    # 2. 자산 유형별
    color_map = {'STOCK': '#3498db', 'BOND': '#2ecc71', 'CASH': '#f39c12'}

    for asset_type, amount in asset_summary.items():
        if amount > 0:
            data.append({
                'labels': asset_type,
                'parents': 'ROOT',
                'values': amount,
                'colors': color_map.get(asset_type, '#95a5a6')
            })

    # 3. 섹터별 (STOCK/BOND만)
    # "전체 기간"인 경우 최신 월 데이터 사용 (이미 get_asset_type_summary에서 처리됨)
    effective_month = year_month if year_month != "전체 기간" else get_latest_month(db_path)
    if not effective_month:
        return pd.DataFrame(columns=['labels', 'parents', 'values', 'colors'])

    month_id = get_month_id(effective_month, db_path)
    if not month_id:
        return pd.DataFrame(columns=['labels', 'parents', 'values', 'colors'])

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            sector_name,
            asset_type,
            SUM(my_amount) as amount
        FROM analyzed_sectors
        WHERE month_id = ? AND account_id IS NULL
        GROUP BY sector_name, asset_type
        ORDER BY amount DESC
        LIMIT 15
    """, (month_id,))

    for sector_name, asset_type, amount in cursor.fetchall():
        if asset_type in ['STOCK', 'BOND']:
            # 색상: 자산 유형별로 밝기 조정
            base_color = color_map.get(asset_type, '#95a5a6')
            data.append({
                'labels': sector_name,
                'parents': asset_type,
                'values': int(amount),
                'colors': base_color
            })

    conn.close()

    return pd.DataFrame(data)


@st.cache_data(ttl=CACHE_TTL['monthly_data'])
def search_total_holdings(year_month: str, ticker: str, db_path: str = DB_PATH) -> Optional[Dict]:
    """
    종목 검색 (직접 + ETF 통합)

    Returns:
        {
            'ticker': str,
            'name': str,
            'direct_shares': float,
            'direct_value': int,
            'etf_shares': float,
            'etf_value': int,
            'etf_details': List[Tuple],
            'total_shares': float,
            'total_value': int
        }
    """
    # "전체 기간"인 경우 최신 월 데이터 사용
    if year_month == "전체 기간":
        year_month = get_latest_month(db_path)
        if not year_month:
            return None

    month_id = get_month_id(year_month, db_path)
    if not month_id:
        return None

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 직접 보유 확인
    cursor.execute("""
        SELECT SUM(amount) as direct_value
        FROM holdings
        WHERE ticker_mapping = ? AND account_id IN (
            SELECT id FROM accounts WHERE month_id = ?
        )
    """, (ticker, month_id))
    result = cursor.fetchone()
    direct_value = int(result[0]) if result and result[0] else 0

    # ETF 통해 보유 확인
    cursor.execute("""
        SELECT
            source_ticker,
            SUM(my_amount) as etf_value
        FROM analyzed_holdings
        WHERE stock_symbol = ? AND month_id = ? AND account_id IS NULL
        GROUP BY source_ticker
    """, (ticker, month_id))

    etf_details = []
    etf_value_total = 0
    for source_ticker, etf_value in cursor.fetchall():
        etf_value = int(etf_value)
        etf_details.append((source_ticker, 0.0, etf_value))  # 수량은 계산 안 함
        etf_value_total += etf_value

    conn.close()

    # 결과가 없으면 None 반환
    if direct_value == 0 and etf_value_total == 0:
        return None

    return {
        'ticker': ticker,
        'name': ticker,  # 실제로는 종목명 조회 필요
        'direct_shares': 0.0,  # 수량 계산 생략
        'direct_value': direct_value,
        'etf_shares': 0.0,  # 수량 계산 생략
        'etf_value': etf_value_total,
        'etf_details': etf_details,
        'total_shares': 0.0,
        'total_value': direct_value + etf_value_total
    }


@st.cache_data(ttl=CACHE_TTL['monthly_data'])
def get_monthly_holdings_comparison(year_month: str, db_path: str = DB_PATH) -> pd.DataFrame:
    """
    월별 계좌+종목별 투자 내역 비교 (실시간 수익률 포함)

    Args:
        year_month: 기준 월 (YYYY-MM)

    Returns:
        DataFrame with columns:
        - 계좌명, 종목명, 티커
        - 현재투자금액, 전월투자금액, 증감액, 증감률(%)
        - 보유수량, 평균매입가, 현재가
        - 평가금액, 수익금액, 수익률(%)
    """
    from streamlit_app.utils.formatters import get_previous_month
    from streamlit_app.utils.price_fetcher import get_multiple_prices, get_current_price

    month_id = get_month_id(year_month, db_path)
    if not month_id:
        return pd.DataFrame()

    prev_month = get_previous_month(year_month)
    prev_month_id = get_month_id(prev_month, db_path)

    conn = sqlite3.connect(db_path)

    # 현재 월 데이터
    query_current = """
        SELECT
            a.name as 계좌명,
            h.name as 종목명,
            h.ticker_mapping as 티커,
            h.amount as 현재투자금액,
            a.id as account_id,
            h.name as holding_name
        FROM holdings h
        JOIN accounts a ON h.account_id = a.id
        WHERE a.month_id = ?
        ORDER BY a.name, h.amount DESC
    """

    df_current = pd.read_sql_query(query_current, conn, params=(month_id,))

    # 전월 데이터
    if prev_month_id:
        query_prev = """
            SELECT
                a.name as 계좌명,
                h.name as 종목명,
                h.amount as 전월투자금액
            FROM holdings h
            JOIN accounts a ON h.account_id = a.id
            WHERE a.month_id = ?
        """
        df_prev = pd.read_sql_query(query_prev, conn, params=(prev_month_id,))
    else:
        df_prev = pd.DataFrame(columns=['계좌명', '종목명', '전월투자금액'])

    # 계좌별 종목별 매수 정보 (수량, 투자금액)
    query_purchases = """
        SELECT
            account_id,
            ticker,
            SUM(quantity) as 보유수량,
            SUM(input_amount) as 총투자금액
        FROM purchase_history
        GROUP BY account_id, ticker
    """
    df_purchases = pd.read_sql_query(query_purchases, conn)

    conn.close()

    # 현재월과 전월 데이터 병합
    df = pd.merge(
        df_current,
        df_prev,
        on=['계좌명', '종목명'],
        how='left'
    )

    # 매수 정보 병합
    df = pd.merge(
        df,
        df_purchases,
        left_on=['account_id', '티커'],
        right_on=['account_id', 'ticker'],
        how='left'
    )

    # 전월투자금액이 없으면 0으로 설정
    df['전월투자금액'] = df['전월투자금액'].fillna(0)
    df['보유수량'] = df['보유수량'].fillna(0)

    # 증감액 계산
    df['증감액'] = df['현재투자금액'] - df['전월투자금액']

    # 증감률 계산 (전월 금액이 0이면 None)
    df['증감률(%)'] = df.apply(
        lambda row: round((row['증감액'] / row['전월투자금액']) * 100, 2) if row['전월투자금액'] > 0 else None,
        axis=1
    )

    # 실시간 가격 조회
    unique_tickers = df['티커'].unique().tolist()
    current_prices = get_multiple_prices(unique_tickers)

    # 환율 조회 (USD/KRW)
    exchange_rate = get_current_price('KRW=X')  # USD to KRW
    if not exchange_rate or exchange_rate <= 0:
        exchange_rate = 1400  # 기본 환율 (조회 실패 시)

    # 각 행에 현재가 매핑
    df['현재가(USD)'] = df['티커'].map(current_prices)

    # 평균 매입가 계산 (원화)
    df['평균매입가'] = df.apply(
        lambda row: round(row['총투자금액'] / row['보유수량']) if row['보유수량'] > 0 else 0,
        axis=1
    )

    # 현재가 (원화)
    df['현재가'] = df.apply(
        lambda row: round(row['현재가(USD)'] * exchange_rate) if pd.notna(row['현재가(USD)']) and row['현재가(USD)'] > 0 else 0,
        axis=1
    )

    # 평가금액 (원화)
    df['평가금액'] = df.apply(
        lambda row: round(row['보유수량'] * row['현재가']) if row['현재가'] > 0 else 0,
        axis=1
    )

    # 수익금액
    df['수익금액'] = df['평가금액'] - df['총투자금액'].fillna(0)

    # 수익률
    df['수익률(%)'] = df.apply(
        lambda row: round((row['수익금액'] / row['총투자금액']) * 100, 2) if row['총투자금액'] > 0 and row['평가금액'] > 0 else 0,
        axis=1
    )

    # 필요한 컬럼만 선택
    result = df[[
        '계좌명', '종목명', '티커',
        '현재투자금액', '전월투자금액', '증감액', '증감률(%)',
        '보유수량', '평균매입가', '현재가',
        '평가금액', '수익금액', '수익률(%)'
    ]].copy()

    return result
