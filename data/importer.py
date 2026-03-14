"""
월별 YAML 데이터를 SQLite DB에 통합 임포트하는 모듈
- 계좌/보유종목 임포트 (months, accounts, holdings 테이블)
- 매수 기록 임포트 (purchase_history 테이블)
"""
import sqlite3
import yaml
import yfinance as yf
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple


def load_yaml(file_path: str) -> Dict[str, Any]:
    """YAML 파일을 읽어서 딕셔너리로 반환"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def extract_year_month(file_path: str) -> str:
    """파일명에서 년-월 정보를 추출 (예: 'monthly/2025-11.yaml' -> '2025-11')"""
    return Path(file_path).stem


# ---------------------------------------------------------------------------
# 가격 조회 함수
# ---------------------------------------------------------------------------

def get_historical_price(ticker: str, target_date: str, max_lookback_days: int = 7) -> Optional[Tuple[str, float, str]]:
    """
    특정 날짜의 종가를 조회 (휴일인 경우 직전 영업일)

    Returns:
        (실제_날짜, 종가, 통화) 또는 None
    """
    try:
        is_korean = ticker.endswith(('.KS', '.KQ'))
        stock = yf.Ticker(ticker)
        start_date = datetime.strptime(target_date, '%Y-%m-%d') - timedelta(days=max_lookback_days)
        end_date = datetime.strptime(target_date, '%Y-%m-%d') + timedelta(days=1)

        hist = stock.history(start=start_date.strftime('%Y-%m-%d'),
                            end=end_date.strftime('%Y-%m-%d'))

        if hist.empty:
            return None

        latest_date = hist.index[-1].strftime('%Y-%m-%d')
        close_price = float(hist['Close'].iloc[-1])
        currency = 'KRW' if is_korean else 'USD'

        return (latest_date, close_price, currency)

    except Exception as e:
        print(f"      ⚠️  yfinance 조회 실패: {e}")
        return None


def get_price_from_db(ticker: str, target_date: str, db_path: str) -> Optional[float]:
    """DB에 저장된 과거 매수 기록에서 유사한 날짜의 주가를 찾음"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT price_at_purchase, purchase_date
            FROM purchase_history
            WHERE ticker = ?
              AND purchase_date BETWEEN date(?, '-7 days') AND date(?, '+7 days')
              AND price_at_purchase IS NOT NULL
            ORDER BY ABS(julianday(purchase_date) - julianday(?))
            LIMIT 1
        """, (ticker, target_date, target_date, target_date))

        result = cursor.fetchone()
        conn.close()

        if result:
            price, found_date = result
            print(f"      💾 DB에서 찾음: {found_date} 주가 사용 ({price:,.0f}원)")
            return float(price)

        return None

    except Exception as e:
        print(f"      ⚠️  DB 조회 실패: {e}")
        return None


def get_exchange_rate(date: str) -> float:
    """특정 날짜의 USD/KRW 환율 조회"""
    try:
        krw = yf.Ticker("KRW=X")
        start = datetime.strptime(date, '%Y-%m-%d') - timedelta(days=7)
        hist = krw.history(start=start.strftime('%Y-%m-%d'), end=date)

        if not hist.empty:
            return float(hist['Close'].iloc[-1])

        return float(yf.Ticker("KRW=X").info.get('regularMarketPrice', 1450.0))

    except:
        return 1450.0


# ---------------------------------------------------------------------------
# 수량 계산
# ---------------------------------------------------------------------------

def calculate_quantity(
    ticker: str,
    input_amount: int,
    year_month: str,
    purchase_day: int,
    db_path: str
) -> Dict[str, Any]:
    """투자 금액을 기준으로 매수 수량 계산"""
    purchase_date = f"{year_month}-{purchase_day:02d}"
    print(f"   📅 매수 기준일: {purchase_date}")

    price_data = get_historical_price(ticker, purchase_date)

    if price_data is None:
        print(f"      🔍 DB에서 과거 데이터 조회 중...")
        db_price = get_price_from_db(ticker, purchase_date, db_path)

        if db_price is None:
            raise ValueError(f"❌ {ticker}의 {purchase_date} 주가를 찾을 수 없습니다. "
                           f"수동으로 price_at_purchase를 입력하거나 yfinance 데이터를 확인하세요.")

        actual_date = purchase_date
        price_krw = db_price
        currency = 'KRW'
        exchange_rate = None

    else:
        actual_date, close_price, currency = price_data
        print(f"      ✅ {actual_date} 종가: {close_price:,.2f} {currency}")

        if currency == 'KRW':
            price_krw = close_price
            exchange_rate = None
        else:
            exchange_rate = get_exchange_rate(actual_date)
            price_krw = close_price * exchange_rate
            print(f"      💱 환율: {exchange_rate:,.2f} KRW/USD → {price_krw:,.0f}원")

    quantity = input_amount / price_krw
    leftover = input_amount - (int(quantity) * price_krw)

    print(f"      🎯 매수 수량: {quantity:.4f}주 (잔돈: {int(leftover):,}원)")

    return {
        'purchase_date': actual_date,
        'quantity': quantity,
        'price_krw': price_krw,
        'leftover': int(leftover),
        'currency': currency,
        'exchange_rate': exchange_rate
    }


# ---------------------------------------------------------------------------
# DB 저장 함수
# ---------------------------------------------------------------------------

def save_purchase(
    ticker: str,
    asset_type: str,
    year_month: str,
    calc_result: Dict[str, Any],
    input_amount: int,
    account_name: Optional[str],
    note: Optional[str],
    db_path: str,
    interest_rate: Optional[float] = None,
    interest_type: Optional[str] = None,
):
    """purchase_history 테이블에 저장"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        account_id = None
        if account_name:
            cursor.execute("""
                SELECT a.id FROM accounts a
                INNER JOIN months m ON a.month_id = m.id
                WHERE a.name = ? AND m.year_month = ?
            """, (account_name, year_month))
            result = cursor.fetchone()
            if result:
                account_id = result[0]

        cursor.execute("""
            INSERT INTO purchase_history
            (ticker, asset_type, year_month, purchase_date,
             quantity, input_amount, price_at_purchase,
             currency, exchange_rate, account_id, note,
             interest_rate, interest_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ticker,
            asset_type,
            year_month,
            calc_result['purchase_date'],
            calc_result['quantity'],
            input_amount,
            calc_result['price_krw'],
            calc_result['currency'],
            calc_result['exchange_rate'],
            account_id,
            note,
            interest_rate,
            interest_type,
        ))

        conn.commit()
        print(f"      ✅ DB 저장 완료")

    except sqlite3.Error as e:
        print(f"      ❌ DB 저장 실패: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def delete_purchase_history(year_month: str, db_path: str):
    """지정된 월의 모든 구매 기록을 삭제"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        print(f"   🗑️  {year_month}의 기존 구매 기록 삭제 중...")
        cursor.execute("DELETE FROM purchase_history WHERE year_month = ?", (year_month,))
        conn.commit()
        print(f"   ✅ {cursor.rowcount}개의 기존 구매 기록 삭제 완료.")
    except sqlite3.Error as e:
        print(f"      ❌ DB 삭제 실패: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 통합 임포트 함수
# ---------------------------------------------------------------------------

def import_month(yaml_path: str, db_path: str = "portfolio.db", purchase_day: int = 26, overwrite: bool = False):
    """
    YAML → DB 통합 임포트 (계좌/보유종목 + 매수기록)

    Args:
        yaml_path: YAML 파일 경로
        db_path: SQLite DB 파일 경로
        purchase_day: 매수 기준일 (기본값: 26일)
        overwrite: True면 기존 데이터 삭제 후 재삽입
    """
    # 1. YAML 로드 (1회만)
    print(f"📂 YAML 파일 읽는 중: {yaml_path}")
    data = load_yaml(yaml_path)
    year_month = extract_year_month(yaml_path)

    # YAML에 purchase_day가 지정되어 있으면 사용
    yaml_purchase_day = data.get('purchase_day')
    if yaml_purchase_day is not None:
        print(f"   📅 YAML 지정 매수일: {yaml_purchase_day}일 (기본값 {purchase_day}일 대신 사용)")
        purchase_day = int(yaml_purchase_day)

    # 2. 포트폴리오 데이터 임포트 (months, accounts, holdings)
    _import_portfolio(data, year_month, db_path, overwrite)

    # 3. 매수 기록 임포트 (purchase_history)
    _import_purchases(data, year_month, purchase_day, db_path, overwrite)


def _import_portfolio(data: Dict, year_month: str, db_path: str, overwrite: bool):
    """계좌/보유종목을 months, accounts, holdings 테이블에 삽입"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id FROM months WHERE year_month = ?", (year_month,))
        existing_month = cursor.fetchone()

        if existing_month:
            if overwrite:
                print(f"⚠️  {year_month} 데이터가 이미 존재합니다. 삭제 후 재삽입합니다.")
                cursor.execute("DELETE FROM months WHERE year_month = ?", (year_month,))
            else:
                print(f"❌ {year_month} 데이터가 이미 존재합니다. --overwrite 옵션을 사용하세요.")
                return

        cursor.execute("INSERT INTO months (year_month) VALUES (?)", (year_month,))
        month_id = cursor.lastrowid
        print(f"✅ months 테이블 삽입: {year_month} (ID: {month_id})")

        accounts = data.get('accounts', [])
        total_accounts = 0
        total_holdings = 0

        for account in accounts:
            cursor.execute(
                "INSERT INTO accounts (month_id, name, type, broker, fee) VALUES (?, ?, ?, ?, ?)",
                (month_id, account['name'], account['type'], account['broker'], account.get('fee', 0.0))
            )
            account_id = cursor.lastrowid
            total_accounts += 1

            holdings_list = account.get('holdings', [])
            total_amount = sum(h['amount'] for h in holdings_list)

            for holding in holdings_list:
                asset_type = holding.get('asset_type', 'STOCK')
                interest_rate = holding.get('interest_rate')
                target_ratio = holding['amount'] / total_amount if total_amount > 0 else 0.0

                cursor.execute(
                    """INSERT INTO holdings
                    (account_id, name, ticker_mapping, amount, target_ratio, asset_type, interest_rate)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (account_id, holding['name'], holding['ticker_mapping'],
                     holding['amount'], target_ratio, asset_type, interest_rate)
                )
                total_holdings += 1

        conn.commit()
        print(f"✅ 포트폴리오 임포트 완료! (계좌: {total_accounts}개, 종목: {total_holdings}개)")

    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()


def _import_purchases(data: Dict, year_month: str, purchase_day: int, db_path: str, overwrite: bool):
    """매수 기록을 purchase_history 테이블에 삽입"""
    if overwrite:
        delete_purchase_history(year_month, db_path)

    accounts = data.get('accounts', [])
    if not accounts:
        print("❌ accounts 데이터가 없습니다.")
        return

    all_purchases = []
    for account in accounts:
        account_name = account.get('name')
        for holding in account.get('holdings', []):
            all_purchases.append({
                'account_name': account_name,
                'ticker': holding.get('ticker_mapping'),
                'name': holding.get('name'),
                'amount': holding.get('amount'),
                'asset_type': holding.get('asset_type', 'STOCK'),
                'interest_rate': holding.get('interest_rate'),
                'interest_type': holding.get('interest_type', 'simple'),
            })

    if not all_purchases:
        print("⚠️  투자 데이터가 없습니다.")
        return

    print(f"\n🎯 {year_month} 매수 기록 임포트 시작 (총 {len(all_purchases)}건)")
    print("=" * 80)

    success_count = 0
    fail_count = 0

    for i, purchase in enumerate(all_purchases, 1):
        ticker = purchase['ticker']
        name = purchase['name']
        amount = purchase['amount']
        asset_type = purchase['asset_type']
        account_name = purchase['account_name']

        print(f"\n[{i}/{len(all_purchases)}] {name} ({ticker})")
        print(f"   💰 투자 금액: {amount:,}원")
        print(f"   🏦 계좌: {account_name}")

        try:
            if asset_type == 'CASH':
                calc_result = {
                    'purchase_date': f"{year_month}-{purchase_day:02d}",
                    'quantity': amount,
                    'price_krw': 1.0,
                    'leftover': 0,
                    'currency': 'KRW',
                    'exchange_rate': None
                }
                print(f"      💵 현금성 자산: 주가 조회 생략")
            else:
                calc_result = calculate_quantity(
                    ticker=ticker,
                    input_amount=amount,
                    year_month=year_month,
                    purchase_day=purchase_day,
                    db_path=db_path
                )

            save_purchase(
                ticker=ticker,
                asset_type=asset_type,
                year_month=year_month,
                calc_result=calc_result,
                input_amount=amount,
                account_name=account_name,
                note=None,
                db_path=db_path,
                interest_rate=purchase.get('interest_rate'),
                interest_type=purchase.get('interest_type'),
            )

            success_count += 1

        except Exception as e:
            print(f"      ❌ 실패: {e}")
            fail_count += 1

    print("\n" + "=" * 80)
    print(f"✅ 매수 기록 임포트 완료! (성공: {success_count}건, 실패: {fail_count}건)")


# ---------------------------------------------------------------------------
# 하위 호환 래퍼 (기존 코드가 참조하는 경우)
# ---------------------------------------------------------------------------

def import_monthly_data(yaml_path: str, db_path: str = "portfolio.db", overwrite: bool = False):
    """하위 호환: _import_portfolio만 실행"""
    data = load_yaml(yaml_path)
    year_month = extract_year_month(yaml_path)
    _import_portfolio(data, year_month, db_path, overwrite)


def import_monthly_purchases(yaml_path: str, db_path: str = "portfolio.db", purchase_day: int = 26, overwrite: bool = False):
    """하위 호환: _import_purchases만 실행"""
    data = load_yaml(yaml_path)
    year_month = extract_year_month(yaml_path)

    yaml_purchase_day = data.get('purchase_day')
    if yaml_purchase_day is not None:
        purchase_day = int(yaml_purchase_day)

    _import_purchases(data, year_month, purchase_day, db_path, overwrite)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="월별 YAML 데이터를 SQLite DB에 통합 임포트")
    parser.add_argument("yaml_file", help="YAML 파일 경로 (예: monthly/2025-11.yaml)")
    parser.add_argument("--db", default="portfolio.db", help="DB 경로")
    parser.add_argument("--purchase-day", type=int, default=26, help="매수 기준일 (기본값: 26일)")
    parser.add_argument("--overwrite", action="store_true", help="기존 데이터 덮어쓰기")

    args = parser.parse_args()

    if not Path(args.yaml_file).exists():
        print(f"❌ 파일을 찾을 수 없습니다: {args.yaml_file}")
        exit(1)

    import_month(args.yaml_file, args.db, args.purchase_day, args.overwrite)
