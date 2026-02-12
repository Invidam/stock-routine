"""
월별 적립식 투자 데이터를 SQLite DB에 임포트하는 스크립트
사용자가 입력한 금액을 기준으로 수량을 자동 계산하여 저장
"""
import sqlite3
import yaml
import yfinance as yf
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple


def load_yaml(file_path: str) -> Dict[str, Any]:
    """YAML 파일 로드"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def get_historical_price(ticker: str, target_date: str, max_lookback_days: int = 7) -> Optional[Tuple[str, float, str]]:
    """
    특정 날짜의 종가를 조회 (휴일인 경우 직전 영업일)

    Args:
        ticker: 종목 코드
        target_date: 목표 날짜 (YYYY-MM-DD)
        max_lookback_days: 최대 과거 조회 일수

    Returns:
        (실제_날짜, 종가, 통화) 또는 None
        예: ('2024-11-26', 150.25, 'USD')
    """
    try:
        # 한국 주식인지 확인
        is_korean = ticker.endswith(('.KS', '.KQ'))

        # yfinance로 기간 데이터 조회
        stock = yf.Ticker(ticker)
        start_date = datetime.strptime(target_date, '%Y-%m-%d') - timedelta(days=max_lookback_days)
        end_date = datetime.strptime(target_date, '%Y-%m-%d') + timedelta(days=1)

        hist = stock.history(start=start_date.strftime('%Y-%m-%d'),
                            end=end_date.strftime('%Y-%m-%d'))

        if hist.empty:
            return None

        # 가장 최근 영업일의 종가
        latest_date = hist.index[-1].strftime('%Y-%m-%d')
        close_price = float(hist['Close'].iloc[-1])
        currency = 'KRW' if is_korean else 'USD'

        return (latest_date, close_price, currency)

    except Exception as e:
        print(f"      ⚠️  yfinance 조회 실패: {e}")
        return None


def get_price_from_db(ticker: str, target_date: str, db_path: str) -> Optional[float]:
    """
    DB에 저장된 과거 매수 기록에서 유사한 날짜의 주가를 찾음

    Args:
        ticker: 종목 코드
        target_date: 목표 날짜 (YYYY-MM-DD)
        db_path: DB 경로

    Returns:
        주가(KRW) 또는 None
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 목표 날짜와 가장 가까운 매수 기록 찾기 (±7일 이내)
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
    """
    특정 날짜의 USD/KRW 환율 조회

    Args:
        date: 날짜 (YYYY-MM-DD)

    Returns:
        환율 (1 USD = X KRW)
    """
    try:
        krw = yf.Ticker("KRW=X")
        start = datetime.strptime(date, '%Y-%m-%d') - timedelta(days=7)
        hist = krw.history(start=start.strftime('%Y-%m-%d'), end=date)

        if not hist.empty:
            return float(hist['Close'].iloc[-1])

        # 실패 시 최신 환율
        return float(yf.Ticker("KRW=X").info.get('regularMarketPrice', 1450.0))

    except:
        return 1450.0  # 기본값


def calculate_quantity(
    ticker: str,
    input_amount: int,
    year_month: str,
    purchase_day: int,
    db_path: str
) -> Dict[str, Any]:
    """
    투자 금액을 기준으로 매수 수량 계산

    Args:
        ticker: 종목 코드
        input_amount: 투자 금액 (원화)
        year_month: 기준 년월 (YYYY-MM)
        purchase_day: 매수 기준일 (26일 등)
        db_path: DB 경로

    Returns:
        {
            'purchase_date': '2024-11-26',
            'quantity': 1.5,
            'price_krw': 200000,
            'leftover': 0,
            'currency': 'USD',
            'exchange_rate': 1450.0
        }
    """
    # 1. 매수 기준일 생성
    purchase_date = f"{year_month}-{purchase_day:02d}"
    print(f"   📅 매수 기준일: {purchase_date}")

    # 2. 과거 주가 조회 (yfinance 우선)
    price_data = get_historical_price(ticker, purchase_date)

    if price_data is None:
        # yfinance 실패 시 DB에서 조회
        print(f"      🔍 DB에서 과거 데이터 조회 중...")
        db_price = get_price_from_db(ticker, purchase_date, db_path)

        if db_price is None:
            raise ValueError(f"❌ {ticker}의 {purchase_date} 주가를 찾을 수 없습니다. "
                           f"수동으로 price_at_purchase를 입력하거나 yfinance 데이터를 확인하세요.")

        # DB에서 가져온 가격 사용 (이미 KRW)
        actual_date = purchase_date
        price_krw = db_price
        currency = 'KRW'
        exchange_rate = None

    else:
        actual_date, close_price, currency = price_data
        print(f"      ✅ {actual_date} 종가: {close_price:,.2f} {currency}")

        # 3. 원화 환산
        if currency == 'KRW':
            price_krw = close_price
            exchange_rate = None
        else:
            exchange_rate = get_exchange_rate(actual_date)
            price_krw = close_price * exchange_rate
            print(f"      💱 환율: {exchange_rate:,.2f} KRW/USD → {price_krw:,.0f}원")

    # 4. 수량 계산
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


def save_purchase(
    ticker: str,
    asset_type: str,
    year_month: str,
    calc_result: Dict[str, Any],
    input_amount: int,
    account_name: Optional[str],
    note: Optional[str],
    db_path: str
):
    """purchase_history 테이블에 저장"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # account_id 찾기 (있는 경우)
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

        # purchase_history 삽입
        cursor.execute("""
            INSERT INTO purchase_history
            (ticker, asset_type, year_month, purchase_date,
             quantity, input_amount, price_at_purchase,
             currency, exchange_rate, account_id, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            note
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
    """지정된 월의 모든 구매 기록을 삭제합니다."""
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


def import_monthly_purchases(yaml_path: str, db_path: str = "portfolio.db", purchase_day: int = 26, overwrite: bool = False):
    """
    월별 적립식 투자 데이터를 임포트
    accounts > holdings 구조에서 데이터를 읽어옴

    Args:
        yaml_path: YAML 파일 경로
        db_path: DB 경로
        purchase_day: 매수 기준일 (기본값: 26일)
        overwrite: True이면 기존 월 데이터를 덮어씁니다.
    """
    print(f"\n📂 YAML 파일 읽는 중: {yaml_path}")
    data = load_yaml(yaml_path)

    # YAML에 purchase_day가 지정되어 있으면 CLI 파라미터 대신 사용
    yaml_purchase_day = data.get('purchase_day')
    if yaml_purchase_day is not None:
        print(f"   📅 YAML 지정 매수일: {yaml_purchase_day}일 (CLI 기본값 {purchase_day}일 대신 사용)")
        purchase_day = int(yaml_purchase_day)

    # year_month 추출 (파일명에서)
    file_stem = Path(yaml_path).stem  # 2025-11
    year_month = file_stem  # DB 조회 및 날짜 생성 모두 동일: 2025-11

    print(f"\n🎯 {year_month} 적립식 투자 데이터 임포트 시작")

    if overwrite:
        delete_purchase_history(year_month, db_path)

    # accounts 섹션 읽기
    accounts = data.get('accounts', [])
    if not accounts:
        print("❌ accounts 데이터가 없습니다.")
        return

    # 전체 holdings 수집
    all_purchases = []
    for account in accounts:
        account_name = account.get('name')
        holdings = account.get('holdings', [])

        for holding in holdings:
            asset_type = holding.get('asset_type', 'STOCK')

            all_purchases.append({
                'account_name': account_name,
                'ticker': holding.get('ticker_mapping'),
                'name': holding.get('name'),
                'amount': holding.get('amount'),
                'asset_type': asset_type
            })

    if not all_purchases:
        print("⚠️  투자 데이터가 없습니다.")
        return

    print(f"   총 {len(all_purchases)}건")
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
            # CASH인 경우 주가 조회 없이 간단히 저장
            if asset_type == 'CASH':
                calc_result = {
                    'purchase_date': f"{year_month}-{purchase_day:02d}",
                    'quantity': amount,  # 현금은 금액을 그대로 수량으로
                    'price_krw': 1.0,    # 1원당 1원
                    'leftover': 0,
                    'currency': 'KRW',
                    'exchange_rate': None
                }
                print(f"      💵 현금성 자산: 주가 조회 생략")
            else:
                # 수량 계산
                calc_result = calculate_quantity(
                    ticker=ticker,
                    input_amount=amount,
                    year_month=year_month,
                    purchase_day=purchase_day,
                    db_path=db_path
                )

            # DB 저장
            save_purchase(
                ticker=ticker,
                asset_type=asset_type,
                year_month=year_month,
                calc_result=calc_result,
                input_amount=amount,
                account_name=account_name,
                note=None,
                db_path=db_path
            )

            success_count += 1

        except Exception as e:
            print(f"      ❌ 실패: {e}")
            fail_count += 1

    print("\n" + "=" * 80)
    print(f"✅ 임포트 완료!")
    print(f"   - 성공: {success_count}건")
    print(f"   - 실패: {fail_count}건")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="월별 적립식 투자 데이터 임포트")
    parser.add_argument("yaml_file", help="YAML 파일 경로 (예: monthly/2025-11.yaml)")
    parser.add_argument("--db", default="portfolio.db", help="DB 경로")
    parser.add_argument("--purchase-day", type=int, default=26, help="매수 기준일 (기본값: 26일)")

    args = parser.parse_args()

    if not Path(args.yaml_file).exists():
        print(f"❌ 파일을 찾을 수 없습니다: {args.yaml_file}")
        exit(1)

    import_monthly_purchases(args.yaml_file, args.db, args.purchase_day)
