# 📊 Stock Portfolio Routine

개인 투자 포트폴리오 통합 분석 시스템
주식형 ETF, 채권, 현금성 자산을 모두 포함한 Net Worth 분석 및 리포트 자동화

## 🔒 프라이버시 설정 (GitHub 공개 시)

이 프로젝트를 GitHub에 공개할 때 실제 투자 금액이 노출되지 않도록 다음 설정이 적용되어 있습니다:

### 자동 제외 항목 (.gitignore)
- `monthly/*.yaml` - 실제 투자 데이터 파일
- `portfolio.db` - 투자 내역이 저장된 데이터베이스
- `charts/*.png` - 생성된 차트 이미지 (재생성 가능)

### 예시 파일 제공
- `monthly/example-2025-01.yaml` - 상세한 주석이 포함된 예시 파일
- 다양한 계좌 및 자산 유형 포함 (ISA, IRP, 연금저축, 일반, 현금)
- 실제 데이터 파일 생성 가이드 제공

### 실제 데이터 파일 생성 방법

1. 예시 파일 복사:
```bash
cp monthly/example-2025-01.yaml monthly/2025-01.yaml
```

2. 실제 투자 금액으로 수정:
```bash
# 텍스트 에디터로 monthly/2025-01.yaml 수정
# amount 값을 실제 투자 금액으로 변경
```

3. 분석 실행:
```bash
python scripts/run_monthly.py --month 2025-01 --yaml monthly/2025-01.yaml
```

4. Git에서 제외 확인:
```bash
git status  # monthly/*.yaml이 Untracked files에 없어야 함
```

### 주의사항

- `monthly/` 디렉토리에 실제 데이터 파일을 생성해도 Git에 추적되지 않습니다
- `example-`로 시작하는 파일만 Git에 포함됩니다
- 실수로 커밋하지 않도록 커밋 전 항상 `git status`로 확인하세요

---

## ✨ 주요 기능

### 1. 통합 자산 분석
- **다중 계좌 지원**: ISA, IRP, 연금저축, 일반 계좌 등 모든 계좌 통합 관리
- **다양한 자산 유형**: 주식형 ETF, 채권형 ETF, 개별 주식, 현금성 자산(적금, 청약) 포함
- **실시간 ETF 분석**: yfinance를 통한 ETF 내부 구성 종목 및 섹터 분석
- **개별 주식 지원**: AMZN, GOOGL, TSLA 등 개별 종목 자동 감지 및 분석
- **적립식 투자 추적**: 월별 투자 금액 → 수량 자동 계산 → 현재가 기준 평가
- **환율 자동 적용**: 미국 ETF/주식의 원화 환산 자동 계산

### 2. 상세 분석 리포트
- **계좌별 분석**: 각 계좌의 자산 구성 및 섹터 비중
- **전체 포트폴리오 분석**: 모든 계좌를 통합한 전체 자산 분석
- **Net Worth 뷰**: 위험 자산(주식)/안전 자산(채권)/현금 비중
- **통합 섹터 분석**: 주식 섹터 + Fixed Income + Cash & Equivalents
- **Top Holdings**: 개별 종목/채권/현금 상품을 금액 순으로 표시

### 3. 시각화
- **자산 배분 도넛 차트**: 주식형/채권형/현금형 비중
- **섹터별 막대 차트**: 상위 10개 섹터 금액 분포
- **Top Holdings 차트**: 상위 50개 보유 항목 (한국 주식은 실제 종목명 표시)
- **자산 추이 차트**: 월별 총 자산 변화 (2개월 이상 데이터 필요)

### 4. 적립식 투자 추적 시스템 (Accumulative Investment)
- **수량 기반 관리**: 투자 금액 입력 → 과거 주가 조회 → 수량 자동 계산 및 저장
- **불변 수량**: 한 번 저장된 수량은 변경되지 않음 (영구 기록)
- **평가액 계산**: 보유 수량 × 현재가로 실시간 평가
- **과거 주가 조회**: yfinance를 통한 특정 날짜 주가 조회 (휴일 시 직전 영업일)
- **DB 폴백**: yfinance 실패 시 과거 매수 기록에서 유사 날짜 주가 조회
- **계좌 연동**: purchase_history 테이블에 account_id 저장으로 계좌별 매수 이력 추적

### 5. 자동화
- **월별 스냅샷**: YAML 파일로 월별 포트폴리오 상태 기록
- **크론 연동**: 통합 스크립트로 데이터 임포트 → 분석 → 시각화 자동 실행
- **SQLite DB**: 모든 분석 결과를 DB에 저장하여 이력 관리

## 🏗 시스템 구조

```
stock-routine/
├── core/                              # 핵심 비즈니스 로직
│   ├── analyze_portfolio.py           # 포트폴리오 분석 (핵심)
│   └── evaluate_accumulative.py       # 적립식 투자 평가 (수량 × 현재가)
├── data/                              # 데이터 레이어
│   ├── init_db.py                     # DB 초기화
│   ├── import_monthly_data.py         # YAML → DB 임포트 (계좌/보유 항목)
│   ├── import_monthly_purchases.py    # 적립식 투자 수량 계산 및 저장
│   └── query_db.py                    # DB 쿼리 유틸리티
├── visualization/                     # 시각화
│   └── visualize_portfolio.py         # 차트 생성
├── scripts/                           # 실행 스크립트
│   ├── run_monthly.py                 # 통합 실행 스크립트 (크론용)
│   └── run_all_months.py              # 전체 월 일괄 실행
├── streamlit_app/                     # 웹 대시보드
│   ├── components/                    # Plotly 차트 컴포넌트
│   ├── pages/                         # 페이지별 렌더링
│   ├── utils/                         # 유틸리티
│   ├── config.py                      # 설정
│   └── data_loader.py                 # 데이터 로딩 및 캐싱
├── monthly/                           # 월별 데이터
│   ├── README.md                      # YAML 형식 설명서
│   ├── 2025-11-purchase.yaml          # 11월 적립식 투자 데이터
│   ├── 2025-12.yaml                   # 12월 포트폴리오
│   └── 2026-01.yaml                   # 1월 포트폴리오
├── charts/                            # 생성된 차트
│   ├── 2025-12_asset_allocation.png
│   ├── 2025-12_sectors.png
│   ├── 2025-12_top_holdings.png
│   └── asset_trend.png
├── app.py                             # Streamlit 앱 엔트리포인트
├── portfolio.db                       # SQLite 데이터베이스
└── requirements.txt                   # 의존성 목록
```

## 🔄 파이프라인 요약 (run_monthly.py 실행 시)

`run_monthly.py`를 실행하면 아래 4단계가 순서대로 실행되며, 각 단계에서 다른 DB 테이블에 데이터가 저장됩니다.

| 순서 | 스크립트 | 역할 | DB 반영 테이블 | 예시 (SPY 30만원, 2026-01, 26일 기준) |
|---|---|---|---|---|
| Step 1 | `import_monthly_data` | YAML 원본 데이터 저장 | `months`, `accounts`, `holdings` | `ticker="SPY"`, `amount=300000`, `asset_type="STOCK"` |
| Step 2 | `import_monthly_purchases` | 주가 조회 → 수량 계산 | `purchase_history` | `ticker="SPY"`, `quantity=0.3507`, `purchase_date="2026-01-26"` |
| Step 3 | `analyze_portfolio` | yfinance로 ETF 내부 분석 | `analyzed_holdings`, `analyzed_sectors`, `analysis_metadata` | `source="SPY"` → `symbol="AAPL"`, `my_amount=21000` |
| Step 4 | `visualize_portfolio` | DB → 차트 이미지 생성 | (DB 변경 없음) | `charts/2026-01_*.png` |
| 별도 | `evaluate_accumulative` | 전체 수량 합산 → 현재가 평가 | (DB 변경 없음) | SPY 1.0469주 × 현재가 = 917,085원 (+1.9%) |

### 테이블별 역할

| 테이블 | 작성 단계 | 저장 내용 |
|---|---|---|
| `holdings` | Step 1 | 사용자 입력 원본 — "SPY에 30만원 넣었다" |
| `purchase_history` | Step 2 | 수량 기록 — "30만원으로 SPY 0.3507주 샀다" |
| `analyzed_holdings` | Step 3 | ETF 내부 분석 — "30만원 중 AAPL이 7%, 즉 21,000원" |

## 📋 데이터베이스 스키마

### months 테이블
- 월별 기본 정보 (year_month, exchange_rate)

### accounts 테이블
- 계좌 정보 (name, type, broker, fee)

### holdings 테이블
- 계좌별 보유 항목 (name, ticker_mapping, amount, target_ratio, asset_type, interest_rate)

### purchase_history 테이블
- **적립식 투자 매수 이력** (수량 기반 추적)
- 주요 필드:
  - `ticker`: 종목 코드
  - `quantity`: 매수 수량 (불변)
  - `input_amount`: 투자 금액
  - `purchase_date`: 실제 매수일
  - `price_at_purchase`: 매수 당시 주가 (선택, 감사용)
  - `currency`: 통화 (KRW/USD)
  - `exchange_rate`: 환율 (USD 종목만)
  - `account_id`: 계좌 ID (FK)
  - `year_month`: 귀속 월 (예: 2025-11-purchase)

### current_holdings_summary 뷰
- purchase_history를 종목별로 집계한 뷰
- `ticker`, `total_quantity`, `total_invested`, `avg_price`

### analyzed_holdings 테이블
- ETF 분석 결과: 개별 종목 보유 내역 (stock_symbol, stock_name, holding_percent, my_amount, asset_type)

### analyzed_sectors 테이블
- ETF 분석 결과: 섹터별 비중 (sector_name, sector_percent, my_amount, asset_type)

### analysis_metadata 테이블
- 분석 메타데이터 (ticker, status, error_message)

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 가상환경 생성 (권장)
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
# 또는 개별 설치: pip install yfinance pandas pyyaml matplotlib

# DB 초기화
python -m data.init_db
```

### 2. 월별 데이터 준비

`monthly/2025-12.yaml` 파일 작성:

```yaml
accounts:
  - name: "투자 (절세)"
    type: "ISA"
    broker: "토스증권"
    fee: 0.0015  # 연 0.15%
    holdings:
      - name: "ACE 미국 S&P 500"
        ticker_mapping: "SPY"
        amount: 300000
        asset_type: "STOCK"

      - name: "ACE 미국국채30년액티브 (환노출)"
        ticker_mapping: "TLT"
        amount: 200000
        asset_type: "BOND"

      - name: "일반적금"
        ticker_mapping: "CASH"
        amount: 300000
        asset_type: "CASH"
        interest_rate: 0.077  # 연 7.7%
```

자세한 YAML 형식은 `monthly/README.md` 참고

### 3. 분석 실행

#### 워크플로우 A: 통합 스크립트 사용 (전체 분석, 추천)

```bash
python scripts/run_monthly.py --month 2025-12 --yaml monthly/2025-11-purchase.yaml
```

#### 워크플로우 B: 적립식 투자 전용 (개별 스크립트)

```bash
# 1단계: 계좌/보유 항목 임포트
python -m data.import_monthly_data monthly/2025-11-purchase.yaml --overwrite

# 2단계: 적립식 투자 수량 계산 및 저장
python -m data.import_monthly_purchases monthly/2025-11-purchase.yaml --purchase-day 26

# 3단계: 적립식 투자 평가 (수량 × 현재가)
python -m core.evaluate_accumulative
```

#### 워크플로우 C: 전체 분석 (개별 스크립트)

```bash
# 1단계: 계좌/보유 항목 임포트
python -m data.import_monthly_data monthly/2025-11-purchase.yaml --overwrite

# 2단계: 포트폴리오 분석 (ETF holdings/sectors)
python -m core.analyze_portfolio --month 2025-11-purchase --overwrite

# 3단계: 시각화
python -m visualization.visualize_portfolio --month 2025-11-purchase
```

### 4. 결과 확인

```bash
# 터미널에 분석 결과 출력
# charts/ 디렉토리에 차트 이미지 생성

ls charts/
# 2025-12_asset_allocation.png
# 2025-12_sectors.png
# 2025-12_top_holdings.png
# asset_trend.png (2개월 이상 데이터 시)
```

## ⚙️ 크론 자동화

### 매월 1일 오전 9시 자동 실행

```bash
# crontab -e
0 9 1 * * cd /path/to/stock-routine && .venv/bin/python scripts/run_monthly.py --month $(date +\%Y-\%m) --yaml monthly/$(date +\%Y-\%m).yaml >> logs/cron.log 2>&1
```

### 크론 로그 확인

```bash
mkdir logs
tail -f logs/cron.log
```

## 📊 주요 출력 예시

### Net Worth 섹션

```
💰 [종합 자산 요약 - Net Worth]
- 총 자산: 1,469,982원

1. 위험 자산 (주식형)    :    819,982원 ( 55.8%)
2. 안전 자산 (채권형)    :    300,000원 ( 20.4%)
3. 현금성 자산 (적금)    :    350,000원 ( 23.8%)
```

### 통합 섹터 비중

```
📊 [전체 포트폴리오 - 통합 섹터 비중]
📈 technology              :  23.6% (자산내  42.4%)
💵 Cash & Equivalents      :  23.8% (자산내 100.0%)
📊 Fixed Income            :  20.4% (자산내 100.0%)
📈 communication_services  :   6.0% (자산내  10.8%)
```

### 통합 보유 상위 항목

```
🏆 [통합 보유 상위 항목 (TOP 50)]
🥇 [채권] TLT                              :    300,000원 ( 20.4%)
🥈 [현금] 일반적금                             :    300,000원 ( 20.4%)
🥉 [주식] 삼성전자 (005930.KS)                 :    150,000원 ( 10.2%)
   [주식] NVDA [from: SPY,QQQ]             :     49,190원 (  3.3%)
   [주식] AAPL [from: SPY,QQQ]             :     47,205원 (  3.2%)
...
--------------------------------------------------------------------------------
📦 [ETF 내 기타 종목 요약]
(* yfinance는 ETF 상위 10개 종목만 제공하므로, 나머지를 합산)
   기타 종목 (상위 10개 외):    434,389원 ( 29.6%)
   출처 ETF: SPY, QQQ
```

## 🔧 고급 기능

### 1. 적립식 투자 시스템 (Accumulative Investment)

#### 핵심 개념
- **수량 불변성**: 투자 금액을 입력하면 자동으로 수량이 계산되어 DB에 저장됨. 한번 저장된 수량은 변경되지 않음
- **평가액 실시간 계산**: `보유 수량 × 현재가`로 실시간 평가액 계산
- **과거 주가 자동 조회**: 특정 날짜(기본 26일)의 종가를 yfinance로 조회, 실패 시 DB에서 유사 날짜 주가 검색

#### 파일 명명 규칙
- 일반 월별 포트폴리오: `2025-11.yaml`, `2025-12.yaml`
- 적립식 투자 데이터: `2025-11-purchase.yaml`, `2025-12-purchase.yaml`

#### year_month 이중 형식
시스템 내부적으로 두 가지 형식 사용:
- **DB 조회용**: `2025-11-purchase` (months, accounts 테이블 조회용)
- **날짜 생성용**: `2025-11` (purchase_date 생성용, 예: `2025-11-26`)

#### YAML 구조
기존 `accounts > holdings` 구조를 그대로 사용:
```yaml
accounts:
  - name: "투자 (절세)"
    type: "ISA"
    broker: "신한투자증권"
    fee: 0.0
    holdings:
      - name: "ACE 미국 S&P 500"
        ticker_mapping: "SPY"
        amount: 300000  # 이번 달 투자 금액 (원화)
        asset_type: "STOCK"
```

**중요**: CASH 자산은 수량 개념이 없어 자동으로 제외됨

#### 사용 예시
```bash
# 1. 11월 적립식 투자 데이터 임포트
python -m data.import_monthly_data monthly/2025-11-purchase.yaml --overwrite

# 2. 수량 계산 및 purchase_history 저장 (26일 기준)
python -m data.import_monthly_purchases monthly/2025-11-purchase.yaml --purchase-day 26

# 3. 현재 보유 수량 및 평가액 확인
python -m core.evaluate_accumulative

# 출력 예시:
# 📊 적립식 투자 현황
#
# SPY         : 보유 1.2345주 | 투자 300,000원 | 현재 320,000원 | +20,000원 (+6.7%)
# QQQ         : 보유 0.5678주 | 투자 200,000원 | 현재 195,000원 | -5,000원 (-2.5%)
# ...
```

### 2. 개별 주식 지원 (Individual Stocks)

#### 자동 감지
- `yfinance`의 `quoteType` 필드로 ETF와 개별 주식 자동 구분
- `quoteType == 'EQUITY'` → 개별 주식
- `quoteType == 'ETF'` → ETF

#### 분석 방식
- **개별 주식**: 자기 자신을 100% 보유한 것으로 처리, 섹터는 `info.get('sector')`에서 조회
- **ETF**: 기존 로직 (funds_data.top_holdings, funds_data.sector_weightings)

#### 지원 종목
- AMZN (Amazon.com Inc)
- GOOGL (Alphabet Inc Class A)
- TSLA (Tesla Inc)
- 기타 모든 개별 주식

### 3. 자산 유형 (asset_type)

- `STOCK`: 주식형 ETF 또는 개별 주식 (yfinance로 holdings/sectors 분석)
- `BOND`: 채권형 ETF (yfinance 시도, 실패 시 Fixed Income으로 처리)
- `CASH`: 현금성 자산 (yfinance 조회 없이 Cash & Equivalents로 처리)

### 4. 티커 매핑

한국 ETF → 미국 대응 ETF 매핑으로 분석 정확도 향상:
- `KODEX 코스피 100` → `EWY` (iShares MSCI South Korea ETF)

### 5. 기타 종목 (OTHER)

yfinance의 `top_holdings`는 상위 10개만 제공하므로, 나머지 종목을 "OTHER"로 자동 추가하여 원금과 일치하도록 보정
- **표시 위치**: 금액이 많더라도 항상 목록 맨 마지막에 표시 (별도 섹션으로 구분)
- **출처 추적**: 어떤 ETF에서 발생한 기타 종목인지 표시 (예: SPY, QQQ)

### 6. 한국 주식 표시

- **자동 감지**: `.KS` 확장자를 가진 주식은 한국 주식으로 자동 인식
- **실제 종목명 표시**: 티커 대신 실제 회사명 표시 (예: `005930.KS` → `삼성전자 (005930.KS)`)
- **다중 ETF 추적**: 여러 ETF에 포함된 종목은 출처 표시 (예: `AAPL [from: SPY,QQQ]`)

### 7. 환율 자동 계산

- `yfinance`에서 `KRW=X` 티커로 최신 환율 조회
- 미국 ETF/개별 주식 holdings의 원화 환산 자동 적용

## 🛠 개발 가이드

### DB 마이그레이션

기존 DB에 필요한 스키마 변경 사항이 있을 경우 직접 SQL로 실행하거나,
`data/init_db.py`를 참고하여 스키마를 업데이트하세요.

### 스크립트 옵션

#### import_monthly_data.py

```bash
python -m data.import_monthly_data monthly/2025-11-purchase.yaml --overwrite --db portfolio.db
```

#### import_monthly_purchases.py

```bash
# 매수 기준일 26일 (기본값)
python -m data.import_monthly_purchases monthly/2025-11-purchase.yaml --db portfolio.db

# 매수 기준일 변경 (예: 15일)
python -m data.import_monthly_purchases monthly/2025-11-purchase.yaml --purchase-day 15
```

#### evaluate_accumulative.py

```bash
# 현재 보유 수량 및 평가액 출력
python -m core.evaluate_accumulative --db portfolio.db
```

#### analyze_portfolio.py

```bash
python -m core.analyze_portfolio --month 2025-12 --overwrite --skip-account --skip-total
```

#### visualize_portfolio.py

```bash
python -m visualization.visualize_portfolio --month 2025-12 --output charts --db portfolio.db
```

#### run_monthly.py

```bash
python scripts/run_monthly.py --month 2025-12 --yaml monthly/2025-11-purchase.yaml \
  --skip-import --skip-analyze --skip-visualize
```

## 📝 월별 데이터 작성 가이드

자세한 내용은 `monthly/README.md` 참조

### 필수 필드

- `name`: 계좌/종목 이름
- `type`: ISA, IRP, 연금저축, 일반
- `broker`: 증권사명
- `ticker_mapping`: 분석용 티커 (SPY, QQQ, TLT, EWY, CASH 등)
- `amount`: 매수 금액 (원)
- `asset_type`: STOCK, BOND, CASH

### 선택 필드

- `fee`: 계좌 운영수수료 (기본값: 0.0)
- `interest_rate`: 이자율 (CASH만 해당, 예: 0.077 = 7.7%)
- `target_ratio`: 자동 계산됨 (입력 불필요)

## 🐛 트러블슈팅

### yfinance 경고

```
⚠️  TLT: top_holdings 데이터 없음
```

→ 정상 동작. 채권 ETF는 holdings 데이터가 없어 "Fixed Income" 섹터로 대체 처리됨

### Matplotlib 폰트 경고

```
UserWarning: Glyph 128176 (\N{MONEY BAG}) missing from font
```

→ 차트는 정상 생성됨. 이모지만 깨짐 (무시 가능)

### DB 테이블 없음

```
sqlite3.OperationalError: no such table: months
```

→ `python -m data.init_db` 실행

## 🌐 웹 대시보드 (Streamlit)

인터랙티브 웹 기반 포트폴리오 분석 대시보드

### 주요 기능

**📅 월별 투자 비교**
- 4대 핵심 지표 (총자산, 총원금, 총수익, 수익률)
- Waterfall Chart로 자산 변동 흐름 시각화
- 월별 비교 테이블 및 자산 추이 차트

**🏦 계좌별 포트폴리오**
- 계좌별 접기/펼치기 기능
- 보유 종목 vs ETF 투시 분석 (토글 방식)
- 섹터 비중 Pie Chart
- 한국 주식 자동 종목명 표시

**🏆 전체 포트폴리오**
- 자산 유형별 요약 (STOCK/BOND/CASH)
- Sunburst Chart (계층적 구조, 드릴다운 지원)
- 종목 검색 (직접 + ETF 통한 간접 보유 통합)
- 통합 섹터 비중 및 Top 20 Holdings

**⌨️ 키보드 단축키 지원** ✨ **NEW!**
- `1`, `2`, `3`: 페이지 이동 (월별 비교/계좌별/전체)
- `←`: 이전 월 선택
- `→`: 다음 월 선택
- `F`: '전체 기간' 선택
- 사이드바 네비게이션 버튼으로도 이동 가능

**🌐 "전체 기간" 통합 기능** ✨ **NEW!**
- 월 선택 드롭다운에서 "전체 기간" 선택 가능
- 모든 월의 매수 내역(purchase_history) 자동 합산
- CASH 항목 포함 (최신 월 holdings와 병합)
- 계좌별 통합 보기 지원

### 빠른 시작

```bash
# Streamlit 앱 실행
streamlit run app.py

# 브라우저에서 접속
# http://localhost:8501
```

### 성능 최적화

- **캐싱 전략**: ETF 데이터 24시간, 월별 데이터 1시간
- **Top N 제한**: ETF 투시 10개, 전체 보유 20개
- **조건부 로딩**: ETF 투시 토글 방식 (기본 OFF)

### 상세 문서

- [Streamlit 앱 사용 가이드](./streamlit_app/README.md)
- [아키텍처 문서](./streamlit_app/ARCHITECTURE.md)
- [UI 디자인 문서](./designs/)

---

## 🎯 향후 계획

- [x] 웹 대시보드 (Streamlit) ✅ **완료!**
- [x] 키보드 단축키 지원 ✅ **완료!**
- [x] "전체 기간" 통합 기능 ✅ **완료!**
- [ ] 텔레그램 봇 연동 (차트 이미지 자동 전송)
- [ ] 리밸런싱 추천 알고리즘
- [ ] 포트폴리오 백테스팅 기능

## 📜 라이선스

MIT License

## 🙏 기여

Issues와 Pull Requests 환영합니다!

---

**Made with ❤️ for personal portfolio management**
