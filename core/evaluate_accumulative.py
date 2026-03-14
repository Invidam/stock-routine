"""
적립식 투자 현황 평가 및 리포트 생성
DB에 저장된 수량을 기준으로 현재 가치를 평가
"""
import sqlite3
import yfinance as yf
import pandas as pd
from typing import Optional
from core.interest_calculator import calc_cash_current_value


def get_current_price(ticker: str) -> Optional[float]:
    """
    현재가 조회 (KRW 기준)

    Args:
        ticker: 종목 코드

    Returns:
        현재가 (원화) 또는 None
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # 현재가 조회 (여러 필드 시도)
        current_price = (info.get('currentPrice') or
                        info.get('regularMarketPrice') or
                        info.get('previousClose'))

        if current_price is None:
            return None

        # 한국 주식이 아니면 환율 적용
        if not ticker.endswith(('.KS', '.KQ')):
            try:
                exchange_rate = yf.Ticker("KRW=X").info.get('regularMarketPrice', 1450.0)
                current_price = current_price * exchange_rate
            except:
                current_price = current_price * 1450.0  # 기본 환율

        return float(current_price)

    except Exception as e:
        print(f"⚠️  {ticker} 현재가 조회 실패: {e}")
        return None


def evaluate_holdings(db_path: str = "portfolio.db") -> pd.DataFrame:
    """
    적립식 투자 종목의 현재 가치 평가

    Args:
        db_path: DB 경로

    Returns:
        DataFrame with columns:
        - ticker
        - asset_type
        - quantity (총 보유 수량)
        - invested (총 투자 금액)
        - avg_price (평단가)
        - current_price (현재가)
        - current_value (현재 평가액)
        - profit (평가 손익)
        - return_rate (수익률 %)
    """
    conn = sqlite3.connect(db_path)

    # 종목별 보유 수량 및 투자 금액 집계 (STOCK/BOND)
    holdings = pd.read_sql_query("""
        SELECT
            ticker,
            asset_type,
            SUM(quantity) as quantity,
            SUM(input_amount) as invested,
            ROUND(SUM(input_amount) / NULLIF(SUM(quantity), 0), 2) as avg_price,
            COUNT(*) as purchase_count,
            MIN(purchase_date) as first_purchase,
            MAX(purchase_date) as last_purchase
        FROM purchase_history
        WHERE asset_type != 'CASH'
        GROUP BY ticker, asset_type
        ORDER BY invested DESC
    """, conn)

    # CASH 개별 납입 내역 (이자 계산을 위해 행 단위로 조회)
    cash_records = pd.read_sql_query("""
        SELECT
            ticker,
            asset_type,
            input_amount,
            purchase_date,
            interest_rate,
            interest_type,
            account_id
        FROM purchase_history
        WHERE asset_type = 'CASH'
        ORDER BY purchase_date
    """, conn)

    # CASH를 name 기준으로 그룹핑하기 위해 account + holdings 조인으로 이름 조회
    cash_names = pd.read_sql_query("""
        SELECT DISTINCT
            ph.ticker,
            ph.interest_rate,
            ph.interest_type,
            h.name
        FROM purchase_history ph
        LEFT JOIN accounts a ON ph.account_id = a.id
        LEFT JOIN holdings h ON h.account_id = a.id AND h.ticker_mapping = ph.ticker AND h.asset_type = 'CASH'
        WHERE ph.asset_type = 'CASH'
    """, conn)

    conn.close()

    results = []

    # STOCK/BOND 처리
    if not holdings.empty:
        for _, row in holdings.iterrows():
            ticker = row['ticker']
            quantity = row['quantity']
            invested = row['invested']

            print(f"📊 {ticker}: {quantity:.4f}주 보유 (투자: {invested:,}원)")

            current_price = get_current_price(ticker)

            if current_price is None:
                print(f"   ⚠️  현재가 조회 실패 - 평가 제외")
                continue

            current_value = quantity * current_price
            profit = current_value - invested
            return_rate = (profit / invested * 100) if invested > 0 else 0

            print(f"   💰 평단가: {row['avg_price']:,.0f}원 | 현재가: {current_price:,.0f}원")
            print(f"   📈 평가액: {current_value:,.0f}원 | "
                  f"손익: {'+' if profit >= 0 else ''}{profit:,.0f}원 ({return_rate:+.2f}%)")

            results.append({
                'ticker': ticker,
                'asset_type': row['asset_type'],
                'quantity': quantity,
                'invested': invested,
                'avg_price': row['avg_price'],
                'current_price': current_price,
                'current_value': current_value,
                'profit': profit,
                'return_rate': return_rate,
                'purchase_count': row['purchase_count'],
                'first_purchase': row['first_purchase'],
                'last_purchase': row['last_purchase']
            })

    # CASH 처리 (적금 이자 반영)
    if not cash_records.empty:
        # interest_rate + interest_type 조합별로 그룹핑 (같은 적금 상품)
        cash_groups = cash_records.groupby(
            ['ticker', 'interest_rate', 'interest_type'],
            dropna=False
        )

        for (ticker, rate, itype), group in cash_groups:
            invested = int(group['input_amount'].sum())
            rate = rate if pd.notna(rate) else None
            itype = itype if pd.notna(itype) else 'simple'

            # 이름 찾기
            name_match = cash_names[
                (cash_names['ticker'] == ticker) &
                (cash_names['interest_rate'] == rate if pd.notna(rate) else cash_names['interest_rate'].isna())
            ]
            display_name = name_match['name'].iloc[0] if not name_match.empty and pd.notna(name_match['name'].iloc[0]) else f"CASH({rate*100:.1f}%)" if rate else "CASH"

            # 각 납입건별 이자 계산 후 합산
            total_value = 0.0
            for _, rec in group.iterrows():
                total_value += calc_cash_current_value(
                    principal=int(rec['input_amount']),
                    annual_rate=rate,
                    purchase_date=rec['purchase_date'],
                    interest_type=itype,
                )

            profit = total_value - invested
            return_rate = (profit / invested * 100) if invested > 0 else 0

            rate_str = f" ({rate*100:.1f}%, {'단리' if itype == 'simple' else '복리'})" if rate else ""
            print(f"💵 {display_name}{rate_str}: 투자 {invested:,}원")
            print(f"   📈 평가액: {total_value:,.0f}원 | "
                  f"이자: {'+' if profit >= 0 else ''}{profit:,.0f}원 ({return_rate:+.2f}%)")

            results.append({
                'ticker': display_name,
                'asset_type': 'CASH',
                'quantity': invested,
                'invested': invested,
                'avg_price': 1.0,
                'current_price': total_value / invested if invested > 0 else 1.0,
                'current_value': total_value,
                'profit': profit,
                'return_rate': return_rate,
                'purchase_count': len(group),
                'first_purchase': group['purchase_date'].min(),
                'last_purchase': group['purchase_date'].max(),
            })

    return pd.DataFrame(results)


def print_summary_report(holdings_df: pd.DataFrame):
    """
    적립식 투자 현황 요약 리포트 출력

    Args:
        holdings_df: evaluate_holdings 결과
    """
    if holdings_df.empty:
        print("\n⚠️  적립식 투자 데이터가 없습니다.")
        return

    print("\n" + "=" * 120)
    print("💰 [적립식 투자 현황 요약]")
    print("=" * 120)
    print(f"{'종목':<12} {'수량':>10} {'평단가':>12} {'현재가':>12} "
          f"{'투자금액':>14} {'평가금액':>14} {'손익':>14} {'수익률':>8} {'매수횟수':>8}")
    print("-" * 120)

    for _, row in holdings_df.iterrows():
        profit_sign = "+" if row['profit'] >= 0 else ""
        emoji = "🟢" if row['profit'] >= 0 else "🔴"

        print(f"{row['ticker']:<12} {row['quantity']:>10.4f} "
              f"{row['avg_price']:>12,.0f}원 {row['current_price']:>12,.0f}원 "
              f"{row['invested']:>14,}원 {row['current_value']:>14,.0f}원 "
              f"{emoji} {profit_sign}{row['profit']:>12,.0f}원 {row['return_rate']:>6.1f}% "
              f"{int(row['purchase_count']):>8}회")

    # 합계
    total_invested = holdings_df['invested'].sum()
    total_value = holdings_df['current_value'].sum()
    total_profit = total_value - total_invested
    total_return = (total_profit / total_invested * 100) if total_invested > 0 else 0

    print("-" * 120)
    print(f"{'합계':<12} {'':<10} {'':<12} {'':<12} "
          f"{total_invested:>14,}원 {total_value:>14,.0f}원 "
          f"{'+' if total_profit >= 0 else ''}{total_profit:>14,.0f}원 {total_return:>6.1f}%")
    print("=" * 120)


def print_detailed_report(holdings_df: pd.DataFrame):
    """
    종목별 상세 정보 출력

    Args:
        holdings_df: evaluate_holdings 결과
    """
    if holdings_df.empty:
        return

    print("\n" + "=" * 80)
    print("📋 [종목별 상세 정보]")
    print("=" * 80)

    for _, row in holdings_df.iterrows():
        print(f"\n🔹 {row['ticker']} ({row['asset_type']})")
        print(f"   총 보유 수량: {row['quantity']:.4f}주")
        print(f"   총 투자 금액: {row['invested']:,}원")
        print(f"   평균 단가: {row['avg_price']:,.0f}원")
        print(f"   현재 가격: {row['current_price']:,.0f}원")
        print(f"   현재 평가액: {row['current_value']:,.0f}원")
        print(f"   평가 손익: {'+' if row['profit'] >= 0 else ''}{row['profit']:,.0f}원 "
              f"({row['return_rate']:+.2f}%)")
        print(f"   매수 횟수: {int(row['purchase_count'])}회")
        print(f"   매수 기간: {row['first_purchase']} ~ {row['last_purchase']}")


def print_asset_allocation(holdings_df: pd.DataFrame):
    """
    자산 유형별 배분 현황 출력

    Args:
        holdings_df: evaluate_holdings 결과
    """
    if holdings_df.empty:
        return

    print("\n" + "=" * 80)
    print("📊 [자산 유형별 배분]")
    print("=" * 80)

    # 자산 유형별 집계
    allocation = holdings_df.groupby('asset_type').agg({
        'invested': 'sum',
        'current_value': 'sum'
    }).reset_index()

    total_value = allocation['current_value'].sum()

    for _, row in allocation.iterrows():
        asset_type = row['asset_type']
        invested = row['invested']
        value = row['current_value']
        profit = value - invested
        return_rate = (profit / invested * 100) if invested > 0 else 0
        allocation_pct = (value / total_value * 100) if total_value > 0 else 0

        print(f"\n🔸 {asset_type}")
        print(f"   투자 금액: {invested:,}원")
        print(f"   평가 금액: {value:,.0f}원 ({allocation_pct:.1f}%)")
        print(f"   손익: {'+' if profit >= 0 else ''}{profit:,.0f}원 ({return_rate:+.2f}%)")


def main(db_path: str = "portfolio.db", detailed: bool = False):
    """
    적립식 투자 평가 메인 함수

    Args:
        db_path: DB 경로
        detailed: 상세 리포트 출력 여부
    """
    print("🔍 적립식 투자 현황 평가 중...")
    print()

    # 평가
    holdings_df = evaluate_holdings(db_path)

    # 리포트 출력
    print_summary_report(holdings_df)

    if detailed and not holdings_df.empty:
        print_detailed_report(holdings_df)
        print_asset_allocation(holdings_df)

    print("\n✅ 평가 완료!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="적립식 투자 현황 평가 및 리포트")
    parser.add_argument("--db", default="portfolio.db", help="DB 경로")
    parser.add_argument("--detailed", action="store_true", help="상세 리포트 출력")

    args = parser.parse_args()

    main(args.db, args.detailed)
