# 계좌별 포트폴리오 페이지 UI 디자인

## 1. 페이지 개요

**목적**: 각 계좌별로 보유 종목을 확인하고, ETF 투시 기능으로 내부 구성 종목 분석

**주요 기능**:
- 계좌별 접기/펼치기 (Expander)
- 탭 분리: 보유 종목 vs ETF 투시
- ETF 투시는 토글 버튼으로 활성화
- 섹터 비중 파이 차트
- Top 10 제한으로 성능 최적화

## 2. 레이아웃 구조

```
┌────────────────────────────────────────────────────────────────┐
│  🏦 계좌별 포트폴리오 - 2025-12                                   │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  📌 투자 (절세) - ISA | 토스증권 | 총 800,000원               ▼│
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                                                          │ │
│  │  [보유 종목] [ETF 투시 분석]                              │ │
│  │  ─────────  ──────────────                              │ │
│  │                                                          │ │
│  │  📊 보유 종목 리스트                                      │ │
│  │  ┌────────────────────────────────────────────────────┐ │ │
│  │  │ 종목명          │ 티커 │ 금액     │ 비중   │ 유형  │ │ │
│  │  ├────────────────┼──────┼──────────┼────────┼───────┤ │ │
│  │  │ ACE 미국 S&P500│ SPY  │ 300,000원│ 37.5%  │ STOCK │ │ │
│  │  │ ACE 미국국채30년│ TLT  │ 200,000원│ 25.0%  │ BOND  │ │ │
│  │  │ 일반적금        │ CASH │ 300,000원│ 37.5%  │ CASH  │ │ │
│  │  └────────────────┴──────┴──────────┴────────┴───────┘ │ │
│  │                                                          │ │
│  │  📊 섹터 비중 (Pie Chart)                                │ │
│  │  ┌────────────────────────────────────────────────────┐ │ │
│  │  │           ╱──────╲                                 │ │ │
│  │  │         ╱          ╲                               │ │ │
│  │  │        │ Technology │  37.5%                       │ │ │
│  │  │        │   37.5%    │                              │ │ │
│  │  │         ╲          ╱                               │ │ │
│  │  │    CASH  ╲───────╱  Fixed Income                   │ │ │
│  │  │    37.5%              25.0%                        │ │ │
│  │  └────────────────────────────────────────────────────┘ │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  📌 연금저축 - IRP | 신한투자증권 | 총 500,000원              ▼│
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                                                          │ │
│  │  [보유 종목] [ETF 투시 분석]                              │ │
│  │             ──────────────                              │ │
│  │                                                          │ │
│  │  🔍 ETF 투시 활성화: [  OFF  ]  ← 토글 버튼              │ │
│  │                                                          │ │
│  │  ℹ️ ETF 투시를 활성화하면 ETF 내부 구성 종목을 확인할 수   │ │
│  │     있습니다.                                            │ │
│  │                                                          │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  📌 연금저축 - IRP (ETF 투시 활성화 시)                       ▼│
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                                                          │ │
│  │  [보유 종목] [ETF 투시 분석]                              │ │
│  │             ──────────────                              │ │
│  │                                                          │ │
│  │  🔍 ETF 투시 활성화: [  ON   ]  ← 토글 버튼              │ │
│  │                                                          │ │
│  │  🔎 ETF 내부 구성 종목 (Top 10)                          │ │
│  │  ┌────────────────────────────────────────────────────┐ │ │
│  │  │ 종목    │ 비중   │ 내 보유 금액 │ 출처 ETF         │ │ │
│  │  ├─────────┼────────┼──────────────┼──────────────────┤ │ │
│  │  │ AAPL    │ 7.2%   │ 36,000원     │ SPY              │ │ │
│  │  │ MSFT    │ 6.5%   │ 32,500원     │ SPY              │ │ │
│  │  │ NVDA    │ 5.8%   │ 29,000원     │ SPY              │ │ │
│  │  │ GOOGL   │ 4.2%   │ 21,000원     │ SPY              │ │ │
│  │  │ ...     │ ...    │ ...          │ ...              │ │ │
│  │  │ OTHER   │ 50.0%  │ 250,000원    │ SPY              │ │ │
│  │  └─────────┴────────┴──────────────┴──────────────────┘ │ │
│  │                                                          │ │
│  │  ⚠️ ETF 내 상위 10개 종목만 표시됩니다.                    │ │
│  │     나머지 종목은 'OTHER'로 합산되었습니다.               │ │
│  │                                                          │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

## 3. 컴포넌트 상세 설계

### 3.1 계좌 Expander

**컴포넌트**: `st.expander()`

```python
def render(selected_month: str):
    """계좌별 포트폴리오 페이지 렌더링"""

    st.header(f"🏦 계좌별 포트폴리오 - {selected_month}")

    # 계좌 목록 조회
    accounts = get_accounts(selected_month)

    if not accounts:
        st.warning("이 달에는 계좌 데이터가 없습니다.")
        return

    # 각 계좌별로 Expander 생성
    for account in accounts:
        # 계좌 헤더
        header = f"📌 {account['name']} - {account['type']} | {account['broker']} | 총 {account['total_value']:,}원"

        with st.expander(header, expanded=True):  # 첫 번째는 자동 펼침
            render_account_details(selected_month, account)
```

**데이터 구조** (`accounts`):
```python
[
    {
        'id': 1,
        'name': '투자 (절세)',
        'type': 'ISA',
        'broker': '토스증권',
        'fee': 0.0015,
        'total_value': 800000
    },
    ...
]
```

### 3.2 탭 구조 (보유 종목 vs ETF 투시)

**컴포넌트**: `st.tabs()`

```python
def render_account_details(selected_month: str, account: dict):
    """계좌 상세 정보 렌더링"""

    # 탭 생성
    tab1, tab2 = st.tabs(["보유 종목", "ETF 투시 분석"])

    with tab1:
        render_holdings_tab(selected_month, account)

    with tab2:
        render_etf_lookthrough_tab(selected_month, account)
```

### 3.3 보유 종목 탭

**컴포넌트**: `st.dataframe()` + `plotly.graph_objects.Pie`

```python
def render_holdings_tab(selected_month: str, account: dict):
    """보유 종목 탭 렌더링"""

    # 보유 종목 데이터 조회
    df_holdings = get_account_holdings(selected_month, account['id'])

    # 테이블 표시
    st.subheader("📊 보유 종목 리스트")

    # 데이터프레임 포맷팅
    df_display = df_holdings.copy()
    df_display['금액'] = df_display['amount'].apply(lambda x: f"{x:,}원")
    df_display['비중'] = df_display['ratio'].apply(lambda x: f"{x:.1f}%")

    st.dataframe(
        df_display[['종목명', '티커', '금액', '비중', '자산유형']],
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    # 섹터 비중 차트
    st.subheader("📊 섹터 비중")

    # 섹터 데이터 조회
    df_sectors = get_account_sectors(selected_month, account['id'])

    if not df_sectors.empty:
        fig = create_sector_pie_chart(df_sectors)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("섹터 데이터가 없습니다.")
```

**Sector Pie Chart 구현**:
```python
import plotly.graph_objects as go

def create_sector_pie_chart(df_sectors: pd.DataFrame):
    """
    섹터 비중 파이 차트 생성
    """
    fig = go.Figure(data=[go.Pie(
        labels=df_sectors['sector_name'],
        values=df_sectors['amount'],
        textinfo='label+percent',
        textposition='inside',
        marker=dict(
            colors=['#3498db', '#2ecc71', '#f39c12', '#e74c3c', '#9b59b6'],
            line=dict(color='white', width=2)
        )
    )])

    fig.update_layout(
        title="섹터별 자산 분포",
        height=400,
        showlegend=True
    )

    return fig
```

### 3.4 ETF 투시 탭 (핵심 기능)

**컴포넌트**: `st.toggle()` + `st.dataframe()`

```python
def render_etf_lookthrough_tab(selected_month: str, account: dict):
    """ETF 투시 탭 렌더링"""

    # 토글 버튼 (unique key 필요)
    lookthrough_enabled = st.toggle(
        "🔍 ETF 투시 활성화",
        value=False,
        key=f"lookthrough_toggle_{account['id']}",
        help="ETF 내부 구성 종목을 확인합니다 (상위 10개만 표시)"
    )

    if not lookthrough_enabled:
        st.info("💡 ETF 투시를 활성화하면 ETF 내부 구성 종목을 확인할 수 있습니다.")
        return

    # ETF 투시 데이터 로딩
    with st.spinner("ETF 구성 종목 분석 중..."):
        df_lookthrough = get_etf_lookthrough(selected_month, account['id'], top_n=10)

    if df_lookthrough.empty:
        st.warning("이 계좌에는 ETF가 없거나 분석 데이터가 없습니다.")
        return

    # 테이블 표시
    st.subheader("🔎 ETF 내부 구성 종목 (Top 10)")

    # 포맷팅
    df_display = df_lookthrough.copy()
    df_display['비중'] = df_display['holding_percent'].apply(lambda x: f"{x:.1f}%")
    df_display['내 보유 금액'] = df_display['my_amount'].apply(lambda x: f"{x:,}원")

    st.dataframe(
        df_display[['종목', '비중', '내 보유 금액', '출처 ETF']],
        use_container_width=True,
        hide_index=True
    )

    # 경고 메시지
    st.caption("⚠️ ETF 내 상위 10개 종목만 표시됩니다. 나머지 종목은 'OTHER'로 합산되었습니다.")
```

**데이터 구조** (`df_lookthrough`):
```python
   종목    비중(%)  내보유금액   출처ETF
0  AAPL    7.2     36000      SPY
1  MSFT    6.5     32500      SPY
2  NVDA    5.8     29000      SPY
3  GOOGL   4.2     21000      SPY
...
9  OTHER   50.0    250000     SPY
```

## 4. 데이터 요구사항

### 4.1 필요한 함수 (`data_loader.py`)

```python
@st.cache_data(ttl=3600)
def get_accounts(year_month: str) -> List[dict]:
    """
    해당 월의 모든 계좌 조회

    Returns:
        [
            {
                'id': int,
                'name': str,
                'type': str,
                'broker': str,
                'fee': float,
                'total_value': int
            },
            ...
        ]
    """
    pass

@st.cache_data(ttl=3600)
def get_account_holdings(year_month: str, account_id: int) -> pd.DataFrame:
    """
    계좌별 보유 종목 조회

    Columns: ['종목명', '티커', 'amount', 'ratio', '자산유형']
    """
    pass

@st.cache_data(ttl=3600)
def get_account_sectors(year_month: str, account_id: int) -> pd.DataFrame:
    """
    계좌별 섹터 비중 조회

    Columns: ['sector_name', 'amount', 'percent']
    """
    pass

@st.cache_data(ttl=86400)  # 24시간 캐싱 (ETF 데이터는 자주 안 바뀜)
def get_etf_lookthrough(year_month: str, account_id: int, top_n: int = 10) -> pd.DataFrame:
    """
    ETF 투시 데이터 조회 (Top N만)

    Columns: ['종목', 'holding_percent', 'my_amount', '출처 ETF']
    """
    pass
```

### 4.2 DB 쿼리 로직

```sql
-- 계좌 목록 조회
SELECT
    a.id,
    a.name,
    a.type,
    a.broker,
    a.fee,
    SUM(h.amount) as total_value
FROM accounts a
JOIN holdings h ON a.id = h.account_id
WHERE a.month_id = (SELECT id FROM months WHERE year_month = '2025-12')
GROUP BY a.id;

-- 계좌별 보유 종목
SELECT
    h.name as 종목명,
    h.ticker_mapping as 티커,
    h.amount,
    h.target_ratio as ratio,
    h.asset_type as 자산유형
FROM holdings h
WHERE h.account_id = 1;

-- 계좌별 섹터 비중
SELECT
    sector_name,
    SUM(my_amount) as amount,
    SUM(sector_percent) as percent
FROM analyzed_sectors
WHERE account_id = 1 AND month_id = (SELECT id FROM months WHERE year_month = '2025-12')
GROUP BY sector_name
ORDER BY amount DESC;

-- ETF 투시 (Top 10)
SELECT
    stock_symbol as 종목,
    holding_percent,
    my_amount,
    source_ticker as 출처ETF
FROM analyzed_holdings
WHERE account_id = 1
  AND month_id = (SELECT id FROM months WHERE year_month = '2025-12')
  AND asset_type = 'STOCK'
ORDER BY my_amount DESC
LIMIT 10;
```

## 5. 성능 최적화 전략

### 5.1 캐싱 전략

```python
# ETF 투시 데이터는 24시간 캐싱 (데이터 변경 빈도 낮음)
@st.cache_data(ttl=86400)
def get_etf_lookthrough(...):
    pass

# 계좌/보유종목 데이터는 1시간 캐싱
@st.cache_data(ttl=3600)
def get_account_holdings(...):
    pass
```

### 5.2 Top N 제한

```python
# 기본 10개로 제한
def get_etf_lookthrough(year_month: str, account_id: int, top_n: int = 10):
    """
    상위 N개만 조회하여 스크롤 최소화
    나머지는 'OTHER'로 합산
    """
    pass
```

### 5.3 Lazy Loading (토글 활성화 시에만 로딩)

```python
# ETF 투시는 토글이 켜질 때만 데이터 로딩
if lookthrough_enabled:
    df = get_etf_lookthrough(...)  # 이때만 DB 쿼리 실행
else:
    # 로딩하지 않음 -> 성능 향상
    pass
```

## 6. 에러 처리

### 6.1 계좌 없음

```python
accounts = get_accounts(selected_month)

if not accounts:
    st.warning(f"⚠️ {selected_month}에는 계좌 데이터가 없습니다.")
    st.stop()
```

### 6.2 ETF 데이터 없음

```python
df_lookthrough = get_etf_lookthrough(selected_month, account_id)

if df_lookthrough.empty:
    st.info("이 계좌에는 ETF가 없거나 분석 데이터가 없습니다.")
```

### 6.3 차트 렌더링 실패

```python
try:
    fig = create_sector_pie_chart(df_sectors)
    st.plotly_chart(fig)
except Exception as e:
    st.error(f"차트 생성 실패: {e}")
    # 테이블로 대체
    st.table(df_sectors)
```

## 7. 완성 코드 스케치

```python
# streamlit_app/pages/account_portfolio.py

import streamlit as st
import plotly.graph_objects as go
from streamlit_app.data_loader import (
    get_accounts,
    get_account_holdings,
    get_account_sectors,
    get_etf_lookthrough
)

def render(selected_month: str):
    """계좌별 포트폴리오 페이지 렌더링"""

    st.header(f"🏦 계좌별 포트폴리오 - {selected_month}")

    # 계좌 목록 조회
    with st.spinner("계좌 데이터 로딩 중..."):
        accounts = get_accounts(selected_month)

    if not accounts:
        st.warning(f"⚠️ {selected_month}에는 계좌 데이터가 없습니다.")
        st.stop()

    # 각 계좌별 Expander
    for idx, account in enumerate(accounts):
        header = f"📌 {account['name']} - {account['type']} | {account['broker']} | 총 {account['total_value']:,}원"

        with st.expander(header, expanded=(idx == 0)):  # 첫 번째만 펼침
            render_account_details(selected_month, account)


def render_account_details(selected_month: str, account: dict):
    """계좌 상세 정보 렌더링"""

    tab1, tab2 = st.tabs(["보유 종목", "ETF 투시 분석"])

    with tab1:
        render_holdings_tab(selected_month, account)

    with tab2:
        render_etf_lookthrough_tab(selected_month, account)


def render_holdings_tab(selected_month: str, account: dict):
    """보유 종목 탭"""

    df = get_account_holdings(selected_month, account['id'])

    st.subheader("📊 보유 종목 리스트")
    # 포맷팅 후 표시
    df_display = df.copy()
    df_display['금액'] = df_display['amount'].apply(lambda x: f"{x:,}원")
    df_display['비중'] = df_display['ratio'].apply(lambda x: f"{x:.1f}%")

    st.dataframe(df_display[['종목명', '티커', '금액', '비중', '자산유형']], use_container_width=True, hide_index=True)

    st.divider()

    st.subheader("📊 섹터 비중")
    df_sectors = get_account_sectors(selected_month, account['id'])

    if not df_sectors.empty:
        fig = create_sector_pie_chart(df_sectors)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("섹터 데이터가 없습니다.")


def render_etf_lookthrough_tab(selected_month: str, account: dict):
    """ETF 투시 탭"""

    lookthrough_enabled = st.toggle(
        "🔍 ETF 투시 활성화",
        value=False,
        key=f"lookthrough_{account['id']}",
        help="ETF 내부 구성 종목 확인 (Top 10)"
    )

    if not lookthrough_enabled:
        st.info("💡 ETF 투시를 활성화하면 ETF 내부 구성 종목을 확인할 수 있습니다.")
        return

    with st.spinner("ETF 분석 중..."):
        df = get_etf_lookthrough(selected_month, account['id'], top_n=10)

    if df.empty:
        st.warning("ETF 데이터가 없습니다.")
        return

    st.subheader("🔎 ETF 내부 구성 종목 (Top 10)")

    df_display = df.copy()
    df_display['비중'] = df_display['holding_percent'].apply(lambda x: f"{x:.1f}%")
    df_display['내 보유 금액'] = df_display['my_amount'].apply(lambda x: f"{x:,}원")

    st.dataframe(df_display[['종목', '비중', '내 보유 금액', '출처 ETF']], use_container_width=True, hide_index=True)
    st.caption("⚠️ 상위 10개 종목만 표시됩니다.")


def create_sector_pie_chart(df_sectors):
    """섹터 파이 차트"""
    fig = go.Figure(data=[go.Pie(
        labels=df_sectors['sector_name'],
        values=df_sectors['amount'],
        textinfo='label+percent',
        marker=dict(line=dict(color='white', width=2))
    )])

    fig.update_layout(title="섹터별 자산 분포", height=400)
    return fig
```
