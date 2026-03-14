"""
포트폴리오 분석 스크립트
DB에 저장된 ETF 보유 내역을 분석하여 실제 보유 종목과 섹터 비중 계산
"""
import sqlite3
import time
import yfinance as yf
import pandas as pd
from typing import Dict, List, Optional, Tuple


# ===== 0. 티커 매핑 및 환율 조회 =====

# 티커 매핑 딕셔너리 (한국 티커 → 미국 ETF)
TICKER_MAPPING = {
    'KOSPI': 'EWY',  # 코스피 → iShares MSCI South Korea ETF
    # 필요시 추가 가능
}


def map_ticker(ticker: str) -> str:
    """
    티커 매핑 적용 (KOSPI → EWY 등)

    Args:
        ticker: 원본 티커

    Returns:
        매핑된 티커 (매핑 없으면 원본 반환)
    """
    mapped = TICKER_MAPPING.get(ticker, ticker)
    if mapped != ticker:
        print(f"   🔄 티커 매핑: {ticker} → {mapped}")
    return mapped


def get_exchange_rate() -> float:
    """
    yfinance를 사용하여 USD/KRW 환율 조회

    Returns:
        환율 (1달러당 원화)
    """
    try:
        ticker = yf.Ticker("KRW=X")
        current_rate = ticker.fast_info['last_price']
        return current_rate
    except Exception as e:
        print(f"⚠️  환율 조회 실패: {e}, 기본값 1,450원 사용")
        return 1450.0  # 기본값


def save_exchange_rate(year_month: str, exchange_rate: float, db_path: str):
    """
    months 테이블에 환율 정보 저장

    Args:
        year_month: 'YYYY-MM'
        exchange_rate: 환율
        db_path: DB 경로
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE months SET exchange_rate = ? WHERE year_month = ?",
        (exchange_rate, year_month)
    )

    conn.commit()
    conn.close()


def get_saved_exchange_rate(year_month: str, db_path: str) -> Optional[float]:
    """
    DB에 저장된 환율 조회

    Args:
        year_month: 'YYYY-MM'
        db_path: DB 경로

    Returns:
        환율 또는 None
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT exchange_rate FROM months WHERE year_month = ?",
        (year_month,)
    )
    result = cursor.fetchone()
    conn.close()

    return result[0] if result and result[0] else None


# ===== 1. DB 조회 레이어 =====

def get_month_id(year_month: str, db_path: str) -> Optional[int]:
    """
    year_month에 해당하는 month_id 조회

    Args:
        year_month: 'YYYY-MM' 형식의 년-월
        db_path: DB 파일 경로

    Returns:
        month_id 또는 None
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id FROM months WHERE year_month = ?",
        (year_month,)
    )
    result = cursor.fetchone()
    conn.close()

    return result[0] if result else None


def get_etf_holdings(year_month: str, db_path: str, exclude_tickers: List[str] = None) -> List[Dict]:
    """
    특정 월의 ETF 보유 정보 조회 (티커별 합산, 제외 티커 필터링)

    Args:
        year_month: 'YYYY-MM' 형식
        db_path: DB 파일 경로
        exclude_tickers: 제외할 티커 리스트 (예: ['CASH'])

    Returns:
        [
            {
                'ticker': 'SPY',
                'name': 'ACE 미국 S&P 500',
                'total_amount': 420000,  # 여러 계좌 합산
                'asset_type': 'STOCK'
            },
            ...
        ]
    """
    if exclude_tickers is None:
        exclude_tickers = []

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 티커별 합산 쿼리
    placeholders = ','.join('?' * len(exclude_tickers))
    exclude_clause = f"AND h.ticker_mapping NOT IN ({placeholders})" if exclude_tickers else ""

    query = f"""
        SELECT
            h.ticker_mapping as ticker,
            h.name as name,
            h.asset_type as asset_type,
            SUM(h.amount) as total_amount
        FROM holdings h
        INNER JOIN accounts a ON h.account_id = a.id
        INNER JOIN months m ON a.month_id = m.id
        WHERE m.year_month = ?
        {exclude_clause}
        GROUP BY h.ticker_mapping, h.name, h.asset_type
        ORDER BY total_amount DESC
    """

    cursor.execute(query, (year_month, *exclude_tickers))
    results = cursor.fetchall()

    conn.close()

    # Dict로 변환
    etf_list = []
    for row in results:
        etf_list.append({
            'ticker': row['ticker'],
            'name': row['name'],
            'total_amount': row['total_amount'],
            'asset_type': row['asset_type']
        })

    return etf_list


def get_account_etf_holdings(year_month: str, db_path: str, exclude_tickers: List[str] = None) -> List[Dict]:
    """
    특정 월의 계좌별 ETF 보유 정보 조회

    Args:
        year_month: 'YYYY-MM' 형식
        db_path: DB 파일 경로
        exclude_tickers: 제외할 티커 리스트

    Returns:
        [
            {
                'account_id': 1,
                'account_name': '투자 (절세)',
                'ticker': 'SPY',
                'name': 'ACE 미국 S&P 500',
                'amount': 300000,
                'asset_type': 'STOCK'
            },
            ...
        ]
    """
    if exclude_tickers is None:
        exclude_tickers = []

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    placeholders = ','.join('?' * len(exclude_tickers))
    exclude_clause = f"AND h.ticker_mapping NOT IN ({placeholders})" if exclude_tickers else ""

    query = f"""
        SELECT
            a.id as account_id,
            a.name as account_name,
            h.ticker_mapping as ticker,
            h.name as holding_name,
            h.asset_type as asset_type,
            SUM(h.amount) as amount
        FROM holdings h
        INNER JOIN accounts a ON h.account_id = a.id
        INNER JOIN months m ON a.month_id = m.id
        WHERE m.year_month = ?
        {exclude_clause}
        GROUP BY a.id, a.name, h.ticker_mapping, h.name, h.asset_type
        ORDER BY a.id, amount DESC
    """

    cursor.execute(query, (year_month, *exclude_tickers))
    results = cursor.fetchall()

    conn.close()

    # Dict로 변환
    account_etf_list = []
    for row in results:
        account_etf_list.append({
            'account_id': row['account_id'],
            'account_name': row['account_name'],
            'ticker': row['ticker'],
            'name': row['holding_name'],
            'amount': row['amount'],
            'asset_type': row['asset_type']
        })

    return account_etf_list


# ===== 2. yfinance 데이터 수집 레이어 =====

def fetch_etf_holdings(ticker: str, retry: int = 3) -> Optional[pd.DataFrame]:
    """
    yfinance를 사용하여 ETF의 top holdings 가져오기 (main.py 참고)

    Args:
        ticker: ETF 티커 (예: 'SPY')
        retry: 재시도 횟수

    Returns:
        DataFrame with columns: ['Symbol', 'Name', 'Holding Percent']
        또는 실패 시 None
    """
    for attempt in range(retry):
        try:
            etf = yf.Ticker(ticker)
            holdings_df = etf.funds_data.top_holdings

            if holdings_df is None or holdings_df.empty:
                print(f"⚠️  {ticker}: top_holdings 데이터 없음")
                return None

            return holdings_df

        except AttributeError:
            # funds_data 속성이 없는 경우
            print(f"⚠️  {ticker}: ETF 데이터를 지원하지 않음")
            return None

        except Exception as e:
            print(f"⚠️  {ticker} 시도 {attempt+1}/{retry} 실패: {e}")
            if attempt < retry - 1:
                time.sleep(2 ** attempt)  # exponential backoff
            else:
                return None

    return None


def fetch_etf_sectors(ticker: str, retry: int = 3) -> Optional[Dict[str, float]]:
    """
    yfinance를 사용하여 ETF의 sector weightings 가져오기 (main.py 참고)

    Args:
        ticker: ETF 티커
        retry: 재시도 횟수

    Returns:
        {'Technology': 0.28, 'Healthcare': 0.15, ...}
        또는 실패 시 None
    """
    for attempt in range(retry):
        try:
            etf = yf.Ticker(ticker)
            sector_data = etf.funds_data.sector_weightings

            if sector_data is None or len(sector_data) == 0:
                print(f"⚠️  {ticker}: sector_weightings 데이터 없음")
                return None

            return sector_data

        except AttributeError:
            print(f"⚠️  {ticker}: ETF 데이터를 지원하지 않음")
            return None

        except Exception as e:
            print(f"⚠️  {ticker} 시도 {attempt+1}/{retry} 실패: {e}")
            if attempt < retry - 1:
                time.sleep(2 ** attempt)
            else:
                return None

    return None


# ===== 3. 분석 및 계산 레이어 =====

def calculate_my_holdings(
    etf_ticker: str,
    my_investment: int,
    holdings_df: pd.DataFrame
) -> List[Dict]:
    """
    ETF의 holdings를 내 투자금액 기준으로 계산 (main.py:44 참고)

    Args:
        etf_ticker: 'SPY'
        my_investment: 420000 (원)
        holdings_df: ETF 구성 종목 DataFrame

    Returns:
        [
            {
                'source_ticker': 'SPY',
                'stock_symbol': 'AAPL',
                'stock_name': 'Apple Inc.',
                'holding_percent': 0.065,
                'my_amount': 27300
            },
            ...
        ]
    """
    result = []
    total_weight = 0.0

    for index, row in holdings_df.iterrows():
        stock_symbol = row.get('Symbol', index)  # Symbol 컬럼 또는 인덱스
        stock_name = row.get('Name', stock_symbol)
        weight_in_etf = row['Holding Percent']

        # 내 포트폴리오에서 이 종목이 차지하는 실제 금액
        my_stock_value = int(my_investment * weight_in_etf)

        result.append({
            'source_ticker': etf_ticker,
            'stock_symbol': stock_symbol,
            'stock_name': stock_name,
            'holding_percent': weight_in_etf,
            'my_amount': my_stock_value
        })

        total_weight += weight_in_etf

    # 누락된 holdings를 "기타 종목"으로 추가
    if total_weight < 1.0:
        remaining_weight = 1.0 - total_weight
        remaining_amount = int(my_investment * remaining_weight)

        result.append({
            'source_ticker': etf_ticker,
            'stock_symbol': 'OTHER',
            'stock_name': f'{etf_ticker} 기타 종목',
            'holding_percent': remaining_weight,
            'my_amount': remaining_amount
        })

    return result


def calculate_my_sectors(
    etf_ticker: str,
    my_investment: int,
    sectors: Dict[str, float]
) -> List[Dict]:
    """
    ETF의 섹터 비중을 내 투자금액 기준으로 계산 (main.py:59 참고)

    Args:
        etf_ticker: 'SPY'
        my_investment: 420000 (원)
        sectors: {'Technology': 0.28, ...}

    Returns:
        [
            {
                'source_ticker': 'SPY',
                'sector_name': 'Technology',
                'sector_percent': 0.28,
                'my_amount': 117600
            },
            ...
        ]
    """
    result = []
    total_weight = 0.0

    for sector_name, weight_in_etf in sectors.items():
        my_sector_value = int(my_investment * weight_in_etf)

        result.append({
            'source_ticker': etf_ticker,
            'sector_name': sector_name,
            'sector_percent': weight_in_etf,
            'my_amount': my_sector_value
        })

        total_weight += weight_in_etf

    # 누락된 섹터를 "기타"로 추가
    if total_weight < 1.0:
        remaining_weight = 1.0 - total_weight
        remaining_amount = int(my_investment * remaining_weight)

        result.append({
            'source_ticker': etf_ticker,
            'sector_name': 'other',
            'sector_percent': remaining_weight,
            'my_amount': remaining_amount
        })

    return result


# ===== 3.5 자산 유형별 분석 함수 =====

def analyze_stock_asset(
    ticker: str,
    name: str,
    amount: int,
    month_id: int,
    account_id: Optional[int],
    db_path: str
):
    """
    주식형 자산 분석 (ETF 또는 개별 주식)

    Args:
        ticker: 티커 심볼
        name: 보유 종목명
        amount: 투자 금액
        month_id: 월 ID
        account_id: 계좌 ID (None이면 전체)
        db_path: DB 경로
    """
    mapped_ticker = map_ticker(ticker)

    # ETF인지 개별 주식인지 확인
    try:
        stock = yf.Ticker(mapped_ticker)
        info = stock.info
        quote_type = info.get('quoteType', 'UNKNOWN')
    except Exception as e:
        print(f"⚠️  {mapped_ticker} 정보 조회 실패: {e}")
        quote_type = 'UNKNOWN'

    # 개별 주식인 경우
    if quote_type == 'EQUITY':
        print(f"   📌 개별 주식으로 처리")
        # Holdings: 자기 자신을 100% 보유
        holdings_data = [{
            'source_ticker': mapped_ticker,
            'stock_symbol': mapped_ticker,
            'stock_name': name,
            'holding_percent': 1.0,
            'my_amount': amount
        }]
        save_analyzed_holdings(month_id, account_id, holdings_data, db_path, asset_type='STOCK')

        # Sectors: info에서 sector 조회
        sector_name = info.get('sector', 'Unknown')
        if sector_name and sector_name != 'Unknown':
            sectors_data = [{
                'source_ticker': mapped_ticker,
                'sector_name': sector_name,
                'sector_percent': 1.0,
                'my_amount': amount
            }]
            save_analyzed_sectors(month_id, account_id, sectors_data, db_path, asset_type='STOCK')

        return

    # ETF인 경우 (기존 로직)
    # Holdings 조회
    holdings_df = fetch_etf_holdings(mapped_ticker)
    if holdings_df is not None and not holdings_df.empty:
        holdings_data = calculate_my_holdings(mapped_ticker, amount, holdings_df)
        save_analyzed_holdings(month_id, account_id, holdings_data, db_path, asset_type='STOCK')

    # Sectors 조회
    sectors = fetch_etf_sectors(mapped_ticker)
    if sectors is not None and len(sectors) > 0:
        sectors_data = calculate_my_sectors(mapped_ticker, amount, sectors)
        save_analyzed_sectors(month_id, account_id, sectors_data, db_path, asset_type='STOCK')


def analyze_bond_asset(
    ticker: str,
    name: str,
    amount: int,
    month_id: int,
    account_id: Optional[int],
    db_path: str
):
    """
    채권형 ETF 분석 (조회 시도, 실패 시 대체)

    Args:
        ticker: 티커 심볼
        name: 보유 종목명
        amount: 투자 금액
        month_id: 월 ID
        account_id: 계좌 ID (None이면 전체)
        db_path: DB 경로
    """
    mapped_ticker = map_ticker(ticker)

    # 1. Holdings 조회 시도
    holdings_df = fetch_etf_holdings(mapped_ticker)
    if holdings_df is not None and not holdings_df.empty:
        holdings_data = calculate_my_holdings(mapped_ticker, amount, holdings_df)
    else:
        # 실패: 채권 자체를 holding으로
        holdings_data = [{
            'source_ticker': mapped_ticker,
            'stock_symbol': mapped_ticker,
            'stock_name': name,
            'holding_percent': 1.0,
            'my_amount': amount
        }]
    save_analyzed_holdings(month_id, account_id, holdings_data, db_path, asset_type='BOND')

    # 2. Sectors 조회 시도
    sectors = fetch_etf_sectors(mapped_ticker)
    if sectors is not None and len(sectors) > 0:
        sectors_data = calculate_my_sectors(mapped_ticker, amount, sectors)
    else:
        # 실패: Fixed Income 섹터로
        sectors_data = [{
            'source_ticker': mapped_ticker,
            'sector_name': 'Fixed Income',
            'sector_percent': 1.0,
            'my_amount': amount
        }]
    save_analyzed_sectors(month_id, account_id, sectors_data, db_path, asset_type='BOND')


def analyze_cash_asset(
    ticker: str,
    name: str,
    amount: int,
    month_id: int,
    account_id: Optional[int],
    db_path: str
):
    """
    현금형 자산 분석 (yfinance 조회 없음)

    Args:
        ticker: 티커 심볼 (CASH)
        name: 보유 종목명 (예: "주택청약종합저축")
        amount: 투자 금액
        month_id: 월 ID
        account_id: 계좌 ID (None이면 전체)
        db_path: DB 경로
    """
    # Holdings: 현금 상품 자체
    holdings_data = [{
        'source_ticker': 'CASH',
        'stock_symbol': 'CASH',
        'stock_name': name,
        'holding_percent': 1.0,
        'my_amount': amount
    }]
    save_analyzed_holdings(month_id, account_id, holdings_data, db_path, asset_type='CASH')

    # Sectors: Cash & Equivalents
    sectors_data = [{
        'source_ticker': 'CASH',
        'sector_name': 'Cash & Equivalents',
        'sector_percent': 1.0,
        'my_amount': amount
    }]
    save_analyzed_sectors(month_id, account_id, sectors_data, db_path, asset_type='CASH')


# ===== 4. DB 저장 레이어 =====

def save_analyzed_holdings(
    month_id: int,
    account_id: Optional[int],
    holdings_data: List[Dict],
    db_path: str,
    asset_type: str = 'STOCK'
) -> int:
    """
    analyzed_holdings 테이블에 저장

    Args:
        month_id: 월 ID
        account_id: 계좌 ID (None이면 전체 분석)
        holdings_data: calculate_my_holdings 결과
        db_path: DB 경로
        asset_type: 자산 유형 ('STOCK', 'BOND', 'CASH')

    Returns:
        저장된 레코드 수
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    count = 0
    for holding in holdings_data:
        cursor.execute(
            """
            INSERT INTO analyzed_holdings
            (month_id, account_id, source_ticker, stock_symbol, stock_name,
             holding_percent, my_amount, asset_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                month_id,
                account_id,
                holding['source_ticker'],
                holding['stock_symbol'],
                holding['stock_name'],
                holding['holding_percent'],
                holding['my_amount'],
                asset_type
            )
        )
        count += 1

    conn.commit()
    conn.close()

    return count


def save_analyzed_sectors(
    month_id: int,
    account_id: Optional[int],
    sectors_data: List[Dict],
    db_path: str,
    asset_type: str = 'STOCK'
) -> int:
    """
    analyzed_sectors 테이블에 저장

    Args:
        month_id: 월 ID
        account_id: 계좌 ID (None이면 전체 분석)
        sectors_data: calculate_my_sectors 결과
        db_path: DB 경로
        asset_type: 자산 유형 ('STOCK', 'BOND', 'CASH')

    Returns:
        저장된 레코드 수
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    count = 0
    for sector in sectors_data:
        cursor.execute(
            """
            INSERT INTO analyzed_sectors
            (month_id, account_id, source_ticker, sector_name,
             sector_percent, my_amount, asset_type)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                month_id,
                account_id,
                sector['source_ticker'],
                sector['sector_name'],
                sector['sector_percent'],
                sector['my_amount'],
                asset_type
            )
        )
        count += 1

    conn.commit()
    conn.close()

    return count



# ===== 5. 집계 및 출력 레이어 =====

def aggregate_holdings(month_id: int, account_id: Optional[int], db_path: str) -> pd.DataFrame:
    """
    같은 종목은 합산하여 집계

    Args:
        month_id: 월 ID
        account_id: 계좌 ID (None이면 전체)
        db_path: DB 경로

    Returns:
        DataFrame with columns: ['stock_symbol', 'stock_name', 'total_amount', 'percentage']
    """
    conn = sqlite3.connect(db_path)

    if account_id is None:
        # 전체 집계
        query = """
            SELECT
                stock_symbol,
                stock_name,
                SUM(my_amount) as total_amount
            FROM analyzed_holdings
            WHERE month_id = ? AND account_id IS NULL
            GROUP BY stock_symbol, stock_name
            ORDER BY total_amount DESC
        """
        params = (month_id,)
    else:
        # 계좌별 집계
        query = """
            SELECT
                stock_symbol,
                stock_name,
                SUM(my_amount) as total_amount
            FROM analyzed_holdings
            WHERE month_id = ? AND account_id = ?
            GROUP BY stock_symbol, stock_name
            ORDER BY total_amount DESC
        """
        params = (month_id, account_id)

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    # 비율 계산
    if not df.empty:
        total = df['total_amount'].sum()
        df['percentage'] = df['total_amount'] / total * 100

    return df


def aggregate_sectors(month_id: int, account_id: Optional[int], db_path: str) -> pd.DataFrame:
    """
    같은 섹터는 합산하여 집계

    Args:
        month_id: 월 ID
        account_id: 계좌 ID (None이면 전체)
        db_path: DB 경로

    Returns:
        DataFrame with columns: ['sector_name', 'total_amount', 'percentage']
    """
    conn = sqlite3.connect(db_path)

    if account_id is None:
        query = """
            SELECT
                sector_name,
                SUM(my_amount) as total_amount
            FROM analyzed_sectors
            WHERE month_id = ? AND account_id IS NULL
            GROUP BY sector_name
            ORDER BY total_amount DESC
        """
        params = (month_id,)
    else:
        query = """
            SELECT
                sector_name,
                SUM(my_amount) as total_amount
            FROM analyzed_sectors
            WHERE month_id = ? AND account_id = ?
            GROUP BY sector_name
            ORDER BY total_amount DESC
        """
        params = (month_id, account_id)

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    # 비율 계산
    if not df.empty:
        total = df['total_amount'].sum()
        df['percentage'] = df['total_amount'] / total * 100

    return df


def print_analysis_summary(
    holdings_df: pd.DataFrame,
    sectors_df: pd.DataFrame,
    total_investment: int,
    title: str = "포트폴리오"
):
    """
    분석 결과를 콘솔에 출력 (main.py 스타일)

    Args:
        holdings_df: 종목별 집계 결과
        sectors_df: 섹터별 집계 결과
        total_investment: 총 투자금액
        title: 출력 제목
    """
    print("\n" + "=" * 80)
    print(f"🏆 [{title} - 실제 보유 상위 종목]")
    print("-" * 80)

    if not holdings_df.empty:
        for idx, row in holdings_df.iterrows():
            print(f"- {row['stock_name']:<30} ({row['stock_symbol']:<6}): {int(row['total_amount']):>10,}원 ({row['percentage']:>5.1f}%)")
    else:
        print("데이터 없음")

    print("\n" + "=" * 80)
    print(f"📊 [{title} - 섹터별 분산 현황]")
    print("-" * 80)

    if not sectors_df.empty:
        for idx, row in sectors_df.iterrows():
            print(f"- {row['sector_name']:<30}: {row['percentage']:>5.1f}%")
    else:
        print("데이터 없음")


# ===== 5.5. 통합 분석 출력 (Net Worth) =====

def calculate_net_worth(month_id: int, db_path: str) -> Dict:
    """자산 유형별 금액 및 비중"""
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

    by_type = {}
    total = 0

    for asset_type, amount in results:
        by_type[asset_type] = {'amount': amount}
        total += amount

    # 비중 계산
    for asset_type in by_type:
        by_type[asset_type]['percentage'] = (by_type[asset_type]['amount'] / total * 100) if total > 0 else 0

    return {
        'total': total,
        'by_type': by_type
    }


def calculate_integrated_sectors(month_id: int, db_path: str) -> pd.DataFrame:
    """전체 자산 대비 섹터 비중"""
    conn = sqlite3.connect(db_path)

    query = """
        SELECT sector_name, asset_type, SUM(my_amount) as amount
        FROM analyzed_sectors
        WHERE month_id = ? AND account_id IS NULL
        GROUP BY sector_name, asset_type
        ORDER BY amount DESC
    """

    df = pd.read_sql_query(query, conn, params=(month_id,))
    conn.close()

    if df.empty:
        return df

    total_amount = df['amount'].sum()
    type_totals = df.groupby('asset_type')['amount'].sum()

    df['percentage_in_total'] = df['amount'] / total_amount * 100
    df['percentage_in_type'] = df.apply(
        lambda row: row['amount'] / type_totals[row['asset_type']] * 100,
        axis=1
    )

    return df


def calculate_integrated_holdings(month_id: int, db_path: str, limit: int = 30) -> pd.DataFrame:
    """통합 보유 상위 항목

    - STOCK, BOND: ticker 기준으로 통합 (같은 종목/채권은 합침)
    - CASH: 개별 항목으로 유지 (적금 상품별로 분리)
    - stock_name도 함께 반환 (한국 주식 표시용)
    """
    conn = sqlite3.connect(db_path)

    query = """
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
            CASE WHEN stock_symbol = 'OTHER' THEN 1 ELSE 0 END,  -- OTHER을 마지막으로
            amount DESC
        LIMIT ?
    """

    df = pd.read_sql_query(query, conn, params=(month_id, limit))
    conn.close()

    if df.empty:
        return df

    total = df['amount'].sum()
    df['percentage'] = df['amount'] / total * 100

    return df


def print_integrated_analysis(month_id: int, db_path: str):
    """통합 포트폴리오 분석 결과 출력"""

    # 1. Net Worth
    net_worth = calculate_net_worth(month_id, db_path)

    print("\n" + "=" * 80)
    print("💰 [종합 자산 요약 - Net Worth]")
    print("-" * 80)
    print(f"- 총 자산: {net_worth['total']:,}원\n")

    type_labels = {
        'STOCK': '위험 자산 (주식형)',
        'BOND': '안전 자산 (채권형)',
        'CASH': '현금성 자산 (적금)'
    }

    for i, (asset_type, data) in enumerate(net_worth['by_type'].items(), 1):
        label = type_labels.get(asset_type, asset_type)
        print(f"{i}. {label:20}: {data['amount']:>12,}원 ({data['percentage']:>5.1f}%)")

    # 2. 통합 섹터 비중
    sectors_df = calculate_integrated_sectors(month_id, db_path)

    print("\n" + "=" * 80)
    print("📊 [전체 포트폴리오 - 통합 섹터 비중]")
    print("(* 주식 섹터 + 채권 + 현금성 자산을 모두 포함한 비중입니다)")
    print("-" * 80)

    type_icons = {
        'STOCK': '📈',
        'BOND': '📊',
        'CASH': '💵'
    }

    for idx, row in sectors_df.iterrows():
        icon = type_icons.get(row['asset_type'], '📌')
        print(f"{icon} {row['sector_name']:<30}: {row['percentage_in_total']:>5.1f}% "
              f"(자산내 {row['percentage_in_type']:>5.1f}%)")

    # 3. 통합 holdings TOP 50 (OTHER 제외) + 기타
    top_n = 50
    holdings_df_all = calculate_integrated_holdings(month_id, db_path, limit=999999)  # 전체 가져오기

    # OTHER을 분리
    other_row = holdings_df_all[holdings_df_all['stock_symbol'] == 'OTHER']
    holdings_df_without_other = holdings_df_all[holdings_df_all['stock_symbol'] != 'OTHER']
    holdings_df_top = holdings_df_without_other.head(top_n)

    print("\n" + "=" * 80)
    print(f"🏆 [통합 보유 상위 항목 (TOP {top_n})]")
    print("(* 개별 주식과 적금 상품이 금액 순으로 표시)")
    print("-" * 80)

    medals = ['🥇', '🥈', '🥉']
    type_labels_short = {
        'STOCK': '주식',
        'BOND': '채권',
        'CASH': '현금'
    }

    for idx, row in holdings_df_top.iterrows():
        medal = medals[idx] if idx < 3 else '  '
        type_label = type_labels_short.get(row['asset_type'], row['asset_type'])

        # 한국 주식(.KS)은 실제 이름 표시, 나머지는 ticker 표시
        if row['asset_type'] == 'STOCK' and row['stock_symbol'] and row['stock_symbol'].endswith('.KS'):
            display_text = f"{row['stock_name']:<30} ({row['stock_symbol']:<10})"
        else:
            display_text = f"{row['display_name']:<42}"

        # source_tickers 정보 추가
        source_info = f" [from: {row['source_tickers']}]" if pd.notna(row.get('source_tickers')) and ',' in str(row.get('source_tickers', '')) else ""

        print(f"{medal} [{type_label}] {display_text}: "
              f"{int(row['amount']):>12,}원 ({row['percentage']:>5.1f}%){source_info}")

    # OTHER 항목 표시 (ETF 내 상위 10개 외 나머지 종목)
    if not other_row.empty:
        print("\n" + "-" * 80)
        print("📦 [ETF 내 기타 종목 요약]")
        print("(* yfinance는 ETF 상위 10개 종목만 제공하므로, 나머지를 합산)")
        print("-" * 80)
        for idx, row in other_row.iterrows():
            sources = row['source_tickers'].split(',') if pd.notna(row.get('source_tickers')) else []
            print(f"   기타 종목 (상위 10개 외): {int(row['amount']):>12,}원 ({row['percentage']:>5.1f}%)")
            if sources:
                print(f"   출처 ETF: {', '.join(sources)}")

    # 표시되지 않은 소액 종목들 (TOP 50 밖)
    if len(holdings_df_without_other) > top_n:
        remaining_df = holdings_df_without_other.iloc[top_n:]
        remaining_total = remaining_df['amount'].sum()
        remaining_count = len(remaining_df)
        remaining_percentage = remaining_df['percentage'].sum()

        print(f"\n   [소액] TOP {top_n} 외 소액 종목 ({remaining_count}개): "
              f"{int(remaining_total):>12,}원 ({remaining_percentage:>5.1f}%)")


# ===== 6. 메인 오케스트레이션 =====

def analyze_month_portfolio(
    year_month: str,
    db_path: str = "portfolio.db",
    overwrite: bool = False,
    exclude_tickers: List[str] = None,
    analyze_by_account: bool = True,
    analyze_total: bool = True
):
    """
    특정 월의 포트폴리오를 분석하여 DB에 저장

    Args:
        year_month: 'YYYY-MM' 형식
        db_path: DB 경로
        overwrite: True면 기존 분석 데이터 삭제 후 재분석
        exclude_tickers: 분석에서 제외할 티커 목록 (기본값: [] - 모든 자산 분석)
        analyze_by_account: 계좌별 분석 수행 여부
        analyze_total: 전체 합산 분석 수행 여부
    """
    if exclude_tickers is None:
        exclude_tickers = []  # 모든 자산 유형 분석

    print(f"\n📂 {year_month}월 포트폴리오 분석 시작")
    print("=" * 80)

    # 1. 환율 조회 및 저장
    exchange_rate = get_exchange_rate()
    print(f"💱 환율: 1 USD = {exchange_rate:,.2f} KRW")

    # 1.5. month_id 조회
    month_id = get_month_id(year_month, db_path)
    if month_id is None:
        print(f"❌ {year_month} 데이터를 찾을 수 없습니다.")
        return

    # 환율 저장
    save_exchange_rate(year_month, exchange_rate, db_path)

    # 2. 기존 데이터 확인 및 삭제
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM analyzed_holdings WHERE month_id = ?", (month_id,))
    existing_count = cursor.fetchone()[0]

    if existing_count > 0:
        if overwrite:
            print(f"⚠️  기존 분석 데이터 {existing_count}건 삭제 중...")
            cursor.execute("DELETE FROM analyzed_holdings WHERE month_id = ?", (month_id,))
            cursor.execute("DELETE FROM analyzed_sectors WHERE month_id = ?", (month_id,))
            conn.commit()
        else:
            print(f"❌ 이미 분석된 데이터가 있습니다. --overwrite 옵션을 사용하세요.")
            conn.close()
            return

    conn.close()

    # 3. 계좌별 분석
    total_holdings_count = 0
    total_sectors_count = 0

    if analyze_by_account:
        print("\n🏦 계좌별 분석 수행 중...")
        account_etfs = get_account_etf_holdings(year_month, db_path, exclude_tickers)

        for etf_data in account_etfs:
            account_id = etf_data['account_id']
            account_name = etf_data['account_name']
            ticker = etf_data['ticker']
            name = etf_data['name']
            amount = etf_data['amount']
            asset_type = etf_data['asset_type']

            print(f"\n  📊 [{account_name}] [{asset_type}] {name} ({ticker}): {amount:,}원")

            try:
                # 자산 유형별 분석
                if asset_type == 'STOCK':
                    analyze_stock_asset(ticker, name, amount, month_id, account_id, db_path)
                elif asset_type == 'BOND':
                    analyze_bond_asset(ticker, name, amount, month_id, account_id, db_path)
                elif asset_type == 'CASH':
                    analyze_cash_asset(ticker, name, amount, month_id, account_id, db_path)

                print(f"     ✅ 분석 완료")
            except Exception as e:
                print(f"     ❌ 오류: {e}")

    # 4. 전체 합산 분석
    if analyze_total:
        print("\n🌐 전체 포트폴리오 분석 수행 중...")
        total_etfs = get_etf_holdings(year_month, db_path, exclude_tickers)

        total_investment = sum(etf['total_amount'] for etf in total_etfs)
        print(f"  💰 총 투자 금액: {total_investment:,}원")

        for etf_data in total_etfs:
            ticker = etf_data['ticker']
            name = etf_data['name']
            amount = etf_data['total_amount']
            asset_type = etf_data['asset_type']

            print(f"\n  📊 [전체] [{asset_type}] {name} ({ticker}): {amount:,}원")

            try:
                # 자산 유형별 분석 (account_id=None)
                if asset_type == 'STOCK':
                    analyze_stock_asset(ticker, name, amount, month_id, None, db_path)
                elif asset_type == 'BOND':
                    analyze_bond_asset(ticker, name, amount, month_id, None, db_path)
                elif asset_type == 'CASH':
                    analyze_cash_asset(ticker, name, amount, month_id, None, db_path)

                print(f"     ✅ 분석 완료")
            except Exception as e:
                print(f"     ❌ 오류: {e}")

    # 5. 결과 출력
    print("\n" + "=" * 80)
    print("💾 분석 완료! DB에 저장되었습니다.")
    print("=" * 80)

    # 전체 포트폴리오 집계 및 출력
    if analyze_total:
        holdings_df = aggregate_holdings(month_id, None, db_path)
        sectors_df = aggregate_sectors(month_id, None, db_path)
        total_inv = holdings_df['total_amount'].sum() if not holdings_df.empty else 0
        print_analysis_summary(holdings_df, sectors_df, total_inv, "전체 포트폴리오")

        # 환율 정보 표시
        print(f"\n💱 환율 정보: 1 USD = {exchange_rate:,.2f} KRW로 계산됨")
        print(f"   (미국 ETF의 원화 환산 금액은 이 환율 기준)")

        # 통합 Net Worth 분석 출력
        print_integrated_analysis(month_id, db_path)

    print("\n✅ 분석 완료!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="월별 포트폴리오 ETF 구성 분석")
    parser.add_argument("--month", required=True, help="분석할 년-월 (예: 2025-12)")
    parser.add_argument("--db", default="portfolio.db", help="SQLite DB 파일 경로")
    parser.add_argument("--overwrite", action="store_true", help="기존 분석 데이터 덮어쓰기")
    parser.add_argument("--exclude", default="", help="제외할 티커 (쉼표 구분, 기본값: 모든 자산 분석)")
    parser.add_argument("--skip-account", action="store_true", help="계좌별 분석 건너뛰기")
    parser.add_argument("--skip-total", action="store_true", help="전체 분석 건너뛰기")

    args = parser.parse_args()

    # 제외 티커 파싱
    exclude_tickers = [t.strip() for t in args.exclude.split(',') if t.strip()]

    # 분석 실행
    analyze_month_portfolio(
        year_month=args.month,
        db_path=args.db,
        overwrite=args.overwrite,
        exclude_tickers=exclude_tickers,
        analyze_by_account=not args.skip_account,
        analyze_total=not args.skip_total
    )
