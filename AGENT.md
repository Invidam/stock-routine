# 🤖 Agent Development Guide

이 문서는 AI 에이전트 및 개발자가 프로젝트를 이해하고 수정할 때 참고하는 가이드입니다.

## 📐 아키텍처 개요

### 시스템 플로우

```
YAML 데이터 작성
    ↓
data/import_monthly_data.py (YAML → SQLite DB)
    ↓
core/analyze_portfolio.py (yfinance → ETF 분석 → DB 저장)
    ↓
visualization/visualize_portfolio.py (DB → Matplotlib 차트)
    ↓
charts/*.png (최종 출력)
```

### 핵심 컴포넌트

1. **데이터 레이어** (`data/`)
   - `init_db.py`: 스키마 정의 및 DB 초기화
   - `import_monthly_data.py`: YAML → DB 변환
   - `import_monthly_purchases.py`: 적립식 투자 수량 계산
   - `query_db.py`: DB 쿼리 유틸리티
   - `portfolio.db`: SQLite 데이터베이스 (루트)

2. **분석 레이어** (`core/`)
   - `analyze_portfolio.py`: 핵심 로직 (약 1000줄)
   - `evaluate_accumulative.py`: 적립식 투자 평가
   - yfinance API 호출
   - ETF holdings/sectors 분석
   - 자산 유형별 처리 (STOCK/BOND/CASH)

3. **시각화 레이어** (`visualization/`)
   - `visualize_portfolio.py`: Matplotlib 차트 생성
   - 4종류 차트 (도넛, 막대 x2, 라인)

4. **자동화 레이어** (`scripts/`)
   - `run_monthly.py`: 통합 실행 스크립트
   - `run_all_months.py`: 전체 월 일괄 실행
   - 크론 연동 가능

5. **웹 대시보드 레이어** (`streamlit_app/`)
   - `app.py`: Streamlit 앱 엔트리포인트 (루트)
   - `pages/`: 페이지별 렌더링 로직
   - `components/`: Plotly 차트 컴포넌트
   - `data_loader.py`: 데이터 로딩 및 캐싱
   - `utils/`: 유틸리티 함수

## 🔑 핵심 설계 결정

### 1. 자산 유형 분류 (asset_type)

#### 배경
초기에는 주식형 ETF만 지원했으나, 사용자의 요청으로 채권과 현금성 자산을 추가함

#### 구현
- `STOCK`: yfinance로 ETF holdings/sectors 조회
- `BOND`: yfinance 시도 → 실패 시 "Fixed Income" 섹터로 대체
- `CASH`: yfinance 조회 없이 "Cash & Equivalents" 섹터로 직접 처리

#### 코드 위치
- `core/analyze_portfolio.py:440-540` - 자산 유형별 분석 함수
- `analyze_stock_asset()`
- `analyze_bond_asset()`
- `analyze_cash_asset()`

### 2. 기타 종목 (OTHER) 처리

#### 문제
yfinance의 `top_holdings`는 상위 10개만 제공하여, SPY(500개 종목) 중 10개만 분석하면 원금의 40%만 표시됨

#### 해결
`calculate_my_holdings()` 함수에서 holdings 비중 합계를 계산하고, 1.0이 안되면 나머지를 "OTHER" 항목으로 자동 추가

#### 코드
```python
# core/analyze_portfolio.py:383-394
if total_weight < 1.0:
    remaining_weight = 1.0 - total_weight
    remaining_amount = int(my_investment * remaining_weight)

    result.append({
        'source_ticker': etf_ticker,
        'stock_symbol': 'OTHER',
        'stock_name': f'{etf_ticker} 기타 종목',
        'holding_percent': remaining_weight,
        'my_amount': remaining_amount
    })
```

### 3. 같은 Ticker 통합

#### 문제
"ACE 미국국채30년액티브"와 "미국채 30년" 모두 TLT로 매핑되는데, 이름이 달라서 별도 항목으로 표시됨

#### 해결
통합 holdings 계산 시 STOCK/BOND는 `stock_symbol`로 GROUP BY하여 같은 ticker는 자동 통합

#### 코드
```sql
-- core/analyze_portfolio.py:916-934
SELECT
    CASE
        WHEN asset_type IN ('STOCK', 'BOND') THEN stock_symbol
        ELSE stock_name
    END as display_name,
    asset_type,
    SUM(my_amount) as amount
FROM analyzed_holdings
WHERE month_id = ? AND account_id IS NULL
GROUP BY
    CASE
        WHEN asset_type IN ('STOCK', 'BOND') THEN stock_symbol
        ELSE stock_name
    END,
    asset_type
```

### 4. target_ratio 자동 계산

#### 배경
사용자가 매번 수동으로 계산하기 번거로움

#### 구현
`data/import_monthly_data.py`에서 계좌별 총액을 계산하고, 각 holding의 비중을 자동 계산

#### 코드
```python
# data/import_monthly_data.py:98-109
total_amount = sum(h['amount'] for h in holdings_list)

for holding in holdings_list:
    target_ratio = holding['amount'] / total_amount if total_amount > 0 else 0.0
    # DB에 저장
```

### 5. 한국 주식 실제 종목명 표시

#### 배경
한국 주식은 티커(예: 005930.KS)가 사람이 읽기 어렵고, 실제 회사명(삼성전자)을 보는 것이 직관적임

#### 구현
- `.KS` 확장자로 한국 주식 자동 감지
- `stock_name` 필드를 활용하여 실제 회사명 표시
- 티커는 괄호 안에 부가 정보로 표시

#### 코드
```python
# core/analyze_portfolio.py:1040-1054
if row['asset_type'] == 'STOCK' and row['stock_symbol'] and row['stock_symbol'].endswith('.KS'):
    # 한국 주식: 실제 이름 표시
    display_text = f"{row['stock_name']:<30} ({row['stock_symbol']:<10})"
else:
    # 미국 주식, 채권, 현금: ticker/이름 표시
    display_text = f"{row['display_name']:<42}"
```

### 6. 다중 ETF 출처 추적

#### 배경
AAPL이나 MSFT 같은 종목이 SPY와 QQQ 모두에 포함되어 있을 때, 어떤 ETF에서 온 것인지 알 수 없음

#### 구현
- `GROUP_CONCAT(DISTINCT source_ticker)` SQL 함수 사용
- 쉼표로 여러 ETF 출처 연결
- 2개 이상의 ETF에서 온 경우 `[from: SPY,QQQ]` 형태로 표시

#### 코드
```python
# core/analyze_portfolio.py:939-980
query = """
    SELECT
        ...
        GROUP_CONCAT(DISTINCT source_ticker) as source_tickers,
        SUM(my_amount) as amount
    FROM analyzed_holdings
    WHERE month_id = ? AND account_id IS NULL
    GROUP BY ...
"""

# 표시 시
source_info = f" [from: {row['source_tickers']}]" if pd.notna(row.get('source_tickers')) and ',' in str(row.get('source_tickers', '')) else ""
```

### 7. OTHER 항목 맨 마지막 표시

#### 배경
OTHER 항목이 금액이 많을 경우 상위 순위에 표시되면 실제 개별 종목을 보기 어려움

#### 구현
- SQL `ORDER BY`에 `CASE WHEN stock_symbol = 'OTHER' THEN 1 ELSE 0 END` 추가
- 금액과 무관하게 OTHER을 항상 마지막으로 정렬
- 터미널 출력 시 별도 섹션 "📦 [ETF 내 기타 종목 요약]"으로 분리

#### 코드
```python
# core/analyze_portfolio.py:939-980
ORDER BY
    CASE WHEN stock_symbol = 'OTHER' THEN 1 ELSE 0 END,  -- OTHER을 마지막으로
    amount DESC

# 터미널 출력 시
other_row = holdings_df_all[holdings_df_all['stock_symbol'] == 'OTHER']
holdings_df_without_other = holdings_df_all[holdings_df_all['stock_symbol'] != 'OTHER']
holdings_df_top = holdings_df_without_other.head(top_n)
```

## 📊 데이터베이스 설계

### ER 다이어그램

```
months (월별 기본 정보)
  ↓ 1:N
accounts (계좌)
  ↓ 1:N
  ├─ holdings (보유 항목: 원본 데이터)
  └─ purchase_history (적립식 투자 매수 이력) [NEW]

months
  ↓ 1:N
analyzed_holdings (분석 결과: 개별 종목)
analyzed_sectors (분석 결과: 섹터 비중)
analysis_metadata (분석 메타)

purchase_history
  ↓ aggregation
current_holdings_summary (뷰: 종목별 보유 수량 집계) [NEW]
```

### 주요 테이블

#### holdings
- 사용자 입력 데이터 (YAML에서 임포트)
- `asset_type`: STOCK/BOND/CASH
- `interest_rate`: 현금 자산의 이자율

#### analyzed_holdings
- ETF 분석 결과
- `source_ticker`: 원본 ETF (SPY, QQQ, TLT)
- `stock_symbol`: 개별 종목 ticker (AAPL, MSFT, ...)
- `stock_name`: 개별 종목 이름
- `asset_type`: 자산 유형 (분석 시 상속)

#### analyzed_sectors
- 섹터별 비중
- `sector_name`: technology, Fixed Income, Cash & Equivalents 등
- `asset_type`: 자산 유형

#### purchase_history (NEW)
- **적립식 투자 매수 이력** (수량 기반 추적)
- 핵심 필드:
  - `ticker`: 종목 코드 (SPY, QQQ, AMZN, ...)
  - `quantity`: 매수 수량 (REAL, 불변)
  - `input_amount`: 투자 금액 (원화)
  - `purchase_date`: 실제 매수일 (YYYY-MM-DD)
  - `price_at_purchase`: 매수 당시 주가 (원화 환산, 선택적)
  - `currency`: 통화 (KRW/USD)
  - `exchange_rate`: 환율 (USD 종목만)
  - `account_id`: 계좌 FK (필수, 계좌별 매수 이력 추적)
  - `year_month`: 귀속 월 (예: "2025-11-purchase")
  - `asset_type`: 자산 유형 (STOCK/BOND, CASH는 제외됨)

- **설계 원칙**:
  - 수량은 불변 (한번 저장되면 절대 변경 안 됨)
  - price_at_purchase는 감사/추적용으로만 저장, 평가 계산에는 사용 안 함
  - 평가액은 항상 `quantity × current_price`로 실시간 계산

#### current_holdings_summary (뷰) (NEW)
- purchase_history를 종목별로 집계한 읽기 전용 뷰
- 필드:
  - `ticker`: 종목 코드
  - `asset_type`: 자산 유형
  - `total_quantity`: 총 보유 수량
  - `total_invested`: 총 투자 금액
  - `avg_price`: 평균 매수가 (total_invested / total_quantity)

### account_id 컬럼의 의미

- `account_id IS NULL`: 전체 포트폴리오 통합 분석 결과
- `account_id = 1, 2, ...`: 개별 계좌 분석 결과
- **purchase_history**: account_id 필수 (계좌별 매수 이력 추적)

## 🔧 주요 함수 설명

### core/analyze_portfolio.py

#### fetch_etf_holdings(ticker)
- yfinance로 ETF의 top_holdings 조회
- 반환: DataFrame with ['Symbol', 'Name', 'Holding Percent']
- 주의: 상위 10개만 제공됨

#### calculate_my_holdings(etf_ticker, my_investment, holdings_df)
- ETF holdings를 내 투자금액 기준으로 계산
- **중요**: 비중 합계 < 1.0이면 "OTHER" 항목 자동 추가
- 반환: List[Dict] with ['source_ticker', 'stock_symbol', 'stock_name', 'holding_percent', 'my_amount']

#### analyze_stock_asset(ticker, name, amount, month_id, account_id, db_path)
- 주식형 ETF 또는 개별 주식 분석
- **개별 주식 감지**: `quoteType == 'EQUITY'`인 경우 개별 주식으로 처리
  - Holdings: 자기 자신을 100% 보유한 것으로 저장
  - Sectors: `info.get('sector')`에서 섹터 조회
- **ETF**: yfinance로 holdings/sectors 조회 → DB 저장
- 코드 위치: `core/analyze_portfolio.py:440-540`
- 예시:
  ```python
  # 개별 주식 감지
  quote_type = info.get('quoteType', 'UNKNOWN')

  if quote_type == 'EQUITY':
      print(f"   📌 개별 주식으로 처리")
      # Holdings: 자기 자신 100%
      holdings_data = [{
          'source_ticker': mapped_ticker,
          'stock_symbol': mapped_ticker,
          'stock_name': name,
          'holding_percent': 1.0,
          'my_amount': amount
      }]
      save_analyzed_holdings(month_id, account_id, holdings_data, db_path, asset_type='STOCK')

      # Sectors: info에서 조회
      sector_name = info.get('sector', 'Unknown')
      if sector_name and sector_name != 'Unknown':
          sectors_data = [{
              'source_ticker': mapped_ticker,
              'sector_name': sector_name,
              'sector_percent': 1.0,
              'my_amount': amount
          }]
          save_analyzed_sectors(month_id, account_id, sectors_data, db_path, asset_type='STOCK')
      return

  # ETF인 경우 기존 로직
  holdings_df = fetch_etf_holdings(mapped_ticker)
  ...
  ```

#### analyze_bond_asset(...)
- 채권형 ETF 분석
- yfinance 시도 → 실패 시 대체 로직 (Fixed Income 섹터)

#### analyze_cash_asset(...)
- 현금성 자산 처리
- yfinance 조회 없이 직접 "Cash & Equivalents" 섹터로 저장

#### print_integrated_analysis(month_id, db_path)
- 통합 포트폴리오 분석 결과 출력
- Net Worth + 통합 섹터 + 통합 holdings TOP 50
- 한국 주식(.KS)은 실제 종목명 표시
- OTHER은 별도 섹션으로 맨 마지막에 표시

### visualization/visualize_portfolio.py

#### create_asset_allocation_chart(net_worth, output_path)
- 도넛 차트: 주식형/채권형/현금형 비중
- 중앙에 총 자산 표시

#### create_sector_chart(sectors_df, output_path)
- 막대 차트: 섹터별 금액 분포

#### create_top_holdings_chart(holdings_df, output_path, top_n=50)
- 막대 차트: 상위 50개 보유 항목 (초장형 레이아웃)
- 한국 주식(.KS)은 실제 종목명 표시
- OTHER은 회색으로 맨 마지막에 표시 (구분선 포함)
- 상위 3개 항목은 테두리로 강조
- 자산 유형별 색상 구분 (주식/채권/현금/기타)

#### create_asset_trend_chart(db_path, output_path, months=6)
- 라인 차트: 월별 총 자산 추이
- 최소 2개월 데이터 필요

### data/import_monthly_purchases.py

#### import_monthly_purchases(yaml_path, db_path, purchase_day)
- 적립식 투자 데이터 임포트 (YAML → purchase_history)
- **중요**: 기존 YAML 구조(`accounts > holdings`)를 그대로 사용
- 핵심 로직:
  ```python
  # year_month 이중 형식
  file_stem = Path(yaml_path).stem  # "2025-11-purchase"
  year_month_db = file_stem  # DB 조회용
  year_month_date = file_stem.replace('-purchase', '')  # 날짜 생성용

  # CASH 제외
  if asset_type == 'CASH':
      continue

  # 수량 계산
  calc_result = calculate_quantity(ticker, amount, year_month_date, purchase_day, db_path)

  # DB 저장 (account_id 반드시 포함)
  save_purchase(ticker, asset_type, year_month_db, calc_result, amount, account_name, ...)
  ```

#### get_historical_price(ticker, target_date, max_lookback_days=7)
- yfinance로 특정 날짜의 종가 조회
- 휴일인 경우 직전 영업일 자동 조회
- 반환: `(실제_날짜, 종가, 통화)` 또는 `None`

#### get_price_from_db(ticker, target_date, db_path)
- DB의 과거 매수 기록에서 유사 날짜(±7일) 주가 검색
- yfinance 실패 시 폴백으로 사용
- 반환: `주가(KRW)` 또는 `None`

#### calculate_quantity(ticker, input_amount, year_month, purchase_day, db_path)
- 투자 금액 기준으로 매수 수량 계산
- 로직:
  1. 매수 기준일 생성 (예: "2025-11-26")
  2. 과거 주가 조회 (yfinance 우선 → DB 폴백)
  3. 환율 적용 (USD 종목만)
  4. 수량 계산: `quantity = input_amount / price_krw`
- 반환: `{'purchase_date', 'quantity', 'price_krw', 'leftover', 'currency', 'exchange_rate'}`

#### save_purchase(ticker, asset_type, year_month, calc_result, input_amount, account_name, note, db_path)
- purchase_history 테이블에 저장
- **중요**: account_name으로 account_id 조회 (year_month_db 사용)
- 계좌를 찾지 못하면 account_id는 NULL (그러나 이는 비정상 상황)

### core/evaluate_accumulative.py

#### evaluate_holdings(db_path)
- purchase_history에서 종목별 보유 수량 집계
- 현재가 조회 (yfinance)
- 평가액 계산: `current_value = quantity × current_price`
- 손익 계산: `profit = current_value - invested`
- 수익률 계산: `return_rate = (profit / invested) × 100`
- 반환: DataFrame with ['ticker', 'quantity', 'invested', 'current_price', 'current_value', 'profit', 'return_rate']

#### get_current_price(ticker)
- yfinance로 현재가 조회
- 한국 주식(.KS/.KQ): KRW로 반환
- 미국 주식/ETF: USD → KRW 환산
- 반환: `현재가(KRW)`

## 🚨 주의사항

### yfinance API 제한

1. **top_holdings는 상위 10개만 제공**
   - 해결: "OTHER" 항목으로 나머지 보정

2. **TLT 등 채권 ETF는 holdings 데이터 없음**
   - 해결: "Fixed Income" 섹터로 대체

3. **환율 데이터 (KRW=X) 조회 실패 가능**
   - 해결: 기본값 1,450원 사용

4. **개별 주식은 funds_data 속성 없음**
   - 해결: quoteType 필드로 ETF/개별주식 구분, 개별 주식은 100% 자기 보유로 처리

5. **과거 주가 조회 실패 가능** (휴일, 상장 전 등)
   - 해결: DB 폴백 (과거 매수 기록에서 유사 날짜 검색)

### DB 무결성

1. **months 테이블의 year_month는 UNIQUE**
   - 같은 월 데이터 재임포트 시 `--overwrite` 필수

2. **account_id IS NULL = 전체 분석**
   - 계좌별 분석과 전체 분석은 별도로 저장

3. **analyzed_* 테이블은 overwrite 시 DELETE**
   - 분석 결과가 중복 저장되지 않도록 주의

4. **purchase_history의 account_id는 필수** (NULL이면 안 됨)
   - year_month 불일치로 account_id가 NULL이 되는 경우 주의
   - DB 조회용 year_month ("2025-11-purchase")와 날짜 생성용 year_month ("2025-11")를 구분

5. **year_month 이중 형식 주의**
   - 파일명: `2025-11-purchase.yaml`
   - DB에 저장된 year_month: `2025-11-purchase` (months, accounts 테이블)
   - purchase_date 생성: `2025-11` + `-26` → `2025-11-26`
   - **절대 혼동 금지**: account_id 조회 시 전자, 날짜 생성 시 후자 사용

## 📝 개발 이력

### Phase 1: 기본 시스템 구축
- SQLite DB 설계
- YAML 임포트
- yfinance 연동
- 주식형 ETF 분석

### Phase 2: 자산 유형 확장
- asset_type 컬럼 추가 (STOCK/BOND/CASH)
- DB 마이그레이션 스크립트
- 자산 유형별 분석 함수

### Phase 3: 통합 Net Worth 뷰
- 위험/안전/현금 자산 구분
- 통합 섹터 비중
- 통합 holdings (초기 TOP 30)

### Phase 4: 기타 종목 처리
- yfinance top_holdings 한계 해결
- "OTHER" 항목 자동 추가
- 원금과 평가액 일치

### Phase 5: Ticker 통합
- 같은 ticker는 하나로 합침
- TLT 200,000 + 100,000 → 300,000

### Phase 6: 시각화
- Matplotlib 차트 4종
- 자산 배분 도넛
- 섹터/holdings 막대
- 자산 추이 라인

### Phase 7: 자동화
- run_monthly.py 통합 스크립트
- 크론 연동 가능
- 로깅 추가

### Phase 8: 상세 분석 및 시각화 개선
- TOP 30 → TOP 50 확장
- 한국 주식 실제 종목명 표시 (.KS 감지)
- 다중 ETF 출처 추적 (GROUP_CONCAT)
- OTHER 항목 맨 마지막 표시 (SQL ORDER BY 개선)
- 초장형 차트 레이아웃 (16x70 figsize)
- 상위 3개 항목 테두리 강조
- requirements.txt 추가

### Phase 9: 개별 주식 지원 (Individual Stocks)
- **문제**: AMZN, GOOGL, TSLA 등 개별 주식에서 "No Fund data found" 에러 발생
- **원인**: 개별 주식은 ETF가 아니므로 `funds_data` 속성이 없음
- **해결**: `quoteType` 필드로 ETF와 개별 주식 자동 구분
  - `quoteType == 'EQUITY'` → 개별 주식
  - `quoteType == 'ETF'` → ETF
- **구현**: `analyze_stock_asset()` 함수 수정
  - 개별 주식: 자기 자신을 100% 보유, 섹터는 `info.get('sector')`
  - ETF: 기존 로직 유지 (funds_data.top_holdings)

### Phase 10: 적립식 투자 추적 시스템 (Accumulative Investment)
- **요구사항**:
  - 월별 투자 금액 입력 → 수량 자동 계산 → 현재가 기준 평가
  - 수량은 불변 (한번 저장되면 변경 안 됨)
  - 과거 주가 자동 조회 (특정 날짜, 기본 26일)
  - 기존 YAML 구조(`accounts > holdings`) 유지 (절대 변경 금지)

- **구현**:
  1. **DB 스키마 추가** (`migrate_add_purchase_history.py`):
     - `purchase_history` 테이블: ticker, quantity, input_amount, purchase_date, price_at_purchase, account_id
     - `current_holdings_summary` 뷰: 종목별 보유 수량 집계

  2. **수량 계산 스크립트** (`import_monthly_purchases.py`):
     - YAML 파일에서 `accounts > holdings` 읽기
     - 과거 주가 조회 (yfinance 우선, 실패 시 DB 폴백)
     - 수량 계산: `amount / price_krw`
     - purchase_history 테이블에 저장
     - **중요**: CASH 자산은 자동 제외 (수량 개념 없음)

  3. **평가 스크립트** (`evaluate_accumulative.py`):
     - 종목별 보유 수량 집계
     - 현재가 조회
     - 평가액 계산: `quantity × current_price`
     - 손익 및 수익률 계산

- **핵심 설계 결정**:
  - **year_month 이중 형식**:
    - `year_month_db = "2025-11-purchase"` (DB 조회용, months/accounts 테이블)
    - `year_month_date = "2025-11"` (날짜 생성용, purchase_date 생성)
  - **account_id 필수**: purchase_history 테이블에 account_id 저장 (계좌별 매수 이력 추적)
  - **price_at_purchase 선택적**: 감사용으로만 저장, 계산에는 사용 안 함

- **에러 수정**:
  1. **account_id NULL 문제**:
     - 원인: year_month 불일치 (months 테이블: "2025-11-purchase", 조회: "2025-11")
     - 해결: year_month를 DB 조회용과 날짜 생성용으로 분리

  2. **purchase_date 오류** ("2025-11-purchase-26"):
     - 원인: 날짜 생성 시 전체 파일명 사용
     - 해결: year_month_date에서 "-purchase" 제거

- **파일 명명 규칙**:
  - 일반 월별 포트폴리오: `2025-11.yaml`, `2025-12.yaml`
  - 적립식 투자 데이터: `2025-11-purchase.yaml`, `2025-12-purchase.yaml`

### Phase 11: Streamlit 웹 대시보드 (Web Dashboard)

- **요구사항**:
  - 인터랙티브 웹 기반 포트폴리오 분석 대시보드
  - CLI 대신 브라우저에서 직관적으로 데이터 확인
  - 실시간 차트 인터랙션 (줌, 호버, 드릴다운)
  - 성능 최적화 (캐싱, Top N 제한)

- **아키텍처 설계**:
  ```
  app.py (메인)
  └── streamlit_app/
      ├── config.py              # 설정 (색상, 캐싱 등)
      ├── data_loader.py         # DB 데이터 로딩 + 캐싱
      ├── components/
      │   └── charts.py          # Plotly 차트
      ├── pages/
      │   ├── monthly_comparison.py    # 월별 투자 비교
      │   ├── account_portfolio.py     # 계좌별 포트폴리오
      │   └── total_portfolio.py       # 전체 포트폴리오
      └── utils/
          ├── formatters.py      # 숫자/날짜 포맷팅
          └── state.py           # 세션 상태 관리
  ```

- **주요 구현**:

  1. **월별 투자 비교 페이지**:
     - 4개 Metric Cards: 총자산, 총원금, 총수익, 수익률
     - Waterfall Chart: [전월 자산] → [추가 입금] → [평가 손익] → [금월 자산]
     - 월별 비교 테이블 (최근 3개월)
     - 자산 추이 Line Chart (전체 기간)

  2. **계좌별 포트폴리오 페이지**:
     - 계좌별 Expander (접기/펼치기)
     - 2개 탭: 보유 종목 vs ETF 투시 분석
     - ETF 투시 토글 (기본 OFF, 성능 최적화)
     - 섹터 Pie Chart
     - 한국 주식 자동 종목명 표시 (예: 삼성전자 (005930.KS))
     - OTHER은 맨 하단 표시

  3. **전체 포트폴리오 페이지**:
     - 자산 유형별 요약 (STOCK/BOND/CASH)
     - Sunburst Chart (계층적 구조, 클릭 시 드릴다운)
     - 종목 검색 기능 (직접 보유 + ETF 내 간접 보유 통합)
     - 통합 섹터 비중 Horizontal Bar Chart
     - Top 20 Holdings 테이블

- **성능 최적화**:
  - **캐싱 전략**: `@st.cache_data` 데코레이터 사용
    - 월별 데이터: 1시간 TTL
    - ETF 데이터: 24시간 TTL
    - 정적 데이터: 7일 TTL
  - **Top N 제한**: ETF 투시 10개, 전체 보유 20개
  - **조건부 로딩**: ETF 투시 토글 방식 (기본 OFF → 데이터 로딩 안 함)
  - **DB 쿼리 최적화**: 필요한 컬럼만 SELECT, 인덱스 활용

- **기술 스택**:
  - Streamlit 1.52.2: 웹 프레임워크
  - Plotly 6.5.0: 인터랙티브 차트
  - Pandas: 데이터 처리
  - SQLite: DB (기존 활용)

- **핵심 설계 결정**:
  1. **캐싱**: 같은 데이터 재요청 시 DB 쿼리 생략 → 성능 향상
  2. **상태 관리**: `st.session_state`로 선택한 월 유지 (페이지 이동 시)
  3. **비중 계산**: 계좌별로 재계산 (holdings의 target_ratio 대신)
  4. **차트 라이브러리**: Plotly (matplotlib 대신) → 인터랙티브 기능
  5. **레이아웃**: Wide 레이아웃 + 4컬럼 Metrics → 화면 최대 활용

- **문서화**:
  - `streamlit_app/README.md`: 사용 가이드
  - `streamlit_app/ARCHITECTURE.md`: 아키텍처 문서
  - `designs/`: UI 디자인 문서 (5개 파일)
    - 00-layout-overview.md
    - 01-monthly-comparison.md
    - 02-account-portfolio.md
    - 03-total-portfolio.md
    - 04-components.md

- **실행 방법**:
  ```bash
  # Streamlit 앱 실행
  streamlit run app.py

  # 브라우저 접속
  # http://localhost:8501
  ```

- **개발 중 피드백 및 개선사항**:
  - Waterfall Chart 높이 증가 (400 → 500px)
  - 비중 계산을 계좌별로 변경 (전체 대비 → 계좌 내 비중)
  - 한국 주식 (.KS) 자동 종목명 표시
  - OTHER 항목 맨 하단 정렬
  - ETF 투시 분석 원 그래프 추가 (예정)
  - URL 기반 탭 네비게이션 (예정)
  - 키보드 단축키 (Cmd/Ctrl+1,2,3) (예정)

## 🔮 향후 개선 방향

### 1. 텔레그램 봇 연동

```python
# 예시 코드
import telegram

def send_charts_to_telegram(bot_token, chat_id, charts_dir):
    bot = telegram.Bot(token=bot_token)
    for chart in Path(charts_dir).glob("*.png"):
        bot.send_photo(chat_id=chat_id, photo=open(chart, 'rb'))
```

### 2. 월별 변화 추적 (MoM)

- 이전 월 데이터와 비교
- 수익률 계산
- 변동률 표시

### 3. LLM 연동 (Gemini/GPT)

AI 분석 리포트 자동 생성:

#### Persona: "Portfolio Sentinel"
- 15년 경력의 냉철하고 객관적인 퀀트 자산 운용가
- 숫자와 데이터에 기반한 논리적 분석
- 구체적인 액션 아이템 제시

#### Analysis Guidelines
1. **포트폴리오 건전성 진단**
   - 섹터 쏠림 현상 (특정 섹터 40% 초과 시 경고)
   - ETF 중복 투자 (SPY + QQQ → AAPL/MSFT 중복 노출)
   - 자산 배분 (주식/채권/현금 비율 평가)

2. **기간별 성과 요약**
   - WoW, MoM 수익률 및 평가손익
   - Best/Worst 종목 분석

3. **대응 전략**
   - 리밸런싱 제안 (목표 비중 vs 실제 비중)
   - 포지션 조정 권고

#### Implementation
```python
import google.generativeai as genai

def generate_analysis_report(portfolio_data, month_id, db_path):
    # 데이터 준비
    net_worth = calculate_net_worth(month_id, db_path)
    sectors = calculate_integrated_sectors(month_id, db_path)

    # 프롬프트 생성
    prompt = f"""
    당신은 Portfolio Sentinel입니다.
    다음 데이터를 분석하여 리포트를 작성하세요:

    - 총 자산: {net_worth['total']:,}원
    - 섹터 비중: {sectors.to_dict()}
    ...
    """

    # LLM 호출
    model = genai.GenerativeModel('gemini-1.5-pro')
    response = model.generate_content(prompt)
    return response.text
```

### 4. 리밸런싱 추천

- 목표 비중과 실제 비중 비교
- 매수/매도 추천

### 5. 웹 대시보드

- Streamlit 사용
- 실시간 차트 조회
- 월별 비교

## 🐛 트러블슈팅 가이드

### 문제: 총 자산이 원금보다 적음

#### 진단
```bash
sqlite3 portfolio.db "SELECT asset_type, SUM(my_amount) FROM analyzed_holdings WHERE month_id = X AND account_id IS NULL GROUP BY asset_type"
```

#### 원인
- yfinance top_holdings가 상위 10개만 제공

#### 해결
- "OTHER" 항목 추가 로직 확인
- `calculate_my_holdings()` 함수의 `total_weight < 1.0` 조건 확인

### 문제: 같은 ticker가 중복 표시

#### 진단
```bash
sqlite3 portfolio.db "SELECT display_name, COUNT(*) FROM (통합 holdings 쿼리) GROUP BY display_name HAVING COUNT(*) > 1"
```

#### 원인
- GROUP BY에서 stock_name 사용

#### 해결
- stock_symbol로 GROUP BY 변경
- `calculate_integrated_holdings()` 함수 확인

### 문제: 차트 생성 실패

#### 진단
- Matplotlib 설치 확인: `pip show matplotlib`
- 폰트 경고는 무시 가능 (차트는 생성됨)

#### 해결
```bash
pip install matplotlib
python visualize_portfolio.py --month 2025-12
```

## 📚 참고 자료

### yfinance 문서
- https://github.com/ranaroussi/yfinance
- `etf.funds_data.top_holdings`
- `etf.funds_data.sector_weightings`

### SQLite 문서
- https://www.sqlite.org/docs.html
- CASE WHEN, GROUP BY, NULL handling

### Matplotlib 문서
- https://matplotlib.org/
- pie chart, bar chart, line chart

## ✅ 체크리스트

새로운 기능 추가 시:
- [ ] 테이블 스키마 변경 → `data/init_db.py` 업데이트
- [ ] DB 마이그레이션 스크립트 작성 (필요 시)
- [ ] 핵심 로직 추가 (`core/` 또는 `data/`)
- [ ] 테스트 데이터 (YAML) 준비
- [ ] 전체 플로우 테스트 (`scripts/run_monthly.py`)
- [ ] README.md 업데이트
- [ ] AGENT.md 업데이트

코드 수정 시 주의사항:
- [ ] import 경로가 올바른지 확인 (모듈 경로 사용)
- [ ] 파일 이동 시 모든 참조 업데이트
- [ ] 문서의 예제 명령어 경로 확인
- [ ] 웹 대시보드에서 정상 작동하는지 확인

### Phase 12: "전체 기간" 통합 기능 (All Months Aggregation)

- **요구사항**:
  - 월별 선택 드롭다운에 "전체 기간" 옵션 추가
  - 모든 월의 매수 내역을 합산하여 전체 투자 현황 조회
  - CASH 항목 (일반적금, 주택청약 등)도 포함해야 함

- **주요 구현**:

  1. **월 선택 드롭다운** (`app.py:224-231`):
     - "전체 기간" 옵션 추가
     - 선택 시 모든 월 데이터 통합 조회

  2. **계좌별 포트폴리오 - "전체 기간" 지원** (`data_loader.py`):
     - **get_accounts()**: 계좌명 기준으로 통합 (account_id가 월마다 다름)
       ```python
       # 문제: 각 월마다 다른 account_id (11월: 60, 12월: 65)
       # 해결: 계좌명으로 GROUP BY하여 통합
       SELECT MAX(a.id), a.name, ...
       FROM accounts a
       GROUP BY a.name
       ```
     - **total_value 계산**: purchase_history(ETF/주식) + 최신 월 holdings(CASH)
     - **get_account_holdings()**:
       - purchase_history에서 ETF/주식 합산
       - 최신 월 holdings에서 CASH 항목 가져오기
       - 두 결과 병합

  3. **전체 포트폴리오 - "전체 기간" 지원**:
     - 최신 월 데이터 사용 (analyzed_holdings는 누적 스냅샷)

  4. **월별 투자 비교**:
     - "전체 기간" 제한 유지 (월별 비교 특성상)

- **핵심 설계 결정**:
  1. **옵션 B 채택**: 모든 월의 purchase_history 합산 (옵션 A: 최신 월만 vs 옵션 B: 전체 합산)
  2. **CASH 처리**: purchase_history에는 CASH 없음 → 최신 월 holdings에서 추가
  3. **계좌명 매칭**: account_id가 월마다 다르므로 계좌명(name)으로 매칭
  4. **데이터 병합**: pd.concat()로 ETF/주식 + CASH 병합

- **수정 파일**:
  - `app.py`: "전체 기간" 옵션 추가
  - `data_loader.py`: get_accounts(), get_account_holdings() 수정
  - `account_portfolio.py`: "전체 기간" 지원
  - `monthly_comparison.py`: 색상 표시 제거 (`:red[...]` 마크다운 → `+/-` 기호만)

- **기타 개선사항**:
  - 통합 보유 종목 Top 20: 티커 대신 종목명 우선 표시
  - 수익률 텍스트: 마크다운 제거 (st.dataframe에서 작동 안 함)

### Phase 13: 디렉터리 재구성 + 키보드 단축키 지원

- **요구사항**:
  - 파일들이 루트에 산재되어 있어 관리가 어려움
  - 도메인별로 디렉터리를 분리하여 구조 개선
  - 웹 대시보드에 키보드 단축키 추가로 사용성 향상

- **주요 구현**:

  1. **디렉터리 재구성** (기능별 분류):
     - `core/`: 핵심 비즈니스 로직 (analyze_portfolio.py, evaluate_accumulative.py)
     - `data/`: 데이터 레이어 (init_db.py, import_monthly_data.py, import_monthly_purchases.py, query_db.py)
     - `visualization/`: 시각화 (visualize_portfolio.py)
     - `scripts/`: 실행 스크립트 (run_monthly.py, run_all_months.py)
     - `streamlit_app/`: 웹 대시보드 (기존 유지)

  2. **import 경로 수정**:
     - `scripts/run_monthly.py`: 모든 import를 모듈 경로로 변경
       - `from data.init_db import init_database`
       - `from core.analyze_portfolio import analyze_month_portfolio`
       - `from visualization.visualize_portfolio import visualize_portfolio`
     - `scripts/run_all_months.py`: project_root 경로 수정 (`parent.parent`), import 경로 수정

  3. **키보드 단축키 지원** (`app.py`):
     - **라이브러리**: `streamlit_hotkeys` 사용
     - **페이지 이동**:
       - `1`: 월별 투자 비교
       - `2`: 계좌별 포트폴리오
       - `3`: 전체 포트폴리오
     - **월 선택**:
       - `→`: 다음 월
       - `←`: 이전 월
       - `F`: '전체 기간' 선택
     - **구현 방식**:
       ```python
       import streamlit_hotkeys as hotkeys

       # 단축키 정의
       hotkey_bindings = [
           hotkeys.hk("page_monthly", "1"),
           hotkeys.hk("month_prev", "ArrowLeft"),
           ...
       ]
       hotkeys.activate(hotkey_bindings)

       # 단축키 처리
       if hotkeys.pressed("page_monthly"):
           st.session_state.current_page = "월별 투자 비교"
           st.query_params["page"] = "monthly"
           st.rerun()
       ```

  4. **사이드바 네비게이션 개선**:
     - 커스텀 버튼으로 현재 페이지 강조 (primary/secondary 타입)
     - URL 쿼리 파라미터와 세션 상태 동기화
     - 단축키 안내 문구 추가

- **문서 업데이트**:
  - `README.md`: 디렉터리 구조 및 명령어 경로 수정
  - `AGENT.md`: 시스템 플로우 및 파일 경로 참조 수정
  - 모든 예제 명령어를 새로운 경로로 업데이트
    - `python run_monthly.py` → `python scripts/run_monthly.py`
    - `python import_monthly_data.py` → `python -m data.import_monthly_data`

- **의존성 추가**:
  - `requirements.txt`에 `streamlit-hotkeys` 추가 필요

- **개발 중 고려사항**:
  - 파이썬 모듈 import 방식 사용 (`python -m module.file`)
  - 기존 크론 작업이나 스크립트는 새로운 경로로 업데이트 필요
  - DB 파일과 app.py는 루트에 유지 (엔트리포인트)

---

**Last Updated**: 2025-12-26
**Version**: 1.5.0
**Maintainer**: AI Agent + Human

**Changelog (v1.5.0)**:
- **키보드 단축키 안정화** 🔥 **FIX!**
  - `streamlit-hotkeys` 라이브러리의 조합 키/리더 키 버그로 인해 단일 키 방식으로 최종 변경
  - `1,2,3`: 페이지 이동
  - `←, →`: 이전/다음 월 선택
  - `F`: '전체 기간' 선택
  - 수차례의 디버깅을 통해 안정적인 단축키 동작 확보

**Changelog (v1.4.0)**:
- **디렉터리 재구성** ✨ **NEW!**
  - 기능별로 디렉터리 분리 (core/, data/, visualization/, scripts/)
  - import 경로 전면 수정
  - 모듈 import 방식 사용 (`python -m module.file`)
  - 문서 전체 업데이트 (경로 참조 수정)
- **키보드 단축키 지원 (초기 버전)**
  - streamlit_hotkeys 라이브러리 사용
  - URL 쿼리 파라미터 기반 페이지 상태 관리
- 코드 구조 개선:
  - 관심사 분리 (Separation of Concerns)
  - 유지보수성 향상
  - 확장 가능한 아키텍처

**Changelog (v1.3.1)**:
- **"전체 기간" 통합 기능** ✨ **NEW!**
  - 월 선택 드롭다운에 "전체 기간" 옵션 추가
  - 모든 월의 매수 내역(purchase_history) 자동 합산
  - CASH 항목 지원 (purchase_history + 최신 월 holdings 병합)
  - 계좌명 기준 통합 (account_id 월별 불일치 해결)
- 통합 보유 종목 Top 20: stock_name 우선 표시 (티커 대신)
- 수익률 텍스트 표시 개선: 마크다운 제거 (`+/-` 기호만 사용)
- 버그 수정: "전체 기간" 선택 시 CASH 항목 누락 문제 해결

**Changelog (v1.3.0)**:
- **Streamlit 웹 대시보드 구축** ✨ **NEW!**
  - 인터랙티브 웹 기반 포트폴리오 분석 대시보드
  - 3개 페이지: 월별 투자 비교, 계좌별 포트폴리오, 전체 포트폴리오
  - Plotly 차트 사용 (Waterfall, Sunburst, Pie, Bar, Line)
  - 캐싱 전략 (ETF 24시간, 월별 1시간)
  - ETF 투시 토글 방식 (성능 최적화)
  - 한국 주식 자동 종목명 표시
  - 종목 검색 기능 (직접 + ETF 통한 간접 보유 통합)
- 문서화 완료:
  - streamlit_app/README.md: 사용 가이드
  - streamlit_app/ARCHITECTURE.md: 아키텍처 문서
  - designs/: UI 디자인 문서 (5개 파일)
- requirements.txt 업데이트 (streamlit, plotly 추가)

**Changelog (v1.2.0)**:
- 개별 주식 지원 추가 (AMZN, GOOGL, TSLA 등)
  - quoteType 필드로 ETF/개별주식 자동 구분
  - 개별 주식은 100% 자기 보유 + 섹터 자동 조회
- 적립식 투자 추적 시스템 구축
  - purchase_history 테이블 추가 (수량 기반 추적)
  - current_holdings_summary 뷰 추가
  - import_monthly_purchases.py: 과거 주가 조회 및 수량 계산
  - evaluate_accumulative.py: 현재가 기준 평가액 계산
  - year_month 이중 형식 처리 (DB 조회용 vs 날짜 생성용)
  - account_id 필수 저장 (계좌별 매수 이력 추적)
- DB 마이그레이션 스크립트 추가 (migrate_add_purchase_history.py)
- README.md 및 AGENT.md 문서화 완료

**Changelog (v1.1.0)**:
- TOP 30 → TOP 50 확장
- 한국 주식 실제 종목명 표시 기능 추가
- 다중 ETF 출처 추적 기능 추가
- OTHER 항목 맨 마지막 표시 개선
- 초장형 차트 레이아웃 (TOP 50 지원)
- requirements.txt 추가
