# 월별 투자 비교 페이지 UI 디자인

## 1. 페이지 개요

**목적**: 이번 달과 저번 달의 투자 성과를 비교하여 자산 변동 내역을 시각화

**주요 기능**:
- 총 자산, 원금, 수익금, 수익률 한눈에 보기
- 전월 대비 증감 표시
- 자산 변동 워터폴 차트
- 월별 히스토리 테이블

## 2. 레이아웃 구조

```
┌────────────────────────────────────────────────────────────────┐
│  📅 월별 투자 비교 - 2025-12                                     │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │ 💰 총자산 │  │ 💵 총원금 │  │ 📈 총수익 │  │ 📊 수익률 │      │
│  │          │  │          │  │          │  │          │      │
│  │ 1,469,982│  │ 1,400,000│  │  +69,982 │  │  +5.0%   │      │
│  │   원     │  │   원     │  │   원     │  │          │      │
│  │          │  │          │  │          │  │          │      │
│  │ ↑ 50,000 │  │ ↑ 100,000│  │ ↑ 15,000 │  │ ↑ 1.2%   │      │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘      │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  💧 자산 변동 내역 (Waterfall Chart)                             │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │        │                                                 │ │
│  │ 1.5M   │  ┌──┐                           ┌──┐           │ │
│  │        │  │  │       ┌─────┐             │  │           │ │
│  │ 1.0M   │  │  │       │ +입금│             │금월│          │ │
│  │        │  │전월│───────┤     ├───┬───┐    │자산│          │ │
│  │ 0.5M   │  │자산│       └─────┘   │손익│────┤   │          │ │
│  │        │  │  │                   └───┘    │   │          │ │
│  │   0    └──┴──┴───────────────────────────┴───┴──────────│ │
│  │          [1.32M] [+100K]  [1.42M] [+50K]   [1.47M]      │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  📊 월별 지표 비교                                               │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ 월       │ 총자산    │ 총원금    │ 총수익    │ 수익률    │ │
│  ├──────────┼───────────┼───────────┼───────────┼───────────┤ │
│  │ 2025-12  │ 1,469,982 │ 1,400,000 │  +69,982  │  +5.0%   │ │
│  │ 2025-11  │ 1,319,982 │ 1,300,000 │  +19,982  │  +1.5%   │ │
│  │ 2025-10  │      -    │      -    │      -    │     -    │ │
│  └──────────┴───────────┴───────────┴───────────┴───────────┘ │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  📈 자산 추이 (Line Chart) - 2개월 이상 데이터 필요               │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ 1.5M │                                         ●─────●   │ │
│  │      │                                       ●            │ │
│  │ 1.0M │                                     ●              │ │
│  │      │                                   ●                │ │
│  │ 0.5M │                                 ●                  │ │
│  │      │                               ●                    │ │
│  │   0  └─────┬─────┬─────┬─────┬─────┬─────┬─────┬────────│ │
│  │          09월  10월  11월  12월  01월  02월  03월         │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

## 3. 컴포넌트 상세 설계

### 3.1 Metric Cards (4개)

**컴포넌트**: `st.metric()`

```python
# 데이터 로딩
current_month_data = get_monthly_summary(selected_month)
previous_month_data = get_monthly_summary(get_previous_month(selected_month))

# 증감 계산
delta_total_value = current_month_data['total_value'] - previous_month_data['total_value']
delta_total_invested = current_month_data['total_invested'] - previous_month_data['total_invested']
delta_total_profit = current_month_data['total_profit'] - previous_month_data['total_profit']
delta_return_rate = current_month_data['return_rate'] - previous_month_data['return_rate']

# UI 렌더링
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="💰 총 자산",
        value=f"{current_month_data['total_value']:,}원",
        delta=f"{delta_total_value:+,}원"
    )

with col2:
    st.metric(
        label="💵 총 원금",
        value=f"{current_month_data['total_invested']:,}원",
        delta=f"{delta_total_invested:+,}원"
    )

with col3:
    st.metric(
        label="📈 총 수익",
        value=f"{current_month_data['total_profit']:+,}원",
        delta=f"{delta_total_profit:+,}원"
    )

with col4:
    st.metric(
        label="📊 수익률",
        value=f"{current_month_data['return_rate']:+.1f}%",
        delta=f"{delta_return_rate:+.1f}%"
    )
```

**데이터 구조** (`monthly_summary`):
```python
{
    'total_value': 1469982,      # 총 자산 (평가액)
    'total_invested': 1400000,   # 총 원금
    'total_profit': 69982,       # 총 수익 (평가액 - 원금)
    'return_rate': 5.0           # 수익률 (%)
}
```

### 3.2 Waterfall Chart (자산 변동 내역)

**컴포넌트**: `plotly.graph_objects.Waterfall`

```python
import plotly.graph_objects as go

def create_waterfall_chart(selected_month: str):
    """
    [전월 자산] → [추가 입금] → [평가 손익] → [금월 자산]
    """
    # 데이터 준비
    prev_month = get_previous_month(selected_month)
    prev_data = get_monthly_summary(prev_month)
    curr_data = get_monthly_summary(selected_month)

    # 계산
    prev_value = prev_data['total_value']
    deposit = curr_data['total_invested'] - prev_data['total_invested']  # 추가 입금
    profit = (curr_data['total_value'] - curr_data['total_invested']) - \
             (prev_data['total_value'] - prev_data['total_invested'])  # 평가 손익 증감
    curr_value = curr_data['total_value']

    # Waterfall 차트
    fig = go.Figure(go.Waterfall(
        name="자산 변동",
        orientation="v",
        measure=["absolute", "relative", "relative", "total"],
        x=["전월 자산", "추가 입금", "평가 손익", "금월 자산"],
        y=[prev_value, deposit, profit, curr_value],
        text=[
            f"{prev_value:,}원",
            f"{deposit:+,}원",
            f"{profit:+,}원",
            f"{curr_value:,}원"
        ],
        textposition="outside",
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        increasing={"marker": {"color": "#27ae60"}},  # 증가: 녹색
        decreasing={"marker": {"color": "#e74c3c"}},  # 감소: 빨간색
        totals={"marker": {"color": "#3498db"}}       # 합계: 파란색
    ))

    fig.update_layout(
        title="💧 자산 변동 내역",
        showlegend=False,
        height=400,
        xaxis_title="",
        yaxis_title="금액 (원)",
        yaxis_tickformat=","
    )

    return fig

# 렌더링
st.subheader("💧 자산 변동 내역")
fig = create_waterfall_chart(selected_month)
st.plotly_chart(fig, use_container_width=True)
```

### 3.3 월별 비교 테이블

**컴포넌트**: `st.dataframe()`

```python
def get_month_comparison_table(selected_month: str, num_months: int = 3):
    """
    최근 N개월 데이터를 테이블로 반환
    """
    months = get_recent_months(num_months)

    data = []
    for month in months:
        summary = get_monthly_summary(month)
        data.append({
            '월': month,
            '총 자산': f"{summary['total_value']:,}원",
            '총 원금': f"{summary['total_invested']:,}원",
            '총 수익': f"{summary['total_profit']:+,}원",
            '수익률': f"{summary['return_rate']:+.1f}%"
        })

    return pd.DataFrame(data)

# 렌더링
st.subheader("📊 월별 지표 비교")
df = get_month_comparison_table(selected_month)
st.dataframe(df, use_container_width=True, hide_index=True)
```

### 3.4 자산 추이 차트 (선택사항)

**컴포넌트**: `plotly.graph_objects.Scatter`

```python
import plotly.graph_objects as go

def create_asset_trend_chart():
    """
    전체 월별 자산 추이 라인 차트
    """
    # 모든 월 데이터 조회
    all_months = get_all_months()

    if len(all_months) < 2:
        st.info("자산 추이 차트는 2개월 이상 데이터가 필요합니다.")
        return None

    months = []
    values = []

    for month in all_months:
        summary = get_monthly_summary(month)
        months.append(month)
        values.append(summary['total_value'])

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=months,
        y=values,
        mode='lines+markers',
        name='총 자산',
        line=dict(color='#3498db', width=3),
        marker=dict(size=10)
    ))

    fig.update_layout(
        title="📈 자산 추이",
        xaxis_title="월",
        yaxis_title="총 자산 (원)",
        yaxis_tickformat=",",
        height=400
    )

    return fig

# 렌더링
st.subheader("📈 자산 추이")
fig = create_asset_trend_chart()
if fig:
    st.plotly_chart(fig, use_container_width=True)
```

## 4. 데이터 요구사항

### 4.1 필요한 함수 (`data_loader.py`)

```python
@st.cache_data(ttl=3600)
def get_monthly_summary(year_month: str) -> dict:
    """
    월별 요약 데이터 반환

    Returns:
        {
            'total_value': int,      # 총 자산 (평가액)
            'total_invested': int,   # 총 원금
            'total_profit': int,     # 총 수익
            'return_rate': float     # 수익률 (%)
        }
    """
    pass

def get_previous_month(year_month: str) -> str:
    """
    이전 달 year_month 반환 (예: '2025-12' -> '2025-11')
    """
    pass

def get_recent_months(num_months: int) -> List[str]:
    """
    최근 N개월 리스트 반환 (내림차순)
    """
    pass

def get_all_months() -> List[str]:
    """
    DB에 있는 모든 월 리스트 반환 (오름차순)
    """
    pass
```

### 4.2 DB 쿼리 로직

```sql
-- 월별 총 자산 계산
SELECT
    SUM(h.amount) as total_invested,
    SUM(ah.my_amount) as total_value
FROM holdings h
JOIN analyzed_holdings ah ON h.id = ah.holding_id
WHERE h.account_id IN (
    SELECT id FROM accounts WHERE month_id = (
        SELECT id FROM months WHERE year_month = '2025-12'
    )
);

-- 총 수익 = 총 자산 - 총 원금
-- 수익률 = (총 수익 / 총 원금) * 100
```

## 5. 에러 처리

### 5.1 데이터 부족 시

```python
try:
    current_data = get_monthly_summary(selected_month)
except DataNotFoundError:
    st.error(f"❌ {selected_month} 데이터가 없습니다.")
    st.stop()

previous_month = get_previous_month(selected_month)
try:
    previous_data = get_monthly_summary(previous_month)
except DataNotFoundError:
    st.warning(f"⚠️ 전월({previous_month}) 데이터가 없어 비교가 불가능합니다.")
    # 전월 비교 없이 현재 월만 표시
    previous_data = None
```

### 5.2 차트 렌더링 실패 시

```python
try:
    fig = create_waterfall_chart(selected_month)
    st.plotly_chart(fig, use_container_width=True)
except Exception as e:
    st.error(f"차트 렌더링 실패: {e}")
    # 테이블 형식으로 대체 표시
    st.table(get_waterfall_data_as_table(selected_month))
```

## 6. 완성 코드 스케치

```python
# streamlit_app/pages/monthly_comparison.py

import streamlit as st
import plotly.graph_objects as go
from streamlit_app.data_loader import (
    get_monthly_summary,
    get_previous_month,
    get_recent_months,
    get_all_months
)

def render(selected_month: str):
    """월별 투자 비교 페이지 렌더링"""

    st.header(f"📅 월별 투자 비교 - {selected_month}")

    # 데이터 로딩
    with st.spinner("데이터 로딩 중..."):
        current_data = get_monthly_summary(selected_month)

        previous_month = get_previous_month(selected_month)
        try:
            previous_data = get_monthly_summary(previous_month)
        except:
            previous_data = None
            st.warning(f"⚠️ 전월 데이터가 없습니다.")

    # 1. Metric Cards
    col1, col2, col3, col4 = st.columns(4)

    delta_value = current_data['total_value'] - previous_data['total_value'] if previous_data else 0
    delta_invested = current_data['total_invested'] - previous_data['total_invested'] if previous_data else 0
    delta_profit = current_data['total_profit'] - previous_data['total_profit'] if previous_data else 0
    delta_rate = current_data['return_rate'] - previous_data['return_rate'] if previous_data else 0

    with col1:
        st.metric("💰 총 자산", f"{current_data['total_value']:,}원",
                  delta=f"{delta_value:+,}원" if previous_data else None)

    with col2:
        st.metric("💵 총 원금", f"{current_data['total_invested']:,}원",
                  delta=f"{delta_invested:+,}원" if previous_data else None)

    with col3:
        st.metric("📈 총 수익", f"{current_data['total_profit']:+,}원",
                  delta=f"{delta_profit:+,}원" if previous_data else None)

    with col4:
        st.metric("📊 수익률", f"{current_data['return_rate']:+.1f}%",
                  delta=f"{delta_rate:+.1f}%" if previous_data else None)

    st.divider()

    # 2. Waterfall Chart
    if previous_data:
        st.subheader("💧 자산 변동 내역")
        fig = create_waterfall_chart(selected_month, previous_data, current_data)
        st.plotly_chart(fig, use_container_width=True)
        st.divider()

    # 3. 월별 비교 테이블
    st.subheader("📊 월별 지표 비교")
    df = get_month_comparison_table(selected_month)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()

    # 4. 자산 추이 차트
    st.subheader("📈 자산 추이")
    fig = create_asset_trend_chart()
    if fig:
        st.plotly_chart(fig, use_container_width=True)
```
