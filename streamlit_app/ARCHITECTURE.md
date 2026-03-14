# Streamlit 포트폴리오 대시보드

인터랙티브 웹 기반 포트폴리오 분석 대시보드

## 빠른 시작

```bash
streamlit run app.py
# http://localhost:8501
```

---

## 기능 소개

### 월별 투자 비교
- 4대 핵심 지표 (총자산, 총원금, 총수익, 수익률)
- Waterfall Chart로 자산 변동 흐름 시각화
- 월별 비교 테이블 및 자산 추이 차트

### 계좌별 포트폴리오
- 계좌별 접기/펼치기 + 보유 종목 vs ETF 투시 분석 (토글 방식)
- 섹터 비중 Pie Chart, 한국 주식 자동 종목명 표시

### 전체 포트폴리오
- 자산 유형별 요약 (STOCK/BOND/CASH)
- Sunburst Chart (계층적 구조, 드릴다운)
- 종목 검색 (직접 + ETF 내 간접 보유 통합)
- 통합 섹터 비중 및 Top 20 Holdings

### "전체 기간" 통합
- 월 선택 드롭다운에서 "전체 기간" 선택
- 모든 월의 매수 내역(purchase_history) 자동 합산 + CASH 포함

### 키보드 단축키
- `1`, `2`, `3`: 페이지 이동 (월별 비교/계좌별/전체)
- `←` / `→`: 이전/다음 월
- `F`: '전체 기간' 선택

### 차트 인터랙션 (Plotly)
- 줌 (마우스 드래그), 팬 (Shift+드래그), 호버, 더블 클릭 리셋
- Sunburst: 섹터 클릭으로 드릴다운, 중심 클릭으로 복귀

---

## 아키텍처

```
┌─────────────────────────────────────────────────┐
│                  Browser (User)                  │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│                 app.py (Main App)                 │
│   Sidebar Nav  │  Month Select  │  Page Router   │
└──────────────────────┬──────────────────────────┘
                       │
       ┌───────────────┼───────────────┐
       ▼               ▼               ▼
┌────────────┐ ┌────────────┐ ┌────────────┐
│  Monthly   │ │  Account   │ │   Total    │
│ Comparison │ │ Portfolio  │ │ Portfolio  │
└─────┬──────┘ └─────┬──────┘ └─────┬──────┘
      └───────────────┼───────────────┘
                      ▼
       ┌────────────────────────┐
       │     data_loader.py     │
       │  @st.cache_data        │
       └──────────┬─────────────┘
                  │
      ┌───────────┼───────────┐
      ▼           ▼           ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│  Charts  │ │  Utils   │ │  Config  │
│ (Plotly) │ │(Formats) │ │(Settings)│
└──────────┘ └──────────┘ └──────────┘
                  │
                  ▼
           ┌───────────┐
           │portfolio.db│
           └───────────┘
```

### 디렉토리 구조

```
streamlit_app/
├── config.py               # 설정 (색상, 캐싱 등)
├── data_loader.py          # 데이터 로딩 + 캐싱
├── components/
│   └── charts.py           # Plotly 차트 컴포넌트
├── pages/
│   ├── monthly_comparison.py
│   ├── account_portfolio.py
│   └── total_portfolio.py
└── utils/
    ├── formatters.py       # 숫자/날짜 포맷팅
    ├── price_fetcher.py    # 현재가 조회
    └── state.py            # 세션 상태 관리
```

---

## 모듈 상세

### config.py

```python
COLORS = {'STOCK': '#3498db', 'BOND': '#2ecc71', 'CASH': '#f39c12'}
CACHE_TTL = {'monthly_data': 3600, 'etf_data': 86400}   # 1시간, 24시간
DATA_LIMITS = {'etf_lookthrough_top_n': 10, 'total_holdings_top_n': 20}
DB_PATH = "portfolio.db"
```

### data_loader.py

주요 함수:

| 함수 | 반환 | TTL |
|------|------|-----|
| `get_available_months()` | `List[str]` | 7일 |
| `get_monthly_summary(year_month)` | `dict` (total_value, total_invested, total_profit, return_rate) | 1시간 |
| `get_accounts(year_month)` | `List[dict]` | 1시간 |
| `get_account_holdings(year_month, account_id)` | `DataFrame` | 1시간 |
| `get_account_sectors(year_month, account_id)` | `DataFrame` | 1시간 |
| `get_etf_lookthrough(year_month, account_id, top_n)` | `DataFrame` | 24시간 |
| `get_asset_type_summary(year_month)` | `dict` | 1시간 |
| `get_hierarchical_portfolio_data(year_month)` | `DataFrame` | 1시간 |
| `search_total_holdings(year_month, ticker)` | `dict` | 1시간 |
| `get_total_sectors(year_month, top_n)` | `DataFrame` | 1시간 |
| `get_total_top_holdings(year_month, top_n)` | `DataFrame` | 1시간 |

### components/charts.py

| 함수 | 용도 |
|------|------|
| `create_waterfall_chart(categories, values, title, height)` | 자산 변동 흐름 |
| `create_sunburst_chart(df, title, height)` | 계층적 구조 |
| `create_pie_chart(df, labels_col, values_col, title, height)` | 섹터 비중 |
| `create_horizontal_bar_chart(df, x_col, y_col, title, height)` | 섹터 막대 |
| `create_line_chart(df, x_col, y_col, title, height)` | 자산 추이 |

### utils/

```python
# formatters.py
format_currency(value) -> str           # "1,234,567원"
format_percent(value, decimals) -> str  # "+5.2%"
format_shares(value) -> str             # "1.23주"
get_previous_month(year_month) -> str   # "2025-12" → "2025-11"

# state.py
init_session_state()
get_selected_month() -> str
set_selected_month(year_month)
```

---

## 캐싱 전략

| 레벨 | TTL | 대상 |
|------|-----|------|
| 정적 데이터 | 7일 | `get_available_months()` |
| 월별 데이터 | 1시간 | `get_monthly_summary()` 등 |
| ETF 데이터 | 24시간 | `get_etf_lookthrough()` |

캐시 키: **함수명 + 파라미터**로 자동 생성. 무효화: TTL 만료, 코드 변경, 또는 앱 메뉴 > Clear cache.

---

## 성능 최적화

1. **쿼리 최적화**: 필요한 컬럼만 SELECT, 서브쿼리 활용 (JOIN 최소화)
2. **Top N 제한**: ETF 투시 10개, 전체 보유 20개
3. **조건부 로딩**: ETF 투시 토글 OFF 시 데이터 로딩 생략

---

## 확장 가이드

### 새 페이지 추가

```python
# 1. streamlit_app/pages/my_new_page.py 생성
def render(selected_month: str):
    st.header("새 페이지")
    # ... 구현

# 2. app.py에 라우팅 추가
from streamlit_app.pages import my_new_page
```

### 새 데이터 함수 추가

```python
# data_loader.py
@st.cache_data(ttl=3600)
def get_my_data(year_month: str) -> pd.DataFrame:
    month_id = get_month_id(year_month)
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT ... WHERE month_id = ?", conn, params=(month_id,))
    conn.close()
    return df
```

---

## 설정 커스터마이징

```python
# config.py 에서 수정
COLORS = {'STOCK': '#3498db', 'BOND': '#2ecc71', 'CASH': '#f39c12'}
CACHE_TTL = {'monthly_data': 3600, 'etf_data': 86400}
DATA_LIMITS = {'etf_lookthrough_top_n': 10, 'total_holdings_top_n': 20}
```

---

## 문제 해결

| 문제 | 원인 | 해결 |
|------|------|------|
| 데이터가 없다고 나옴 | DB에 해당 월 데이터 없음 | 파이프라인 재실행 |
| 차트가 안 보임 | 데이터 비어있음 | 브라우저 콘솔(F12) + Streamlit 로그 확인, Clear cache |
| ETF 투시가 느림 | yfinance API 속도 제한 | 24시간 캐싱 적용됨, 필요할 때만 토글 ON |
| 자동 새로고침 | Streamlit 파일 변경 감지 | `streamlit run app.py --server.runOnSave false` |

---

## 배포

### Streamlit Cloud (무료)
1. GitHub 레포 생성 및 푸시
2. [streamlit.io/cloud](https://streamlit.io/cloud) 접속 → 레포 연결

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py"]
```

---

## 보안 고려사항

- **DB**: 읽기 전용 접근 (`PRAGMA query_only = ON`)
- **SQL 인젝션 방지**: 파라미터 바인딩 사용 (`?` placeholder)
- **에러 메시지**: 민감 정보 미노출 (로그에만 기록)
