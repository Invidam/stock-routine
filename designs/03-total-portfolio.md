# 전체 포트폴리오 페이지 UI 디자인

## 1. 페이지 개요

**목적**: 모든 계좌를 통합하여 전체 포트폴리오 현황을 한눈에 파악

**주요 기능**:
- Sunburst Chart (계층적 자산 구성 시각화)
- 종목 검색 기능 (직접 보유 + ETF 내 간접 보유)
- 통합 섹터 비중 (Horizontal Bar Chart)
- Top 20 보유 종목
- 자산 유형별 요약 (STOCK/BOND/CASH)

## 2. 레이아웃 구조

```
┌────────────────────────────────────────────────────────────────┐
│  🏆 전체 포트폴리오 - 2025-12                                     │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  💰 자산 유형별 요약                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                     │
│  │ 📈 주식형 │  │ 💵 채권형 │  │ 💰 현금형 │                     │
│  │          │  │          │  │          │                     │
│  │ 819,982원│  │ 300,000원│  │ 350,000원│                     │
│  │  55.8%   │  │  20.4%   │  │  23.8%   │                     │
│  └──────────┘  └──────────┘  └──────────┘                     │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  🌞 자산 구성 (Sunburst Chart)                                  │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                        ROOT                              │ │
│  │                    ╱    │    ╲                          │ │
│  │                  ╱      │      ╲                        │ │
│  │              STOCK    BOND    CASH                      │ │
│  │              55.8%    20.4%   23.8%                     │ │
│  │             ╱  │  ╲     │                               │ │
│  │          Tech Fin Health                                │ │
│  │          42%  8%  6%                                     │ │
│  │         ╱ │ ╲                                           │ │
│  │      AAPL MSFT NVDA                                     │ │
│  │      3.2% 2.9% 3.3%                                     │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  💡 차트를 클릭하면 세부 항목으로 드릴다운할 수 있습니다.          │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  🔍 종목 검색                                                   │
│                                                                │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ 종목 코드 입력: [ AAPL              ] 🔍               │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                │
│  📊 검색 결과: AAPL (Apple Inc.)                               │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ • 직접 보유:   10.00주  (150,000원)                      │ │
│  │ • ETF 통해:     3.50주  ( 52,500원)                      │ │
│  │   - SPY에서:   2.00주  ( 30,000원)                       │ │
│  │   - QQQ에서:   1.50주  ( 22,500원)                       │ │
│  │ ────────────────────────────────────                     │ │
│  │ ✅ 총 보유:    13.50주  (202,500원)                      │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  📊 통합 섹터 비중 (Top 10)                                     │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ Technology          ██████████████████ 42.4%  (347,000원)│ │
│  │ Cash & Equivalents  ███████████ 23.8%         (350,000원)│ │
│  │ Fixed Income        ██████████ 20.4%          (300,000원)│ │
│  │ Communication       ████ 10.8%                 (88,000원)│ │
│  │ Healthcare          ██ 5.2%                    (42,000원)│ │
│  │ Financials          █ 3.1%                     (25,000원)│ │
│  │ ...                                                      │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  🏅 통합 보유 종목 Top 20                                       │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ 순위│ 종목        │ 유형  │ 금액      │ 비중  │ 출처      │ │
│  ├─────┼─────────────┼───────┼───────────┼───────┼───────────┤ │
│  │  1  │ 일반적금     │ CASH  │ 300,000원 │ 20.4% │ ISA       │ │
│  │  2  │ TLT         │ BOND  │ 300,000원 │ 20.4% │ ISA       │ │
│  │  3  │ 삼성전자    │ STOCK │ 150,000원 │ 10.2% │ 일반      │ │
│  │  4  │ NVDA        │ STOCK │  49,190원 │  3.3% │ SPY,QQQ   │ │
│  │  5  │ AAPL        │ STOCK │  47,205원 │  3.2% │ SPY,QQQ   │ │
│  │  6  │ MSFT        │ STOCK │  42,860원 │  2.9% │ SPY,QQQ   │ │
│  │  7  │ GOOGL       │ STOCK │  31,200원 │  2.1% │ SPY,QQQ   │ │
│  │ ... │ ...         │ ...   │ ...       │ ...   │ ...       │ │
│  │ 20  │ JPM         │ STOCK │  12,500원 │  0.8% │ SPY       │ │
│  └─────┴─────────────┴───────┴───────────┴───────┴───────────┘ │
│                                                                │
│  💡 ETF 내부 종목은 [출처] 컬럼에 ETF 이름이 표시됩니다.          │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

## 3. 컴포넌트 상세 설계

### 3.1 자산 유형별 요약 (Metric Cards)

**컴포넌트**: `st.metric()`

```python
def render(selected_month: str):
    """전체 포트폴리오 페이지 렌더링"""

    st.header(f"🏆 전체 포트폴리오 - {selected_month}")

    # 자산 유형별 요약 조회
    asset_summary = get_asset_type_summary(selected_month)

    st.subheader("💰 자산 유형별 요약")
    col1, col2, col3 = st.columns(3)

    total = asset_summary['STOCK'] + asset_summary['BOND'] + asset_summary['CASH']

    with col1:
        st.metric(
            "📈 주식형",
            f"{asset_summary['STOCK']:,}원",
            delta=f"{asset_summary['STOCK']/total*100:.1f}%"
        )

    with col2:
        st.metric(
            "💵 채권형",
            f"{asset_summary['BOND']:,}원",
            delta=f"{asset_summary['BOND']/total*100:.1f}%"
        )

    with col3:
        st.metric(
            "💰 현금형",
            f"{asset_summary['CASH']:,}원",
            delta=f"{asset_summary['CASH']/total*100:.1f}%"
        )

    st.divider()
```

**데이터 구조** (`asset_summary`):
```python
{
    'STOCK': 819982,
    'BOND': 300000,
    'CASH': 350000
}
```

### 3.2 Sunburst Chart (핵심 차트)

**컴포넌트**: `plotly.graph_objects.Sunburst`

```python
import plotly.graph_objects as go

def create_sunburst_chart(selected_month: str):
    """
    계층 구조:
    ROOT
      ├─ STOCK (55.8%)
      │    ├─ Technology (42.4%)
      │    │    ├─ AAPL (3.2%)
      │    │    ├─ MSFT (2.9%)
      │    │    └─ NVDA (3.3%)
      │    ├─ Communication (10.8%)
      │    └─ Healthcare (5.2%)
      ├─ BOND (20.4%)
      │    └─ Fixed Income (20.4%)
      │         └─ TLT (20.4%)
      └─ CASH (23.8%)
           └─ Cash & Equivalents (23.8%)
                └─ 일반적금 (20.4%)
    """

    # 계층 데이터 조회
    df = get_hierarchical_portfolio_data(selected_month)

    # Sunburst 차트 생성
    fig = go.Figure(go.Sunburst(
        labels=df['labels'],
        parents=df['parents'],
        values=df['values'],
        branchvalues="total",  # 부모 값 = 자식 값 합계
        marker=dict(
            colors=df['colors'],
            line=dict(color='white', width=2)
        ),
        hovertemplate='<b>%{label}</b><br>금액: %{value:,}원<br>비중: %{percentParent}<extra></extra>'
    ))

    fig.update_layout(
        title="🌞 자산 구성 (Sunburst Chart)",
        height=600,
        margin=dict(t=50, l=0, r=0, b=0)
    )

    return fig

# 렌더링
st.subheader("🌞 자산 구성")
fig = create_sunburst_chart(selected_month)
st.plotly_chart(fig, use_container_width=True)
st.caption("💡 차트를 클릭하면 세부 항목으로 드릴다운할 수 있습니다.")
```

**데이터 구조** (`df`):
```python
   labels              parents          values    colors
0  ROOT                ""               1469982   #ffffff
1  STOCK               ROOT             819982    #3498db
2  BOND                ROOT             300000    #2ecc71
3  CASH                ROOT             350000    #f39c12
4  Technology          STOCK            347000    #3498db
5  Communication       STOCK            88000     #3498db
6  AAPL                Technology       47205     #85c1e9
7  MSFT                Technology       42860     #85c1e9
8  NVDA                Technology       49190     #85c1e9
9  Fixed Income        BOND             300000    #2ecc71
10 TLT                 Fixed Income     300000    #82e0aa
11 Cash & Equivalents  CASH             350000    #f39c12
12 일반적금             Cash & Equivalents 300000  #f8c471
...
```

### 3.3 종목 검색 기능 (킬러 기능)

**컴포넌트**: `st.text_input()` + `st.metric()`

```python
def render_stock_search(selected_month: str):
    """종목 검색 섹션"""

    st.subheader("🔍 종목 검색")

    # 검색 입력
    search_ticker = st.text_input(
        "종목 코드 입력",
        placeholder="예: AAPL, NVDA, 005930.KS",
        help="직접 보유 + ETF 내 간접 보유를 모두 검색합니다"
    )

    if not search_ticker:
        st.info("종목 코드를 입력하면 직접 보유와 ETF를 통한 간접 보유를 모두 확인할 수 있습니다.")
        return

    # 검색 실행
    with st.spinner(f"{search_ticker} 검색 중..."):
        result = search_total_holdings(selected_month, search_ticker.strip().upper())

    if not result:
        st.warning(f"'{search_ticker}' 종목을 찾을 수 없습니다.")
        return

    # 결과 표시
    st.success(f"📊 검색 결과: {result['ticker']} ({result['name']})")

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "💼 직접 보유",
            f"{result['direct_shares']:.2f}주",
            delta=f"{result['direct_value']:,}원"
        )

    with col2:
        st.metric(
            "📦 ETF 통해",
            f"{result['etf_shares']:.2f}주",
            delta=f"{result['etf_value']:,}원"
        )

    # ETF별 상세 내역
    if result['etf_details']:
        st.caption("ETF별 상세 내역:")
        for etf_name, shares, value in result['etf_details']:
            st.caption(f"  • {etf_name}에서: {shares:.2f}주 ({value:,}원)")

    st.divider()

    # 총계
    st.metric(
        "✅ 총 보유",
        f"{result['total_shares']:.2f}주",
        delta=f"{result['total_value']:,}원"
    )
```

**데이터 구조** (`result`):
```python
{
    'ticker': 'AAPL',
    'name': 'Apple Inc.',
    'direct_shares': 10.0,        # 직접 보유 수량
    'direct_value': 150000,       # 직접 보유 금액
    'etf_shares': 3.5,            # ETF 통해 보유 수량
    'etf_value': 52500,           # ETF 통해 보유 금액
    'etf_details': [              # ETF별 상세
        ('SPY', 2.0, 30000),
        ('QQQ', 1.5, 22500)
    ],
    'total_shares': 13.5,         # 총 보유 수량
    'total_value': 202500         # 총 보유 금액
}
```

### 3.4 통합 섹터 비중 (Horizontal Bar Chart)

**컴포넌트**: `plotly.graph_objects.Bar`

```python
import plotly.graph_objects as go

def create_sector_bar_chart(selected_month: str, top_n: int = 10):
    """
    통합 섹터 비중 Horizontal Bar Chart
    """
    # 데이터 조회
    df_sectors = get_total_sectors(selected_month, top_n=top_n)

    fig = go.Figure(go.Bar(
        x=df_sectors['amount'],
        y=df_sectors['sector_name'],
        orientation='h',
        text=[f"{pct:.1f}% ({amt:,}원)" for pct, amt in zip(df_sectors['percent'], df_sectors['amount'])],
        textposition='outside',
        marker=dict(
            color=df_sectors['amount'],
            colorscale='Blues',
            showscale=False
        )
    ))

    fig.update_layout(
        title=f"📊 통합 섹터 비중 (Top {top_n})",
        xaxis_title="금액 (원)",
        yaxis_title="",
        xaxis_tickformat=",",
        height=400,
        yaxis={'categoryorder': 'total ascending'}  # 금액 순 정렬
    )

    return fig

# 렌더링
st.subheader("📊 통합 섹터 비중")
fig = create_sector_bar_chart(selected_month, top_n=10)
st.plotly_chart(fig, use_container_width=True)
```

### 3.5 Top 20 보유 종목 테이블

**컴포넌트**: `st.dataframe()`

```python
def render_top_holdings(selected_month: str, top_n: int = 20):
    """상위 보유 종목 테이블"""

    st.subheader(f"🏅 통합 보유 종목 Top {top_n}")

    # 데이터 조회
    df = get_total_top_holdings(selected_month, top_n=top_n)

    # 포맷팅
    df_display = df.copy()
    df_display['순위'] = range(1, len(df) + 1)
    df_display['금액'] = df_display['amount'].apply(lambda x: f"{x:,}원")
    df_display['비중'] = df_display['percent'].apply(lambda x: f"{x:.1f}%")

    # 테이블 표시
    st.dataframe(
        df_display[['순위', '종목', '유형', '금액', '비중', '출처']],
        use_container_width=True,
        hide_index=True
    )

    st.caption("💡 ETF 내부 종목은 [출처] 컬럼에 ETF 이름이 표시됩니다.")
```

**데이터 구조** (`df`):
```python
   종목        유형   amount   percent  출처
0  일반적금    CASH   300000   20.4     ISA
1  TLT        BOND   300000   20.4     ISA
2  삼성전자   STOCK  150000   10.2     일반
3  NVDA       STOCK   49190    3.3     SPY,QQQ
4  AAPL       STOCK   47205    3.2     SPY,QQQ
...
```

## 4. 데이터 요구사항

### 4.1 필요한 함수 (`data_loader.py`)

```python
@st.cache_data(ttl=3600)
def get_asset_type_summary(year_month: str) -> dict:
    """
    자산 유형별 요약

    Returns:
        {'STOCK': int, 'BOND': int, 'CASH': int}
    """
    pass

@st.cache_data(ttl=3600)
def get_hierarchical_portfolio_data(year_month: str) -> pd.DataFrame:
    """
    Sunburst 차트용 계층 데이터

    Columns: ['labels', 'parents', 'values', 'colors']
    """
    pass

@st.cache_data(ttl=3600)
def search_total_holdings(year_month: str, ticker: str) -> dict:
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
    pass

@st.cache_data(ttl=3600)
def get_total_sectors(year_month: str, top_n: int = 10) -> pd.DataFrame:
    """
    통합 섹터 비중 (Top N)

    Columns: ['sector_name', 'amount', 'percent']
    """
    pass

@st.cache_data(ttl=3600)
def get_total_top_holdings(year_month: str, top_n: int = 20) -> pd.DataFrame:
    """
    통합 보유 종목 Top N

    Columns: ['종목', '유형', 'amount', 'percent', '출처']
    """
    pass
```

### 4.2 DB 쿼리 로직

```sql
-- 자산 유형별 요약
SELECT
    asset_type,
    SUM(my_amount) as total_amount
FROM analyzed_holdings
WHERE month_id = (SELECT id FROM months WHERE year_month = '2025-12')
  AND account_id IS NULL
GROUP BY asset_type;

-- 통합 섹터 비중
SELECT
    sector_name,
    SUM(my_amount) as amount,
    SUM(my_amount) * 100.0 / (SELECT SUM(my_amount) FROM analyzed_holdings WHERE ...) as percent
FROM analyzed_sectors
WHERE month_id = (SELECT id FROM months WHERE year_month = '2025-12')
  AND account_id IS NULL
GROUP BY sector_name
ORDER BY amount DESC
LIMIT 10;

-- 종목 검색 (직접 보유)
SELECT SUM(amount) as direct_value
FROM holdings
WHERE ticker_mapping = 'AAPL' AND ...;

-- 종목 검색 (ETF 통해)
SELECT
    source_ticker,
    SUM(my_amount) as etf_value
FROM analyzed_holdings
WHERE stock_symbol = 'AAPL' AND ...
GROUP BY source_ticker;
```

## 5. 인터랙션 및 UX

### 5.1 Sunburst 드릴다운

```python
# Plotly Sunburst는 기본적으로 클릭 시 드릴다운 지원
# 클릭하면 해당 노드가 중심으로 확대됨
# 다시 중심을 클릭하면 상위로 돌아감
```

### 5.2 검색어 자동 대문자 변환

```python
search_ticker = st.text_input("종목 코드 입력")
if search_ticker:
    search_ticker = search_ticker.strip().upper()  # 자동 대문자 변환
```

### 5.3 로딩 인디케이터

```python
with st.spinner("데이터 로딩 중..."):
    df = get_total_top_holdings(selected_month)
```

## 6. 에러 처리

### 6.1 데이터 없음

```python
df = get_total_top_holdings(selected_month)

if df.empty:
    st.warning("데이터가 없습니다.")
    st.stop()
```

### 6.2 검색 결과 없음

```python
result = search_total_holdings(selected_month, ticker)

if not result:
    st.warning(f"'{ticker}' 종목을 찾을 수 없습니다.")
```

## 7. 완성 코드 스케치

```python
# streamlit_app/pages/total_portfolio.py

import streamlit as st
import plotly.graph_objects as go
from streamlit_app.data_loader import (
    get_asset_type_summary,
    get_hierarchical_portfolio_data,
    search_total_holdings,
    get_total_sectors,
    get_total_top_holdings
)

def render(selected_month: str):
    """전체 포트폴리오 페이지 렌더링"""

    st.header(f"🏆 전체 포트폴리오 - {selected_month}")

    # 1. 자산 유형별 요약
    render_asset_type_summary(selected_month)
    st.divider()

    # 2. Sunburst Chart
    render_sunburst_chart(selected_month)
    st.divider()

    # 3. 종목 검색
    render_stock_search(selected_month)
    st.divider()

    # 4. 통합 섹터 비중
    render_sector_chart(selected_month)
    st.divider()

    # 5. Top 20 Holdings
    render_top_holdings(selected_month)


def render_asset_type_summary(selected_month: str):
    """자산 유형별 요약"""
    summary = get_asset_type_summary(selected_month)
    total = sum(summary.values())

    st.subheader("💰 자산 유형별 요약")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("📈 주식형", f"{summary['STOCK']:,}원",
                  delta=f"{summary['STOCK']/total*100:.1f}%")

    with col2:
        st.metric("💵 채권형", f"{summary['BOND']:,}원",
                  delta=f"{summary['BOND']/total*100:.1f}%")

    with col3:
        st.metric("💰 현금형", f"{summary['CASH']:,}원",
                  delta=f"{summary['CASH']/total*100:.1f}%")


def render_sunburst_chart(selected_month: str):
    """Sunburst 차트"""
    st.subheader("🌞 자산 구성")

    with st.spinner("차트 생성 중..."):
        fig = create_sunburst_chart(selected_month)

    st.plotly_chart(fig, use_container_width=True)
    st.caption("💡 차트를 클릭하면 세부 항목으로 드릴다운할 수 있습니다.")


def render_stock_search(selected_month: str):
    """종목 검색"""
    st.subheader("🔍 종목 검색")

    search_ticker = st.text_input("종목 코드 입력", placeholder="예: AAPL")

    if not search_ticker:
        st.info("종목 코드를 입력하세요.")
        return

    result = search_total_holdings(selected_month, search_ticker.upper())

    if not result:
        st.warning(f"'{search_ticker}' 종목을 찾을 수 없습니다.")
        return

    st.success(f"📊 {result['ticker']} ({result['name']})")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("💼 직접", f"{result['direct_shares']:.2f}주",
                  delta=f"{result['direct_value']:,}원")
    with col2:
        st.metric("📦 ETF", f"{result['etf_shares']:.2f}주",
                  delta=f"{result['etf_value']:,}원")

    st.metric("✅ 총계", f"{result['total_shares']:.2f}주",
              delta=f"{result['total_value']:,}원")


def render_sector_chart(selected_month: str):
    """섹터 차트"""
    st.subheader("📊 통합 섹터 비중")
    fig = create_sector_bar_chart(selected_month)
    st.plotly_chart(fig, use_container_width=True)


def render_top_holdings(selected_month: str):
    """Top 20 Holdings"""
    st.subheader("🏅 Top 20 보유 종목")

    df = get_total_top_holdings(selected_month, top_n=20)

    df_display = df.copy()
    df_display['순위'] = range(1, len(df) + 1)
    df_display['금액'] = df_display['amount'].apply(lambda x: f"{x:,}원")
    df_display['비중'] = df_display['percent'].apply(lambda x: f"{x:.1f}%")

    st.dataframe(df_display[['순위', '종목', '유형', '금액', '비중', '출처']],
                 use_container_width=True, hide_index=True)

    st.caption("💡 ETF 내부 종목은 [출처]에 표시됩니다.")
```
