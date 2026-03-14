# Agent Development Guide

이 문서는 AI 에이전트 및 개발자가 프로젝트를 이해하고 수정할 때 참고하는 가이드입니다.

## 아키텍처 개요

### 시스템 플로우

```
YAML 데이터 작성
    ↓
[Step 1] data/importer.py (YAML → months, accounts, holdings + 주가 조회 → purchase_history)
    ↓
[Step 2] core/analyze_portfolio.py (yfinance → ETF 분석 → analyzed_holdings, analyzed_sectors)
    ↓
[Step 3] visualization/visualize_portfolio.py (core/portfolio_data → Matplotlib 차트)
    ↓
charts/*.png (최종 출력)

[별도] core/evaluate_accumulative.py (purchase_history 합산 → 현재가 평가)
```

### 파이프라인 상세 (`python run.py` 실행 시)

| 순서 | 모듈 | 역할 | DB 반영 테이블 | 예시 (SPY 30만원, 2026-01, 26일 기준) |
|---|---|---|---|---|
| Step 1 | `data.importer.import_month()` | YAML → DB 통합 임포트 | `months`, `accounts`, `holdings`, `purchase_history` | YAML 원본 저장 + 수량 계산 (`quantity=0.3507`) |
| Step 2 | `core.analyze_portfolio` | yfinance로 ETF 내부 분석 | `analyzed_holdings`, `analyzed_sectors` | `source="SPY"`, `symbol="AAPL"`, `my_amount=21000` |
| Step 3 | `visualization.visualize_portfolio` | 데이터 조회 + 차트 생성 | (DB 변경 없음) | `charts/2026-01_asset_allocation.png` 등 4종 |
| 별도 | `core.evaluate_accumulative` | 전체 수량 합산 → 현재가 평가 | (DB 변경 없음) | SPY 1.0469주 × 현재가 876,000원 = 917,085원 |

**자동 스킵**: `run.py`는 이미 임포트/분석된 월은 자동으로 건너뛴다. `--force`로 강제 재실행 가능.

### 테이블별 역할 요약

| 테이블 | 작성 단계 | 저장 내용 |
|---|---|---|
| `months` | Step 1 | 월 ID, 환율 |
| `accounts` | Step 1 | 계좌 정보 (월마다 새로 생성) |
| `holdings` | Step 1 | 사용자 입력 원본 — "SPY에 30만원 넣었다" |
| `purchase_history` | Step 1 | 수량 기록 — "30만원으로 SPY 0.3507주 샀다" (수량 불변) |
| `analyzed_holdings` | Step 2 | ETF 내부 분석 — "30만원 중 AAPL이 7%, 즉 21,000원" |
| `analyzed_sectors` | Step 2 | 섹터 비중 — "technology 32%, healthcare 13%" |
| `current_holdings_summary` | (뷰) | purchase_history를 종목별로 자동 집계 |

### 핵심 컴포넌트

1. **통합 CLI** (`run.py`): import → analyze → visualize 파이프라인 (자동 스킵)
2. **데이터 레이어** (`data/`): init_db.py, importer.py
3. **공통 데이터 조회** (`core/portfolio_data.py`): CLI/Web 공용 데이터 쿼리
4. **분석 레이어** (`core/`): analyze_portfolio.py, evaluate_accumulative.py, interest_calculator.py
5. **시각화 레이어** (`visualization/`): visualize_portfolio.py (Matplotlib 차트 4종, portfolio_data 소비)
6. **웹 대시보드 레이어** (`streamlit_app/`): data_loader.py (캐싱 래퍼), [상세 문서](./streamlit_app/ARCHITECTURE.md)

## 핵심 설계 결정

### 1. 자산 유형 분류 (asset_type)

- `STOCK`: yfinance로 ETF holdings/sectors 조회
- `BOND`: yfinance 시도 → 실패 시 "Fixed Income" 섹터로 대체
- `CASH`: yfinance 조회 없이 "Cash & Equivalents" 섹터로 직접 처리
- 코드 위치: `core/analyze_portfolio.py:440-540` — `analyze_stock_asset()`, `analyze_bond_asset()`, `analyze_cash_asset()`

### 2. 기타 종목 (OTHER) 처리

yfinance `top_holdings`는 상위 10개만 제공. `calculate_my_holdings()`에서 비중 합계 < 1.0이면 나머지를 "OTHER"로 자동 추가.

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

OTHER 항목은 SQL `ORDER BY`에서 `CASE WHEN stock_symbol = 'OTHER' THEN 1 ELSE 0 END`로 항상 마지막에 표시.

### 3. 같은 Ticker 통합

STOCK/BOND는 `stock_symbol`로 GROUP BY하여 자동 통합 (예: "ACE 미국국채30년액티브" + "미국채 30년" → TLT로 합산)

```sql
-- core/analyze_portfolio.py:916-934
SELECT
    CASE WHEN asset_type IN ('STOCK', 'BOND') THEN stock_symbol ELSE stock_name END as display_name,
    asset_type, SUM(my_amount) as amount
FROM analyzed_holdings
WHERE month_id = ? AND account_id IS NULL
GROUP BY CASE WHEN asset_type IN ('STOCK', 'BOND') THEN stock_symbol ELSE stock_name END, asset_type
```

### 4. target_ratio 자동 계산

`data/importer.py`의 `_import_portfolio()`에서 계좌별 총액 대비 각 holding의 비중을 자동 계산.

### 5. 한국 주식 실제 종목명 표시

`.KS` 확장자로 한국 주식 자동 감지, `stock_name`으로 실제 회사명 표시 (예: `005930.KS` → `삼성전자 (005930.KS)`)

### 6. 다중 ETF 출처 추적

`GROUP_CONCAT(DISTINCT source_ticker)` SQL로 여러 ETF 출처 연결 (예: `AAPL [from: SPY,QQQ]`)

### 7. 개별 주식 감지

`quoteType == 'EQUITY'`이면 개별 주식으로 처리: 자기 자신 100% 보유, 섹터는 `info.get('sector')`에서 조회.

## 데이터베이스 설계

### ER 다이어그램

```
months (월별 기본 정보)
  ↓ 1:N
accounts (계좌)
  ↓ 1:N
  ├─ holdings (보유 항목: 원본 데이터)
  └─ purchase_history (적립식 투자 매수 이력)

months
  ↓ 1:N
analyzed_holdings (분석 결과: 개별 종목)
analyzed_sectors (분석 결과: 섹터 비중)

purchase_history
  ↓ aggregation
current_holdings_summary (뷰: 종목별 보유 수량 집계)
```

### 주요 테이블

#### holdings
- 사용자 입력 데이터 (YAML에서 임포트)
- `asset_type`: STOCK/BOND/CASH, `interest_rate`: 현금 자산의 이자율

#### analyzed_holdings
- ETF 분석 결과
- `source_ticker`: 원본 ETF, `stock_symbol`: 개별 종목 ticker, `asset_type`: 자산 유형 (분석 시 상속)

#### analyzed_sectors
- 섹터별 비중: `sector_name` (technology, Fixed Income, Cash & Equivalents 등)

#### purchase_history
- **적립식 투자 매수 이력** (수량 기반 추적)
- 핵심 필드: `ticker`, `quantity` (REAL, 불변), `input_amount`, `purchase_date`, `price_at_purchase` (감사용), `currency`, `exchange_rate`, `account_id` (FK, 필수), `year_month`, `asset_type`, `interest_rate`, `interest_type`
- 설계 원칙: 수량 불변, price_at_purchase는 감사용만, 평가액은 항상 `quantity × current_price`로 실시간 계산

#### current_holdings_summary (뷰)
- purchase_history를 종목별로 집계: `ticker`, `total_quantity`, `total_invested`, `avg_price`

### account_id 컬럼의 의미
- `account_id IS NULL`: 전체 포트폴리오 통합 분석 결과
- `account_id = 1, 2, ...`: 개별 계좌 분석 결과
- purchase_history에서는 account_id 필수 (NULL이면 안 됨)

## 주요 함수 설명

### core/analyze_portfolio.py

| 함수 | 설명 |
|------|------|
| `fetch_etf_holdings(ticker)` | yfinance로 ETF top_holdings 조회 (상위 10개) |
| `calculate_my_holdings(etf_ticker, my_investment, holdings_df)` | ETF holdings를 내 투자금액 기준으로 계산. 비중 합계 < 1.0이면 "OTHER" 추가 |
| `analyze_stock_asset(ticker, name, amount, ...)` | 주식형 ETF/개별 주식 분석. `quoteType == 'EQUITY'`이면 개별 주식으로 처리 |
| `analyze_bond_asset(...)` | 채권형 ETF 분석. yfinance 실패 시 Fixed Income 섹터로 대체 |
| `analyze_cash_asset(...)` | 현금성 자산. yfinance 조회 없이 Cash & Equivalents 섹터로 직접 저장 |
| `print_integrated_analysis(month_id, db_path)` | 통합 포트폴리오 분석 결과 출력 (Net Worth + 섹터 + holdings TOP 50) |

### data/importer.py

| 함수 | 설명 |
|------|------|
| `import_month(yaml_path, db_path, purchase_day, overwrite)` | YAML → DB 통합 임포트 (계좌/보유종목 + 매수기록) |
| `get_historical_price(ticker, target_date, max_lookback_days=7)` | yfinance로 특정 날짜 종가 조회. 휴일 시 직전 영업일 |
| `get_price_from_db(ticker, target_date, db_path)` | DB 과거 기록에서 유사 날짜(±7일) 주가 검색 (yfinance 폴백) |
| `calculate_quantity(ticker, input_amount, year_month, purchase_day, db_path)` | 투자 금액 → 수량 계산. 환율 적용 (USD만) |
| `save_purchase(...)` | purchase_history 테이블 저장. account_name으로 account_id 조회 |

### core/portfolio_data.py (공통 데이터 조회 레이어)

| 함수 | 설명 |
|------|------|
| `get_month_id(year_month, db_path)` | year_month → month_id 조회 |
| `get_available_months(db_path)` | 사용 가능한 월 목록 (내림차순) |
| `calc_cash_value(db_path, month_id, up_to_month)` | CASH 자산 이자 반영 평가액 계산 |
| `get_asset_allocation(month_id, db_path)` | 자산유형별 배분 (analyzed_holdings 기반) |
| `get_sector_distribution(month_id, db_path, limit)` | 섹터별 분포 (상위 N개) |
| `get_top_holdings(month_id, db_path, limit)` | 상위 보유종목 (OTHER 제외) |
| `get_cumulative_value(up_to_month, db_path)` | 누적 투자원금/평가금액/수익 (실시간 시세) |
| `get_asset_trend(db_path, months)` | 월별 자산 추이 DataFrame |

### core/evaluate_accumulative.py

| 함수 | 설명 |
|------|------|
| `evaluate_holdings(db_path)` | 종목별 보유 수량 집계 → 현재가 조회 → 평가액/손익/수익률 계산 |
| `get_current_price(ticker)` | yfinance 현재가 조회. 한국 주식: KRW, 미국: USD → KRW 환산 |

## 수익률 계산 상세

### 핵심 공식

모든 모듈에서 동일한 단순 수익률(Simple Return) 공식 사용:

```
수익률(%) = (평가액 - 투자액) / 투자액 × 100
평가액 = 보유수량 × 현재가(KRW)
```

### 수익률 계산 지점 (6곳)

| 파일 | 함수 | 용도 |
|---|---|---|
| `core/evaluate_accumulative.py` | `evaluate_holdings()` | CLI 적립식 평가 |
| `streamlit_app/data_loader.py` | `get_monthly_summary()` | 월별 요약 |
| `streamlit_app/data_loader.py` | `get_account_holdings()` | 계좌별 종목 |
| `streamlit_app/data_loader.py` | `get_total_top_holdings()` | 통합 포트폴리오 Top 20 |
| `streamlit_app/data_loader.py` | `get_monthly_holdings_comparison()` | 월별 비교 |
| `streamlit_app/utils/price_fetcher.py` | `calculate_profit_rate()` | 유틸 함수 |

### 현재가 조회 방식 차이

| 모듈 | 반환값 | 환율 처리 |
|---|---|---|
| `evaluate_accumulative.get_current_price()` | KRW (환율 적용 완료) | 내부에서 USD × 환율 적용 |
| `price_fetcher.get_current_price()` | 원시 가격 (USD/KRW 그대로) | 호출자가 별도 환율 적용 |

### 알려진 불일치 사항

1. **환율 기본값**: 모든 모듈에서 `DEFAULT_EXCHANGE_RATE = 1450` 사용 (`core/portfolio_data.py`에서 정의)
2. **현재가 조회 실패 시**: `evaluate_accumulative`는 해당 종목 제외, `data_loader`는 원금=평가액(수익률 0%)
3. **account_id NULL**: `evaluate_accumulative`는 영향 없음, `data_loader`는 accounts JOIN으로 누락 가능

## 테스트

### 실행 방법

```bash
.venv/bin/pytest tests/ -v
.venv/bin/pytest tests/test_profit_rate.py -v
```

### 테스트 구조

```
tests/
├── conftest.py                  # 공통 픽스처 (인메모리 DB, yfinance mock)
├── test_profit_rate.py          # 수익률 공식 (엣지 케이스 포함)
├── test_calculate_quantity.py   # 투자액→수량 변환, 환율, 폴백
├── test_portfolio_value.py      # 포트폴리오 평가액 (CASH 이자 반영)
├── test_evaluate_holdings.py    # E2E 수익률 계산 (DB→현재가→수익률)
├── test_monthly_summary.py      # 월별 요약, 빈 DB
├── test_current_price.py        # 현재가 조회 (2개 모듈 차이 검증)
├── test_db_aggregation.py       # DB 집계, NULL account_id 영향
└── test_consistency.py          # 모듈 간 수익률 일관성 검증
```

### 주요 픽스처 (conftest.py)

| 픽스처 | 설명 |
|---|---|
| `initialized_db` | 빈 스키마만 생성된 DB |
| `populated_db` | 2개월, 2개 계좌, 미국/한국 주식 + CASH |
| `mock_yfinance` | yfinance.Ticker mock (SPY=610, QQQ=520, KODEX200=36000, KRW=X=1430) |
| `mock_yf_download` | yfinance.download mock (일괄 조회) |

### 테스트 작성 시 주의

- 외부 API(yfinance)는 반드시 mock 처리
- `data_loader.py`의 캐시 데코레이터 → `__wrapped__`로 원본 함수 호출
- `data_loader`에서 `get_current_price`, `get_multiple_prices`는 함수 내부 import → mock 경로는 `streamlit_app.utils.price_fetcher`

## 주의사항

### yfinance API 제한

1. **top_holdings 상위 10개만** → "OTHER" 항목으로 보정
2. **채권 ETF holdings 없음** → "Fixed Income" 섹터 대체
3. **환율(KRW=X) 조회 실패 가능** → 기본값 1,450원
4. **개별 주식 funds_data 없음** → quoteType으로 구분
5. **과거 주가 조회 실패 가능** → DB 폴백

### DB 무결성

1. **months.year_month UNIQUE** → 재임포트 시 `--overwrite` 필수
2. **account_id IS NULL** = 전체 분석 (계좌별 분석과 별도 저장)
3. **analyzed_* overwrite 시 DELETE** → 중복 저장 방지
4. **purchase_history.account_id 필수** (NULL 금지)
5. **year_month 이중 형식**: DB 조회용 `"2025-11-purchase"` vs 날짜 생성용 `"2025-11"` — 혼동 금지

### 적립식 투자 핵심 규칙

- **CASH 제외**: purchase_history에 CASH는 저장되지 않음 (`quantity = amount, price = 1.0`)
- **파일 명명**: 일반 `2025-11.yaml`, 적립식 `2025-11-purchase.yaml`
- **purchase_day 우선순위**: YAML `purchase_day` > CLI `--purchase-day` > 기본값 26

## 트러블슈팅 가이드

### 총 자산이 원금보다 적음
```bash
sqlite3 portfolio.db "SELECT asset_type, SUM(my_amount) FROM analyzed_holdings WHERE month_id = X AND account_id IS NULL GROUP BY asset_type"
```
→ "OTHER" 항목 추가 로직 확인 (`calculate_my_holdings()`)

### 같은 ticker가 중복 표시
→ GROUP BY에서 stock_name 대신 stock_symbol 사용 확인 (`calculate_integrated_holdings()`)

## 개발 이력

| Phase | 내용 |
|-------|------|
| 1 | 기본 시스템 구축 (SQLite, YAML 임포트, yfinance 연동) |
| 2 | 자산 유형 확장 (STOCK/BOND/CASH) |
| 3 | 통합 Net Worth 뷰 |
| 4 | OTHER 종목 처리 (yfinance top_holdings 보정) |
| 5 | Ticker 통합 (같은 ETF 합산) |
| 6 | Matplotlib 시각화 4종 |
| 7 | 자동화 (run_monthly.py, 크론) |
| 8 | 상세 분석 개선 (TOP 50, 한국 주식명, 다중 ETF 추적) |
| 9 | 개별 주식 지원 (quoteType 감지) |
| 10 | 적립식 투자 추적 시스템 (purchase_history, evaluate_accumulative) |
| 11 | Streamlit 웹 대시보드 (Plotly 차트, 캐싱, 3페이지) |
| 12 | "전체 기간" 통합 기능 |
| 13 | 디렉터리 재구성 + 키보드 단축키 |
| 14 | 리팩터링: 임포트 통합(`data/importer.py`), 스크립트 통합(`run.py`), 공통 데이터 레이어(`core/portfolio_data.py`), `analysis_metadata` 제거, 환율 기본값 1450 통일 |

## 체크리스트

새로운 기능 추가 시:
- [ ] 테이블 스키마 변경 → `data/init_db.py` 업데이트
- [ ] 핵심 로직 추가 (`core/` 또는 `data/`)
- [ ] 단위 테스트 추가 (`tests/`)
- [ ] 전체 테스트 실행 및 통과 확인 (`pytest tests/ -v`)
- [ ] 전체 플로우 테스트 (`python run.py --month YYYY-MM`)
- [ ] README.md 업데이트
- [ ] AGENT.md 업데이트

코드 수정 시 주의:
- [ ] import 경로가 올바른지 확인 (모듈 경로 사용)
- [ ] 파일 이동 시 모든 참조 업데이트
- [ ] 웹 대시보드에서 정상 작동 확인

## 참고 자료

- [yfinance](https://github.com/ranaroussi/yfinance): `etf.funds_data.top_holdings`, `etf.funds_data.sector_weightings`
- [SQLite](https://www.sqlite.org/docs.html): CASE WHEN, GROUP BY, NULL handling
- [Streamlit](https://docs.streamlit.io): 웹 프레임워크
- [Plotly](https://plotly.com/python/): 인터랙티브 차트
