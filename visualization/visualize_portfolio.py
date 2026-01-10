"""
포트폴리오 시각화 스크립트
Matplotlib을 사용하여 차트 이미지 생성
"""
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import pandas as pd

# 한글 폰트 설정
plt.rcParams['font.family'] = 'AppleGothic'  # macOS
plt.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지


def get_net_worth(month_id: int, db_path: str) -> dict:
    """자산 유형별 금액 조회"""
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


def get_sector_distribution(month_id: int, db_path: str, limit: int = 10) -> pd.DataFrame:
    """섹터별 비중 조회 (상위 N개)"""
    conn = sqlite3.connect(db_path)

    query = """
        SELECT sector_name, asset_type, SUM(my_amount) as amount
        FROM analyzed_sectors
        WHERE month_id = ? AND account_id IS NULL
        GROUP BY sector_name, asset_type
        ORDER BY amount DESC
        LIMIT ?
    """

    df = pd.read_sql_query(query, conn, params=(month_id, limit))
    conn.close()

    return df


def get_top_holdings(month_id: int, db_path: str, limit: int = 10) -> pd.DataFrame:
    """상위 보유 항목 조회 (터미널 출력과 동일한 로직)"""
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

    # OTHER 제외
    df = df[df['stock_symbol'] != 'OTHER']

    return df


def get_cumulative_net_worth(up_to_month: str, db_path: str) -> dict:
    """
    해당 월까지의 누적 자산 계산

    투자금액은 purchase_history에서 누적 계산
    현재가치는 누적 수량 × 현재 시장가로 계산

    Args:
        up_to_month: 기준 월 (YYYY-MM)
        db_path: 데이터베이스 경로

    Returns:
        {
            'total_invested': 4560000,
            'total_current': 4823000,
            'profit': 263000,
            'return_rate': 5.77,
            'by_type': {
                'STOCK': {
                    'invested': 3240000,
                    'current': 3450000,
                    'percentage': 71.57
                },
                ...
            }
        }
    """
    import yfinance as yf

    conn = sqlite3.connect(db_path)

    # 1. purchase_history에서 투자금액 및 수량 누적 (CASH 제외)
    holdings_df = pd.read_sql_query("""
        SELECT
            ticker,
            asset_type,
            SUM(quantity) as total_quantity,
            SUM(input_amount) as invested,
            AVG(exchange_rate) as avg_exchange_rate
        FROM purchase_history
        WHERE year_month <= ?
        GROUP BY ticker, asset_type
    """, conn, params=(up_to_month,))

    # 2. holdings에서 CASH 누적
    cash_df = pd.read_sql_query("""
        SELECT
            'CASH' as ticker,
            'CASH' as asset_type,
            0.0 as total_quantity,
            SUM(h.amount) as invested,
            NULL as avg_exchange_rate
        FROM holdings h
        JOIN accounts a ON h.account_id = a.id
        JOIN months m ON a.month_id = m.id
        WHERE h.asset_type = 'CASH' AND m.year_month <= ?
    """, conn, params=(up_to_month,))

    conn.close()

    # 3. 전체 holdings 합치기
    if not cash_df.empty and cash_df['invested'].iloc[0] is not None:
        holdings_df = pd.concat([holdings_df, cash_df], ignore_index=True)

    if holdings_df.empty:
        return {
            'total_invested': 0,
            'total_current': 0,
            'profit': 0,
            'return_rate': 0,
            'by_type': {}
        }

    # 4. 환율 조회
    try:
        exchange_rate = yf.Ticker("KRW=X").fast_info['last_price']
    except:
        exchange_rate = 1450.0

    # 5. 각 ticker별 현재가 조회 및 current_value 계산
    holdings_df['current_value'] = 0.0

    for idx, row in holdings_df.iterrows():
        ticker = row['ticker']
        quantity = row['total_quantity']
        asset_type = row['asset_type']
        invested = row['invested']

        if asset_type == 'CASH' or ticker == 'CASH':
            # CASH는 그대로 현재가치 = 투자금액
            holdings_df.at[idx, 'current_value'] = invested
        else:
            try:
                # yfinance로 현재가 조회
                stock = yf.Ticker(ticker)
                current_price_usd = stock.fast_info['last_price']

                # 한국 주식 여부 확인
                is_korean = ticker.endswith(('.KS', '.KQ'))
                if is_korean:
                    current_value = quantity * current_price_usd
                else:
                    current_value = quantity * current_price_usd * exchange_rate

                holdings_df.at[idx, 'current_value'] = current_value

            except Exception as e:
                # 가격 조회 실패 시 투자금액으로 대체
                print(f"⚠️  {ticker} 현재가 조회 실패, 투자금액 사용: {e}")
                holdings_df.at[idx, 'current_value'] = invested

    # 6. asset_type별 집계
    by_type_df = holdings_df.groupby('asset_type').agg({
        'invested': 'sum',
        'current_value': 'sum'
    }).reset_index()

    # 7. 결과 계산
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
    result['total'] = total_current  # 기존 호환성 유지

    return result


def get_month_id(year_month: str, db_path: str) -> int:
    """year_month로부터 month_id 조회"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM months WHERE year_month = ?", (year_month,))
    result = cursor.fetchone()
    conn.close()

    if not result:
        raise ValueError(f"Month {year_month} not found in database")

    return result[0]


def create_asset_allocation_chart(net_worth: dict, output_path: str):
    """자산 배분 도넛 차트 생성"""
    labels_map = {
        'STOCK': '위험 자산\n(주식형)',
        'BOND': '안전 자산\n(채권형)',
        'CASH': '현금성 자산\n(적금)'
    }

    colors = {
        'STOCK': '#FF6B6B',  # 빨강 (위험)
        'BOND': '#4ECDC4',   # 청록 (안전)
        'CASH': '#95E1D3'    # 연두 (현금)
    }

    labels = []
    sizes = []
    chart_colors = []

    for asset_type, data in net_worth['by_type'].items():
        labels.append(labels_map.get(asset_type, asset_type))
        # 새로운 구조: data는 dict (invested, current, percentage)
        amount = data.get('current', data) if isinstance(data, dict) else data
        sizes.append(amount)
        chart_colors.append(colors.get(asset_type, '#CCCCCC'))

    fig, ax = plt.subplots(figsize=(10, 8))

    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=labels,
        colors=chart_colors,
        autopct='%1.1f%%',
        startangle=90,
        pctdistance=0.85,
        textprops={'fontsize': 12, 'weight': 'bold'}
    )

    # 도넛 차트로 만들기
    centre_circle = plt.Circle((0, 0), 0.70, fc='white')
    fig.gca().add_artist(centre_circle)

    # 중앙에 투자금액, 평가금액, 수익률 표시
    if 'total_invested' in net_worth:
        # 누적 모드
        invested = net_worth['total_invested']
        current = net_worth['total_current']
        profit = net_worth['profit']
        return_rate = net_worth['return_rate']

        center_text = f'투자: {invested:,}원\n'
        center_text += f'평가: {current:,}원\n'
        if profit >= 0:
            center_text += f'수익: +{profit:,}원\n({return_rate:+.2f}%)'
        else:
            center_text += f'손실: {profit:,}원\n({return_rate:.2f}%)'

        ax.text(0, 0, center_text,
                ha='center', va='center', fontsize=14, weight='bold')
    else:
        # 기존 모드 (단일 월)
        ax.text(0, 0, f'총 자산\n{net_worth["total"]:,}원',
                ha='center', va='center', fontsize=16, weight='bold')

    ax.axis('equal')
    plt.title('💰 자산 배분 (Asset Allocation)', fontsize=18, weight='bold', pad=20)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"✅ 자산 배분 차트 저장: {output_path}")


def create_sector_chart(sectors_df: pd.DataFrame, output_path: str):
    """섹터별 비중 막대 차트 생성"""
    if sectors_df.empty:
        print("⚠️  섹터 데이터가 없어 차트를 생성하지 않습니다.")
        return

    fig, ax = plt.subplots(figsize=(12, 8))

    # 색상 매핑
    colors_map = {
        'STOCK': '#FF6B6B',
        'BOND': '#4ECDC4',
        'CASH': '#95E1D3'
    }

    colors = [colors_map.get(asset_type, '#CCCCCC') for asset_type in sectors_df['asset_type']]

    bars = ax.barh(sectors_df['sector_name'], sectors_df['amount'], color=colors)

    # 금액 레이블 추가
    for i, (bar, amount) in enumerate(zip(bars, sectors_df['amount'])):
        ax.text(bar.get_width() + max(sectors_df['amount']) * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f'{int(amount):,}원',
                va='center', fontsize=10)

    ax.set_xlabel('금액 (원)', fontsize=12, weight='bold')
    ax.set_title('📊 섹터별 자산 분포 (Top 10)', fontsize=18, weight='bold', pad=20)
    ax.invert_yaxis()  # 상위 항목을 위에 표시

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"✅ 섹터별 차트 저장: {output_path}")


def create_top_holdings_chart(holdings_df: pd.DataFrame, output_path: str, top_n: int = 50):
    """상위 보유 종목 막대 차트 생성 (TOP 50)

    Args:
        holdings_df: 보유 종목 데이터 (OTHER 포함 가능)
        output_path: 저장 경로
        top_n: 표시할 종목 수 (기본 50)
    """
    if holdings_df.empty:
        print("⚠️  보유 종목 데이터가 없어 차트를 생성하지 않습니다.")
        return

    # OTHER 분리
    other_rows = holdings_df[holdings_df['stock_symbol'] == 'OTHER']
    regular_rows = holdings_df[holdings_df['stock_symbol'] != 'OTHER']

    # 상위 N개 + OTHER를 맨 마지막에
    top_rows = regular_rows.head(top_n - 1)  # OTHER 자리 확보
    if not other_rows.empty:
        display_df = pd.concat([top_rows, other_rows], ignore_index=True)
    else:
        display_df = top_rows

    # 총 금액 계산 (비율용)
    total_amount = display_df['amount'].sum()

    # 초장형 차트 생성
    fig_height = max(70, len(display_df) * 1.4)  # 종목 수에 비례
    fig, ax = plt.subplots(figsize=(16, fig_height))

    # Y축 레이블 생성 (한국 주식은 실제 이름)
    y_labels = []
    for idx, row in display_df.iterrows():
        if row['stock_symbol'] == 'OTHER':
            y_labels.append('기타 종목 (상위 10개 외)')
        elif row['asset_type'] == 'STOCK' and pd.notna(row.get('stock_symbol')) and str(row['stock_symbol']).endswith('.KS'):
            # 한국 주식: 실제 이름
            y_labels.append(row['stock_name'])
        else:
            # 미국 주식, 채권, 현금: ticker/이름
            y_labels.append(row['display_name'])

    # 색상 매핑
    colors_map = {
        'STOCK': '#FF6B6B',
        'BOND': '#4ECDC4',
        'CASH': '#95E1D3'
    }

    colors = []
    for idx, row in display_df.iterrows():
        if row['stock_symbol'] == 'OTHER':
            colors.append('#CCCCCC')  # 회색
        else:
            colors.append(colors_map.get(row['asset_type'], '#999999'))

    # 막대 그래프
    bars = ax.barh(range(len(display_df)), display_df['amount'], color=colors)

    # 상위 3개 테두리 강조 (OTHER 제외)
    for i, (bar, row) in enumerate(zip(bars, display_df.itertuples())):
        if row.stock_symbol != 'OTHER' and i < 3:
            bar.set_edgecolor('black')
            bar.set_linewidth(2.5 - i * 0.5)  # 1위가 가장 굵게

    # Y축 설정
    ax.set_yticks(range(len(display_df)))
    ax.set_yticklabels(y_labels, fontsize=10)
    ax.invert_yaxis()  # 상위 항목을 위에

    # 금액 + 비율 레이블
    max_amount = display_df['amount'].max()
    for i, (bar, amount) in enumerate(zip(bars, display_df['amount'])):
        percentage = (amount / total_amount * 100) if total_amount > 0 else 0
        label_text = f'{int(amount):,}원 ({percentage:.1f}%)'

        ax.text(bar.get_width() + max_amount * 0.01,
                bar.get_y() + bar.get_height() / 2,
                label_text,
                va='center', fontsize=9, weight='bold')

    # OTHER 위에 구분선
    if not other_rows.empty:
        other_idx = len(display_df) - 1
        ax.axhline(y=other_idx - 0.5, color='gray', linestyle='--', linewidth=1.5, alpha=0.7)

    # 축 레이블
    ax.set_xlabel('금액 (원)', fontsize=14, weight='bold')
    ax.set_title(f'🏆 상위 보유 종목 (TOP {len(display_df)})', fontsize=20, weight='bold', pad=20)

    # 범례
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#FF6B6B', label='주식'),
        Patch(facecolor='#4ECDC4', label='채권'),
        Patch(facecolor='#95E1D3', label='현금'),
        Patch(facecolor='#CCCCCC', label='기타')
    ]
    ax.legend(handles=legend_elements, loc='lower right', fontsize=12)

    # 하단 설명
    if not other_rows.empty:
        fig.text(0.5, 0.01, '※ 기타: yfinance는 ETF 상위 10개 종목만 제공하므로 나머지를 합산',
                ha='center', fontsize=10, style='italic', color='gray')

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"✅ 상위 보유 종목 차트 저장: {output_path} (총 {len(display_df)}개 항목)")


def create_asset_trend_chart(db_path: str, output_path: str, months: int = 6):
    """자산 추이 라인 차트 생성 (투자금액 vs 평가금액)"""
    conn = sqlite3.connect(db_path)

    # 1. 투자금액 누적 (purchase_history)
    invested_query = """
        SELECT
            year_month,
            SUM(input_amount) as monthly_invested
        FROM purchase_history
        GROUP BY year_month
        ORDER BY year_month
    """

    invested_df = pd.read_sql_query(invested_query, conn)

    # 2. CASH 추가 (holdings)
    cash_query = """
        SELECT
            m.year_month,
            SUM(h.amount) as cash_amount
        FROM holdings h
        JOIN accounts a ON h.account_id = a.id
        JOIN months m ON a.month_id = m.id
        WHERE h.asset_type = 'CASH'
        GROUP BY m.year_month
        ORDER BY m.year_month
    """

    cash_df = pd.read_sql_query(cash_query, conn)

    # 3. 평가금액 (analyzed_holdings)
    value_query = """
        SELECT
            m.year_month,
            SUM(ah.my_amount) as current_value
        FROM months m
        JOIN analyzed_holdings ah ON m.id = ah.month_id
        WHERE ah.account_id IS NULL
        GROUP BY m.year_month
        ORDER BY m.year_month
    """

    value_df = pd.read_sql_query(value_query, conn)
    conn.close()

    # 4. 데이터 병합
    df = pd.merge(invested_df, cash_df, on='year_month', how='outer')
    df = pd.merge(df, value_df, on='year_month', how='outer')
    df = df.fillna(0)

    # 누적 투자금액 계산
    df['cumulative_invested'] = (df['monthly_invested'] + df['cash_amount']).cumsum()

    # 최근 N개월만 표시
    df = df.tail(months)

    if df.empty or len(df) < 1:
        print(f"⚠️  자산 추이를 표시하기 위한 충분한 데이터가 없습니다")
        return

    # 5. 차트 생성
    fig, ax = plt.subplots(figsize=(14, 7))

    # 투자금액 선 (파란색)
    ax.plot(df['year_month'], df['cumulative_invested'],
            marker='o', linewidth=2.5, markersize=8,
            color='#4A90E2', label='투자금액', zorder=3)

    # 평가금액 선 (초록색)
    ax.plot(df['year_month'], df['current_value'],
            marker='s', linewidth=2.5, markersize=8,
            color='#50C878', label='평가금액', zorder=3)

    # 면적 채우기 (수익 영역)
    ax.fill_between(df['year_month'], df['cumulative_invested'], df['current_value'],
                     where=(df['current_value'] >= df['cumulative_invested']),
                     alpha=0.2, color='#50C878', label='수익')

    # 면적 채우기 (손실 영역)
    ax.fill_between(df['year_month'], df['cumulative_invested'], df['current_value'],
                     where=(df['current_value'] < df['cumulative_invested']),
                     alpha=0.2, color='#FF6B6B', label='손실')

    # 각 포인트에 금액 표시
    for i, row in df.iterrows():
        # 투자금액
        ax.text(row['year_month'], row['cumulative_invested'] + max(df['current_value']) * 0.02,
                f'{int(row["cumulative_invested"]):,}',
                ha='center', fontsize=9, weight='bold', color='#4A90E2')
        # 평가금액
        ax.text(row['year_month'], row['current_value'] - max(df['current_value']) * 0.02,
                f'{int(row["current_value"]):,}',
                ha='center', fontsize=9, weight='bold', color='#50C878')

    ax.set_xlabel('월', fontsize=12, weight='bold')
    ax.set_ylabel('금액 (원)', fontsize=12, weight='bold')
    ax.set_title(f'📈 자산 추이 (투자금액 vs 평가금액)', fontsize=18, weight='bold', pad=20)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(loc='upper left', fontsize=11, framealpha=0.9)

    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"✅ 자산 추이 차트 저장: {output_path}")


def visualize_portfolio(year_month: str, db_path: str = "portfolio.db", output_dir: str = "charts"):
    """
    포트폴리오 시각화 메인 함수 (누적 모드)

    Args:
        year_month: 분석할 월 (YYYY-MM)
        db_path: 데이터베이스 경로
        output_dir: 차트 저장 디렉토리
    """
    print(f"📊 {year_month}월 포트폴리오 시각화 시작")
    print(f"   (누적 모드: {year_month}까지의 모든 투자 포함)")
    print("=" * 80)

    # 출력 디렉토리 생성
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # month_id 조회
    try:
        month_id = get_month_id(year_month, db_path)
    except ValueError as e:
        print(f"❌ {e}")
        return

    # 1. 자산 배분 차트 (누적)
    net_worth = get_cumulative_net_worth(year_month, db_path)
    create_asset_allocation_chart(
        net_worth,
        output_path / f"{year_month}_asset_allocation.png"
    )

    # 2. 섹터별 차트 (해당 월)
    sectors_df = get_sector_distribution(month_id, db_path, limit=10)
    create_sector_chart(
        sectors_df,
        output_path / f"{year_month}_sectors.png"
    )

    # 3. 상위 보유 종목 차트 (해당 월, TOP 50)
    holdings_df = get_top_holdings(month_id, db_path, limit=999)
    create_top_holdings_chart(
        holdings_df,
        output_path / f"{year_month}_top_holdings.png",
        top_n=50
    )

    # 4. 자산 추이 차트 (누적, 고정 파일명)
    create_asset_trend_chart(
        db_path,
        output_path / "cumulative_asset_trend.png",
        months=12
    )

    print("=" * 80)
    print(f"✅ 시각화 완료! 차트는 '{output_dir}/' 디렉토리에 저장되었습니다.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="포트폴리오 시각화")
    parser.add_argument("--month", required=True, help="분석할 월 (YYYY-MM)")
    parser.add_argument("--db", default="portfolio.db", help="SQLite DB 파일 경로")
    parser.add_argument("--output", default="charts", help="차트 저장 디렉토리")

    args = parser.parse_args()

    visualize_portfolio(args.month, args.db, args.output)
