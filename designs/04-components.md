# 재사용 컴포넌트 및 유틸리티 디자인

## 1. 개요

**목적**: 중복 코드를 줄이고 일관된 UI를 제공하기 위한 재사용 가능한 컴포넌트 및 유틸리티 함수 설계

**구조**:
```
streamlit_app/
├── components/
│   ├── __init__.py
│   ├── metrics.py      # Metric Cards
│   ├── charts.py       # 차트 컴포넌트 (Plotly)
│   └── tables.py       # 테이블 컴포넌트
└── utils/
    ├── __init__.py
    ├── formatters.py   # 숫자/날짜 포맷팅
    └── state.py        # 상태 관리
```

---

## 2. 차트 컴포넌트 (`charts.py`)

### 2.1 Waterfall Chart

```python
import plotly.graph_objects as go

def create_waterfall_chart(
    categories: list,
    values: list,
    title: str = "Waterfall Chart",
    height: int = 400
) -> go.Figure:
    """
    Waterfall Chart 생성

    Args:
        categories: X축 카테고리 ['전월', '입금', '손익', '금월']
        values: Y축 값 [1320000, 100000, 50000, 1470000]
        title: 차트 제목
        height: 차트 높이

    Returns:
        Plotly Figure 객체
    """
    fig = go.Figure(go.Waterfall(
        name="",
        orientation="v",
        measure=["absolute", "relative", "relative", "total"],
        x=categories,
        y=values,
        text=[f"{v:,}원" for v in values],
        textposition="outside",
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        increasing={"marker": {"color": "#27ae60"}},
        decreasing={"marker": {"color": "#e74c3c"}},
        totals={"marker": {"color": "#3498db"}}
    ))

    fig.update_layout(
        title=title,
        showlegend=False,
        height=height,
        xaxis_title="",
        yaxis_title="금액 (원)",
        yaxis_tickformat=",",
        font=dict(size=12)
    )

    return fig
```

### 2.2 Sunburst Chart

```python
import plotly.graph_objects as go
import pandas as pd

def create_sunburst_chart(
    df: pd.DataFrame,
    title: str = "Sunburst Chart",
    height: int = 600
) -> go.Figure:
    """
    Sunburst Chart 생성 (계층적 데이터)

    Args:
        df: 계층 데이터프레임 (컬럼: labels, parents, values, colors)
        title: 차트 제목
        height: 차트 높이

    Returns:
        Plotly Figure 객체

    Example:
        df = pd.DataFrame({
            'labels': ['ROOT', 'STOCK', 'BOND', 'AAPL', 'TLT'],
            'parents': ['', 'ROOT', 'ROOT', 'STOCK', 'BOND'],
            'values': [1000000, 600000, 400000, 100000, 400000],
            'colors': ['#fff', '#3498db', '#2ecc71', '#85c1e9', '#82e0aa']
        })
    """
    fig = go.Figure(go.Sunburst(
        labels=df['labels'],
        parents=df['parents'],
        values=df['values'],
        branchvalues="total",
        marker=dict(
            colors=df['colors'],
            line=dict(color='white', width=2)
        ),
        hovertemplate='<b>%{label}</b><br>' +
                      '금액: %{value:,}원<br>' +
                      '비중: %{percentParent}<extra></extra>'
    ))

    fig.update_layout(
        title=title,
        height=height,
        margin=dict(t=50, l=0, r=0, b=0)
    )

    return fig
```

### 2.3 Pie Chart (섹터 비중)

```python
import plotly.graph_objects as go
import pandas as pd

def create_pie_chart(
    df: pd.DataFrame,
    labels_col: str = 'labels',
    values_col: str = 'values',
    title: str = "Pie Chart",
    height: int = 400,
    colors: list = None
) -> go.Figure:
    """
    Pie Chart 생성

    Args:
        df: 데이터프레임
        labels_col: 레이블 컬럼명
        values_col: 값 컬럼명
        title: 차트 제목
        height: 차트 높이
        colors: 커스텀 색상 리스트

    Returns:
        Plotly Figure 객체
    """
    default_colors = ['#3498db', '#2ecc71', '#f39c12', '#e74c3c', '#9b59b6',
                      '#1abc9c', '#34495e', '#e67e22', '#95a5a6', '#d35400']

    fig = go.Figure(data=[go.Pie(
        labels=df[labels_col],
        values=df[values_col],
        textinfo='label+percent',
        textposition='inside',
        marker=dict(
            colors=colors or default_colors,
            line=dict(color='white', width=2)
        )
    )])

    fig.update_layout(
        title=title,
        height=height,
        showlegend=True,
        legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.05)
    )

    return fig
```

### 2.4 Horizontal Bar Chart (섹터 비중)

```python
import plotly.graph_objects as go
import pandas as pd

def create_horizontal_bar_chart(
    df: pd.DataFrame,
    x_col: str = 'amount',
    y_col: str = 'sector',
    title: str = "Horizontal Bar Chart",
    height: int = 400,
    show_values: bool = True
) -> go.Figure:
    """
    Horizontal Bar Chart 생성

    Args:
        df: 데이터프레임
        x_col: X축 컬럼 (금액)
        y_col: Y축 컬럼 (카테고리)
        title: 차트 제목
        height: 차트 높이
        show_values: 값 표시 여부

    Returns:
        Plotly Figure 객체
    """
    # 값 표시 텍스트 생성
    if show_values and 'percent' in df.columns:
        text = [f"{pct:.1f}% ({amt:,}원)"
                for pct, amt in zip(df['percent'], df[x_col])]
    elif show_values:
        text = [f"{amt:,}원" for amt in df[x_col]]
    else:
        text = None

    fig = go.Figure(go.Bar(
        x=df[x_col],
        y=df[y_col],
        orientation='h',
        text=text,
        textposition='outside',
        marker=dict(
            color=df[x_col],
            colorscale='Blues',
            showscale=False
        )
    ))

    fig.update_layout(
        title=title,
        xaxis_title="금액 (원)",
        yaxis_title="",
        xaxis_tickformat=",",
        height=height,
        yaxis={'categoryorder': 'total ascending'},  # 금액 순 정렬
        font=dict(size=12)
    )

    return fig
```

### 2.5 Line Chart (자산 추이)

```python
import plotly.graph_objects as go
import pandas as pd

def create_line_chart(
    df: pd.DataFrame,
    x_col: str = 'month',
    y_col: str = 'value',
    title: str = "Line Chart",
    height: int = 400,
    line_color: str = '#3498db'
) -> go.Figure:
    """
    Line Chart 생성 (시계열 데이터)

    Args:
        df: 데이터프레임
        x_col: X축 컬럼 (날짜/월)
        y_col: Y축 컬럼 (값)
        title: 차트 제목
        height: 차트 높이
        line_color: 라인 색상

    Returns:
        Plotly Figure 객체
    """
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df[x_col],
        y=df[y_col],
        mode='lines+markers',
        name='총 자산',
        line=dict(color=line_color, width=3),
        marker=dict(size=10, color=line_color)
    ))

    fig.update_layout(
        title=title,
        xaxis_title="월",
        yaxis_title="금액 (원)",
        yaxis_tickformat=",",
        height=height,
        hovermode='x unified',
        font=dict(size=12)
    )

    return fig
```

---

## 3. 테이블 컴포넌트 (`tables.py`)

### 3.1 포맷팅된 데이터프레임

```python
import streamlit as st
import pandas as pd

def render_formatted_table(
    df: pd.DataFrame,
    format_config: dict = None,
    use_container_width: bool = True,
    hide_index: bool = True
):
    """
    포맷팅이 적용된 테이블 렌더링

    Args:
        df: 원본 데이터프레임
        format_config: 컬럼별 포맷 설정 {'amount': '{:,}원', 'ratio': '{:.1f}%'}
        use_container_width: 컨테이너 너비 사용 여부
        hide_index: 인덱스 숨김 여부

    Example:
        format_config = {
            'amount': lambda x: f"{x:,}원",
            'ratio': lambda x: f"{x:.1f}%"
        }
    """
    if format_config:
        styled_df = df.style.format(format_config)
        st.dataframe(styled_df, use_container_width=use_container_width, hide_index=hide_index)
    else:
        st.dataframe(df, use_container_width=use_container_width, hide_index=hide_index)
```

### 3.2 강조된 테이블 (상위 항목 하이라이트)

```python
import streamlit as st
import pandas as pd

def render_highlighted_table(
    df: pd.DataFrame,
    highlight_col: str,
    top_n: int = 3,
    highlight_color: str = 'lightgreen'
):
    """
    상위 N개 항목을 하이라이트한 테이블

    Args:
        df: 데이터프레임
        highlight_col: 하이라이트 기준 컬럼
        top_n: 상위 N개
        highlight_color: 하이라이트 색상
    """
    def highlight_top(s):
        is_top = s.nlargest(top_n).index
        return [f'background-color: {highlight_color}' if i in is_top else ''
                for i in range(len(s))]

    styled_df = df.style.apply(highlight_top, subset=[highlight_col])
    st.dataframe(styled_df, use_container_width=True)
```

---

## 4. 유틸리티 함수 (`formatters.py`)

### 4.1 숫자 포맷팅

```python
def format_currency(value: float, currency: str = '원') -> str:
    """
    금액 포맷팅 (천 단위 콤마)

    Args:
        value: 금액
        currency: 통화 단위

    Returns:
        포맷팅된 문자열 (예: '1,234,567원')
    """
    return f"{int(value):,}{currency}"


def format_percent(value: float, decimals: int = 1, include_sign: bool = False) -> str:
    """
    퍼센트 포맷팅

    Args:
        value: 퍼센트 값 (5.0 = 5%)
        decimals: 소수점 자릿수
        include_sign: +/- 부호 포함 여부

    Returns:
        포맷팅된 문자열 (예: '+5.0%', '5.0%')
    """
    if include_sign:
        return f"{value:+.{decimals}f}%"
    else:
        return f"{value:.{decimals}f}%"


def format_shares(value: float, decimals: int = 2) -> str:
    """
    주식 수량 포맷팅

    Args:
        value: 수량
        decimals: 소수점 자릿수

    Returns:
        포맷팅된 문자열 (예: '1.23주')
    """
    return f"{value:.{decimals}f}주"


def format_compact_number(value: float) -> str:
    """
    숫자 간략 표시 (K, M, B 단위)

    Args:
        value: 숫자

    Returns:
        간략 표시 (예: 1.2M, 500K)
    """
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}B"
    elif value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    elif value >= 1_000:
        return f"{value / 1_000:.1f}K"
    else:
        return f"{value:.0f}"
```

### 4.2 날짜 포맷팅

```python
from datetime import datetime

def format_year_month(year_month: str, format: str = '%Y년 %m월') -> str:
    """
    year_month 문자열 포맷팅

    Args:
        year_month: 'YYYY-MM' 형식
        format: strftime 포맷

    Returns:
        포맷팅된 문자열 (예: '2025년 12월')
    """
    try:
        dt = datetime.strptime(year_month, '%Y-%m')
        return dt.strftime(format)
    except:
        return year_month


def get_previous_month(year_month: str) -> str:
    """
    이전 달 year_month 반환

    Args:
        year_month: 'YYYY-MM'

    Returns:
        이전 달 'YYYY-MM' (예: '2025-12' -> '2025-11')
    """
    from datetime import datetime, timedelta

    dt = datetime.strptime(year_month, '%Y-%m')
    prev_dt = dt - timedelta(days=1)  # 1일 전으로 이동
    prev_month = prev_dt.replace(day=1)  # 그 달의 1일로
    return prev_month.strftime('%Y-%m')


def get_next_month(year_month: str) -> str:
    """
    다음 달 year_month 반환

    Args:
        year_month: 'YYYY-MM'

    Returns:
        다음 달 'YYYY-MM'
    """
    from datetime import datetime, timedelta
    from calendar import monthrange

    dt = datetime.strptime(year_month, '%Y-%m')
    last_day = monthrange(dt.year, dt.month)[1]
    next_dt = dt.replace(day=last_day) + timedelta(days=1)
    return next_dt.strftime('%Y-%m')
```

---

## 5. 상태 관리 (`state.py`)

### 5.1 세션 상태 초기화

```python
import streamlit as st

def init_session_state():
    """
    세션 상태 초기화
    """
    # 선택한 월 (기본: 최신 월)
    if 'selected_month' not in st.session_state:
        from streamlit_app.data_loader import get_latest_month
        st.session_state.selected_month = get_latest_month()

    # 선택한 페이지
    if 'selected_page' not in st.session_state:
        st.session_state.selected_page = "월별 투자 비교"

    # ETF 투시 활성화 상태 (계좌별)
    if 'etf_lookthrough' not in st.session_state:
        st.session_state.etf_lookthrough = {}


def get_selected_month() -> str:
    """현재 선택된 월 반환"""
    return st.session_state.get('selected_month', '2025-12')


def set_selected_month(year_month: str):
    """선택된 월 설정"""
    st.session_state.selected_month = year_month


def is_etf_lookthrough_enabled(account_id: int) -> bool:
    """특정 계좌의 ETF 투시 활성화 여부"""
    return st.session_state.etf_lookthrough.get(account_id, False)


def toggle_etf_lookthrough(account_id: int):
    """ETF 투시 토글"""
    current = is_etf_lookthrough_enabled(account_id)
    st.session_state.etf_lookthrough[account_id] = not current
```

---

## 6. 색상 테마 (`config.py`)

```python
# streamlit_app/config.py

# 페이지 설정
PAGE_TITLE = "포트폴리오 대시보드"
PAGE_ICON = "💰"
LAYOUT = "wide"

# 색상 팔레트
COLORS = {
    # 자산 유형별
    'STOCK': '#3498db',  # 파란색
    'BOND': '#2ecc71',   # 초록색
    'CASH': '#f39c12',   # 주황색

    # 증감
    'positive': '#27ae60',  # 녹색
    'negative': '#e74c3c',  # 빨간색
    'neutral': '#95a5a6',   # 회색

    # 기타
    'primary': '#3498db',
    'secondary': '#2ecc71',
    'accent': '#f39c12'
}

# 차트 기본 설정
CHART_DEFAULTS = {
    'height': 400,
    'font_size': 12,
    'line_width': 3,
    'marker_size': 10
}

# 데이터 제한
DATA_LIMITS = {
    'etf_lookthrough_top_n': 10,
    'total_holdings_top_n': 20,
    'sectors_top_n': 10
}

# 캐싱 설정 (초 단위)
CACHE_TTL = {
    'monthly_data': 3600,      # 1시간
    'etf_data': 86400,         # 24시간
    'static_data': 604800      # 7일
}
```

---

## 7. 에러 핸들링 유틸리티

```python
# streamlit_app/utils/error_handlers.py

import streamlit as st
from typing import Callable, Any

def safe_execute(func: Callable, error_message: str = "에러 발생", *args, **kwargs) -> Any:
    """
    안전한 함수 실행 (에러 시 사용자에게 메시지 표시)

    Args:
        func: 실행할 함수
        error_message: 에러 메시지
        *args, **kwargs: 함수 인자

    Returns:
        함수 실행 결과 또는 None
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        st.error(f"❌ {error_message}: {str(e)}")
        return None


def require_data(data, error_message: str = "데이터가 없습니다"):
    """
    데이터 필수 체크 (없으면 에러 표시 후 중단)

    Args:
        data: 체크할 데이터
        error_message: 에러 메시지
    """
    if data is None or (hasattr(data, '__len__') and len(data) == 0):
        st.warning(f"⚠️ {error_message}")
        st.stop()
```

---

## 8. 사용 예시

### 8.1 차트 컴포넌트 사용

```python
from streamlit_app.components.charts import create_waterfall_chart
import streamlit as st

# Waterfall Chart
fig = create_waterfall_chart(
    categories=['전월 자산', '추가 입금', '평가 손익', '금월 자산'],
    values=[1320000, 100000, 50000, 1470000],
    title="💧 자산 변동 내역"
)
st.plotly_chart(fig, use_container_width=True)
```

### 8.2 포맷터 사용

```python
from streamlit_app.utils.formatters import format_currency, format_percent

amount = 1234567
ratio = 5.234

print(format_currency(amount))           # "1,234,567원"
print(format_percent(ratio))             # "5.2%"
print(format_percent(ratio, include_sign=True))  # "+5.2%"
```

### 8.3 상태 관리 사용

```python
from streamlit_app.utils.state import init_session_state, get_selected_month

# 초기화
init_session_state()

# 현재 선택된 월 가져오기
month = get_selected_month()
```

---

## 9. 컴포넌트 테스트 가이드

### 9.1 차트 컴포넌트 테스트

```python
# test_charts.py (개발 시 테스트용)

import pandas as pd
from streamlit_app.components.charts import create_pie_chart

# 테스트 데이터
df = pd.DataFrame({
    'labels': ['Technology', 'Healthcare', 'Finance'],
    'values': [500000, 300000, 200000]
})

# 차트 생성
fig = create_pie_chart(df, title="테스트 Pie Chart")

# Streamlit에서 표시
import streamlit as st
st.plotly_chart(fig)
```

### 9.2 포맷터 테스트

```python
# test_formatters.py

from streamlit_app.utils.formatters import *

assert format_currency(1234567) == "1,234,567원"
assert format_percent(5.234) == "5.2%"
assert format_percent(5.234, include_sign=True) == "+5.2%"
assert format_shares(1.2345) == "1.23주"
assert format_compact_number(1500000) == "1.5M"

print("✅ All formatter tests passed!")
```

---

## 10. 성능 최적화 팁

### 10.1 차트 캐싱

```python
import streamlit as st
from streamlit_app.components.charts import create_pie_chart

@st.cache_data
def get_cached_pie_chart(df):
    return create_pie_chart(df)

# 사용
fig = get_cached_pie_chart(df)
st.plotly_chart(fig)
```

### 10.2 조건부 렌더링

```python
# 데이터가 있을 때만 차트 렌더링
if not df.empty:
    fig = create_pie_chart(df)
    st.plotly_chart(fig)
else:
    st.info("차트를 표시할 데이터가 없습니다.")
```

---

이제 모든 UI 컴포넌트 디자인이 완료되었습니다. 이 설계를 바탕으로 실제 구현을 진행할 수 있습니다.
