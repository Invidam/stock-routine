# Streamlit 대시보드 아키텍처

## 목차

- [전체 구조](#전체-구조)
- [데이터 흐름](#데이터-흐름)
- [모듈 상세](#모듈-상세)
- [캐싱 전략](#캐싱-전략)
- [성능 최적화](#성능-최적화)
- [확장 가이드](#확장-가이드)

---

## 전체 구조

### 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser (User)                        │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                      app.py (Main App)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Sidebar     │  │   Header     │  │ Main Content │      │
│  │  Navigation  │  │ Month Select │  │  Page Router │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Monthly    │ │   Account    │ │    Total     │
│  Comparison  │ │  Portfolio   │ │  Portfolio   │
│   (Page)     │ │    (Page)    │ │    (Page)    │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │
       └────────────────┼────────────────┘
                        │
                        ▼
        ┌───────────────────────────────┐
        │      data_loader.py           │
        │  (Cached Data Functions)      │
        │  @st.cache_data decorators    │
        └───────────────┬───────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Charts     │ │   Utils      │ │   Config     │
│  (Plotly)    │ │ (Formatters) │ │  (Settings)  │
└──────────────┘ └──────────────┘ └──────────────┘
                        │
                        ▼
                ┌───────────────┐
                │  portfolio.db │
                │   (SQLite)    │
                └───────────────┘
```

---

## 데이터 흐름

### 1. 앱 시작 (app.py)

```python
1. 페이지 설정 (set_page_config)
2. 세션 상태 초기화 (init_session_state)
3. 사이드바 렌더링 (페이지 선택)
4. 월 선택 드롭다운 렌더링
5. 선택된 페이지 라우팅
```

### 2. 페이지 렌더링

```python
# 예: 월별 투자 비교 페이지
monthly_comparison.render(selected_month)
    ↓
get_monthly_summary(selected_month)  # 캐시됨
    ↓
SQLite DB 쿼리 (캐시 미스 시)
    ↓
데이터 반환 (dict)
    ↓
Streamlit 컴포넌트 렌더링 (st.metric, st.plotly_chart 등)
```

### 3. 캐시 히트 시

```python
get_monthly_summary(selected_month)
    ↓
@st.cache_data 체크
    ↓
캐시 히트 → DB 쿼리 생략
    ↓
즉시 데이터 반환
```

---

## 모듈 상세

### config.py

**역할:** 전역 설정 관리

**주요 상수:**
```python
PAGE_TITLE = "포트폴리오 대시보드"
PAGE_ICON = "💰"
LAYOUT = "wide"

COLORS = {
    'STOCK': '#3498db',
    'BOND': '#2ecc71',
    'CASH': '#f39c12',
}

CACHE_TTL = {
    'monthly_data': 3600,   # 1시간
    'etf_data': 86400,      # 24시간
}

DATA_LIMITS = {
    'etf_lookthrough_top_n': 10,
    'total_holdings_top_n': 20,
}

DB_PATH = "portfolio.db"
```

**사용 예:**
```python
from streamlit_app.config import COLORS, DB_PATH
```

---

### data_loader.py

**역할:** DB 데이터 로딩 및 캐싱

**캐싱 전략:**
- `@st.cache_data(ttl=seconds)` 사용
- TTL(Time To Live) 설정으로 자동 만료
- 같은 파라미터 재요청 시 캐시 반환

**주요 함수:**

#### 기본 데이터
```python
get_available_months() -> List[str]
get_latest_month() -> str
get_month_id(year_month) -> int
```

#### 월별 요약
```python
get_monthly_summary(year_month) -> dict
# Returns: {
#     'total_value': int,
#     'total_invested': int,
#     'total_profit': int,
#     'return_rate': float
# }
```

#### 계좌 데이터
```python
get_accounts(year_month) -> List[dict]
get_account_holdings(year_month, account_id) -> pd.DataFrame
get_account_sectors(year_month, account_id) -> pd.DataFrame
get_etf_lookthrough(year_month, account_id, top_n) -> pd.DataFrame
```

#### 전체 포트폴리오
```python
get_asset_type_summary(year_month) -> dict
get_hierarchical_portfolio_data(year_month) -> pd.DataFrame
search_total_holdings(year_month, ticker) -> dict
get_total_sectors(year_month, top_n) -> pd.DataFrame
get_total_top_holdings(year_month, top_n) -> pd.DataFrame
```

**DB 쿼리 예:**
```python
@st.cache_data(ttl=3600)
def get_monthly_summary(year_month: str) -> Dict:
    month_id = get_month_id(year_month)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT SUM(h.amount) as total_invested
        FROM holdings h
        JOIN accounts a ON h.account_id = a.id
        WHERE a.month_id = ?
    """, (month_id,))

    # ... 데이터 처리

    conn.close()
    return result
```

---

### components/charts.py

**역할:** Plotly 차트 생성

**주요 함수:**

#### Waterfall Chart
```python
create_waterfall_chart(categories, values, title, height)
# 자산 변동 흐름 시각화
# [전월] → [입금] → [손익] → [금월]
```

#### Sunburst Chart
```python
create_sunburst_chart(df, title, height)
# 계층적 구조 시각화
# ROOT > 자산유형 > 섹터 > 종목
```

#### Pie Chart
```python
create_pie_chart(df, labels_col, values_col, title, height)
# 섹터 비중 등
```

#### Horizontal Bar Chart
```python
create_horizontal_bar_chart(df, x_col, y_col, title, height)
# 섹터 비중 (막대)
```

#### Line Chart
```python
create_line_chart(df, x_col, y_col, title, height)
# 자산 추이
```

**공통 패턴:**
```python
import plotly.graph_objects as go

def create_chart(...):
    fig = go.Figure(...)

    fig.update_layout(
        title=title,
        height=height,
        # ... 레이아웃 설정
    )

    return fig
```

---

### pages/

**역할:** 각 페이지 UI 렌더링

#### monthly_comparison.py
```python
def render(selected_month: str):
    st.header(f"📅 월별 투자 비교 - {selected_month}")

    # 1. Metric Cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("총 자산", ...)

    # 2. Waterfall Chart
    fig = create_waterfall_chart(...)
    st.plotly_chart(fig)

    # 3. 월별 비교 테이블
    df = get_recent_months_data(...)
    st.dataframe(df)
```

#### account_portfolio.py
```python
def render(selected_month: str):
    accounts = get_accounts(selected_month)

    for account in accounts:
        with st.expander(account['name']):
            tab1, tab2 = st.tabs(["보유 종목", "ETF 투시"])

            with tab1:
                # 보유 종목 테이블 + 섹터 차트

            with tab2:
                # ETF 투시 토글 + 종목 테이블
```

#### total_portfolio.py
```python
def render(selected_month: str):
    # 1. 자산 유형별 요약
    # 2. Sunburst Chart
    # 3. 종목 검색
    # 4. 섹터 차트
    # 5. Top 20 Holdings
```

---

### utils/

#### formatters.py
```python
format_currency(value) -> str           # "1,234,567원"
format_percent(value, decimals) -> str  # "+5.2%"
format_shares(value) -> str             # "1.23주"
get_previous_month(year_month) -> str   # "2025-12" → "2025-11"
get_next_month(year_month) -> str       # "2025-12" → "2026-01"
```

#### state.py
```python
init_session_state()                    # 세션 초기화
get_selected_month() -> str
set_selected_month(year_month)
```

---

## 캐싱 전략

### Streamlit 캐싱 레벨

**1. 정적 데이터 (7일)**
```python
@st.cache_data(ttl=604800)
def get_available_months():
    # 자주 안 바뀌는 데이터
```

**2. 월별 데이터 (1시간)**
```python
@st.cache_data(ttl=3600)
def get_monthly_summary(year_month):
    # 자주 조회하지만 실시간성 필요 없음
```

**3. ETF 데이터 (24시간)**
```python
@st.cache_data(ttl=86400)
def get_etf_lookthrough(year_month, account_id):
    # 외부 API (yfinance) 의존적
```

### 캐시 키

Streamlit은 **함수명 + 파라미터**로 캐시 키 생성

```python
get_monthly_summary("2025-12")  # 캐시 키 1
get_monthly_summary("2025-11")  # 캐시 키 2 (다른 키)
```

### 캐시 무효화

**자동 무효화:**
- TTL 만료 시
- 함수 코드 변경 시

**수동 무효화:**
- 앱 메뉴 > Clear cache
- `C` 키 누르기

---

## 성능 최적화

### 1. 쿼리 최적화

**인덱스 활용:**
```sql
CREATE INDEX idx_months_year_month ON months(year_month);
CREATE INDEX idx_accounts_month ON accounts(month_id);
```

**JOIN 최소화:**
```sql
-- Bad
SELECT * FROM holdings h
JOIN accounts a ON h.account_id = a.id
JOIN months m ON a.month_id = m.id
WHERE m.year_month = '2025-12';

-- Good
SELECT * FROM holdings h
WHERE h.account_id IN (
    SELECT id FROM accounts WHERE month_id = 123
);
```

### 2. Top N 제한

```python
# 전체 조회 X
SELECT * FROM analyzed_holdings ORDER BY amount DESC;

# Top N만 조회 O
SELECT * FROM analyzed_holdings ORDER BY amount DESC LIMIT 10;
```

### 3. 조건부 렌더링

```python
# ETF 투시: 토글 OFF 시 로딩 안 함
if not lookthrough_enabled:
    st.info("토글을 켜세요")
    return  # 데이터 로딩 생략

# 토글 ON 시에만 로딩
df = get_etf_lookthrough(...)
```

### 4. 컬럼 선택

```python
# Bad: 전체 컬럼
SELECT * FROM holdings;

# Good: 필요한 컬럼만
SELECT name, amount, asset_type FROM holdings;
```

---

## 확장 가이드

### 새 페이지 추가

**1. 페이지 파일 생성**
```python
# streamlit_app/pages/my_new_page.py

def render(selected_month: str):
    st.header("새 페이지")
    # ... 구현
```

**2. app.py에 라우팅 추가**
```python
from streamlit_app.pages import my_new_page

# 사이드바
page = st.radio("페이지", [..., "새 페이지"])

# 라우팅
if page == "새 페이지":
    my_new_page.render(selected_month)
```

### 새 차트 추가

**1. charts.py에 함수 추가**
```python
def create_my_chart(df, ...):
    fig = go.Figure(...)
    fig.update_layout(...)
    return fig
```

**2. 페이지에서 사용**
```python
from streamlit_app.components.charts import create_my_chart

fig = create_my_chart(df)
st.plotly_chart(fig)
```

### 새 데이터 함수 추가

**1. data_loader.py에 함수 추가**
```python
@st.cache_data(ttl=3600)
def get_my_data(year_month: str) -> pd.DataFrame:
    month_id = get_month_id(year_month)

    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("""
        SELECT ...
    """, conn, params=(month_id,))
    conn.close()

    return df
```

**2. 페이지에서 호출**
```python
df = get_my_data(selected_month)
```

---

## 디버깅 팁

### 1. 로그 확인

```python
import streamlit as st

# 디버그 정보 출력
st.write("Debug:", data)

# 에러 정보 출력
try:
    result = some_function()
except Exception as e:
    st.error(f"에러: {e}")
    st.exception(e)  # 스택 트레이스 출력
```

### 2. 캐시 상태 확인

```python
# 캐시 통계
st.write(st.cache_data.get_stats())
```

### 3. 세션 상태 확인

```python
# 모든 세션 상태 출력
st.write("Session State:", st.session_state)
```

---

## 보안 고려사항

### 1. DB 접근 제어

```python
# 읽기 전용 권한
conn = sqlite3.connect(DB_PATH, uri=True, check_same_thread=False)
conn.execute("PRAGMA query_only = ON")
```

### 2. 입력 검증

```python
# SQL 인젝션 방지 (파라미터 바인딩)
cursor.execute("SELECT * FROM months WHERE year_month = ?", (year_month,))
```

### 3. 에러 메시지

```python
# 민감 정보 노출 방지
try:
    result = query_db()
except Exception as e:
    st.error("데이터 로딩 실패")  # 구체적 에러 숨김
    # 로그에만 기록
    logger.error(f"DB Error: {e}")
```

---

**참고:** 이 문서는 Streamlit 대시보드의 기술적 구조를 설명합니다. 사용 방법은 [README.md](./README.md)를 참고하세요.
