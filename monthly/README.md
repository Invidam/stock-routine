# 📅 Monthly Investment Data

이 디렉토리는 월별 투자 정보를 YAML 형태로 관리합니다.

## 📁 파일 명명 규칙

파일명은 `YYYY-MM.yaml` 형식을 따릅니다:
- `2025-12.yaml` - 2025년 12월 데이터
- `2026-01.yaml` - 2026년 1월 데이터

## 📝 YAML 파일 구조

```yaml
purchase_day: 26  # 매수 기준일 (선택적, 미지정 시 CLI 기본값 26)

accounts:
  - name: "계좌 이름"
    type: "계좌 타입"  # ISA, IRP, 연금저축, 일반 등
    broker: "증권사명"
    fee: 수수료율  # 계좌 운영수수료 (0.0015 = 0.15%)
    holdings:
      - name: "종목명"
        ticker_mapping: "티커"  # 분석용 매핑 티커 (예: SPY, QQQ)
        amount: 금액  # 매수 금액 (원)
        target_ratio: 목표비중  # 0.0 ~ 1.0 사이 값
```

## 🔧 필드 설명

### 파일 최상위 레벨
- **purchase_day**: 매수 기준일 (선택적, 1~31)
  - 지정 시 CLI `--purchase-day` 파라미터보다 우선 적용
  - 미지정 시 CLI 기본값(26일) 사용
  - 우선순위: `YAML purchase_day` > `CLI --purchase-day` > `기본값 26`

### Account 레벨
- **name**: 계좌의 별칭 (예: "투자 (절세)", "노후 준비")
- **type**: 계좌 유형 (문자열, 따옴표 필수)
  - `"ISA"`: 개인종합자산관리계좌
  - `"IRP"`: 개인형 퇴직연금
  - `"연금저축"`: 연금저축펀드
  - `"일반"`: 일반 위탁계좌
- **broker**: 증권사명
- **fee**: 계좌 운영수수료율 (소수점 형태)
  - 예: 0.0015 = 0.15%
  - 예: 0.002 = 0.2%
  - 예: 0.0 = 무료

### Holdings 레벨
- **name**: 실제 보유 종목명
- **ticker_mapping**: 분석에 사용할 티커 심볼
  - 국내 상장 해외 ETF의 경우 미국 본토 티커로 매핑
  - 예: S&P 500 ETF → SPY
  - 예: 나스닥 100 ETF → QQQ
  - 예: 코스피 ETF → EWY
- **amount**: 매수 금액 (원 단위)
- **asset_type**: 자산 유형 (문자열, 따옴표 필수, 선택적, 기본값: "STOCK")
  - `"STOCK"`: 주식형 ETF (기본값)
  - `"BOND"`: 채권형 ETF (예: TLT, IEF, BND)
  - `"CASH"`: 현금성 자산 (예: 적금, 주택청약)
- **interest_rate**: 이자율 (선택적, CASH 자산에만 해당)
  - 소수점 형태 (예: 0.077 = 7.7%, 0.023 = 2.3%)
  - 주식/채권 ETF에는 불필요
- **interest_type**: 이자 계산 방식 (문자열, 따옴표 필수, 선택적, CASH 자산에만 해당)
  - `"simple"`: 단리 (기본값)
  - `"compound"`: 복리

**자동 계산 필드:**
- **target_ratio**: 계좌 내 목표 비중 (임포트 시 자동 계산)
  - 계산 공식: holding.amount / 계좌별_총_금액
  - YAML에 입력하지 않아도 됨

## 💡 사용 방법

### 새 월별 파일 작성
1. **이전 달 YAML 파일을 복사**하여 새 파일을 만듭니다
2. 변경된 종목/금액만 수정합니다
3. 계좌 구조, 증권사명, 종목명 등은 이전 달을 그대로 따릅니다

```bash
cp monthly/2026-02.yaml monthly/2026-03.yaml
# 이후 금액/종목 변경사항만 수정
```

### 예시 구조
```yaml
accounts:
  - name: "계좌 별칭"
    type: "ISA"
    broker: "증권사A"
    fee: 0.0015
    holdings:
      - name: "ETF 종목명"
        ticker_mapping: "SPY"
        amount: 300000
        asset_type: "STOCK"
```

## 📊 활용 방법

1. **월말 스냅샷**: 매월 말일 기준으로 새 YAML 파일 생성
2. **변경 추적**: Git을 통해 월별 포트폴리오 변화 이력 관리
3. **분석 입력**: 시계열 분석 시 해당 월의 YAML 파일을 입력 데이터로 사용

## 🏷️ 자산 유형 (asset_type)

### 개요

`asset_type` 필드를 통해 자산을 주식형/채권형/현금형으로 구분할 수 있습니다. 이를 통해 통합 포트폴리오 분석 시 Net Worth 뷰를 제공합니다.

### 자산 유형별 특징

#### STOCK (주식형) - 기본값
- **분석 방법**: yfinance로 ETF holdings/sectors 조회
- **적용 대상**: SPY, QQQ, EWY 등 주식형 ETF
- **생략 가능**: asset_type 필드를 생략하면 자동으로 STOCK으로 처리

**예시:**
```yaml
- name: "주식형 ETF"
  ticker_mapping: "SPY"
  amount: 300000
  asset_type: "STOCK"  # 생략 가능
```

#### BOND (채권형)
- **분석 방법**: yfinance 조회 시도, 실패 시 "Fixed Income" 섹터로 처리
- **적용 대상**: TLT, IEF, BND, AGG 등 채권 ETF
- **출력**: Net Worth에서 "안전 자산 (채권형)"으로 표시

**예시:**
```yaml
- name: "채권형 ETF"
  ticker_mapping: "TLT"
  amount: 200000
  asset_type: "BOND"  # 필수
```

#### CASH (현금형)
- **분석 방법**: yfinance 조회 없이 "Cash & Equivalents" 섹터로 직접 처리
- **적용 대상**: 적금, 주택청약, 예금 등 현금성 자산
- **출력**: Net Worth에서 "현금성 자산"으로 표시, 통합 holdings에서 개별 상품명 표시
- **수익률**: `interest_rate`와 `interest_type` 설정 시 이자 반영 수익률 자동 계산

**예시:**
```yaml
- name: "적금 상품"
  ticker_mapping: "적금"
  amount: 50000
  asset_type: "CASH"  # 필수
  interest_rate: 0.023  # 연 2.3% (선택적)
  interest_type: "simple"  # 단리(기본값) 또는 compound(복리)
```

### 통합 분석 출력

`asset_type`을 사용하면 다음과 같은 통합 분석 결과를 볼 수 있습니다:

1. **Net Worth 섹션**: 위험 자산(주식) / 안전 자산(채권) / 현금성 자산 구분
2. **통합 섹터 비중**: 주식 섹터 + Fixed Income + Cash & Equivalents
3. **통합 보유 항목**: [주식], [채권], [현금] 태그와 함께 금액 순으로 표시

## 🔄 티커 자동 매핑

일부 한국 ETF는 yfinance에서 조회가 불가능하여 분석 시 미국 대응 ETF로 자동 매핑됩니다:

- **EWY** (iShares MSCI South Korea ETF) - 한국 시장 추종 ETF
  - 코스피 추종 ETF 등

**사용 방법:**
```yaml
- name: "코스피 ETF"
  ticker_mapping: "EWY"  # 코스피 추종 ETF는 EWY로 매핑
  amount: 200000
  asset_type: "STOCK"
```

**참고:** 티커 매핑은 `analyze_portfolio.py`의 `TICKER_MAPPING` 딕셔너리에서 관리됩니다.

## ✍️ YAML 작성 규칙

### 따옴표 규칙
- **모든 문자열 값에 쌍따옴표(`"`) 필수**
- 숫자 값(`amount`, `fee`, `interest_rate`, `purchase_day`)에는 따옴표를 붙이지 않음
- 예: `name: "종목명"`, `asset_type: "STOCK"`, `type: "ISA"`

### 이전 달 참고
- 새 파일 작성 시 **반드시 이전 달 YAML 파일을 복사하여 기반으로 사용**
- 계좌 구조, 계좌명, 증권사명, 종목명 등은 이전 달을 그대로 유지
- 변경된 금액/종목만 수정

## ⚠️ 주의사항

- `target_ratio`의 합이 1.0을 초과하지 않도록 주의
- `fee`는 계좌 운영수수료율이므로 0.0 ~ 1.0 사이 값 사용
  - 연 단위 수수료율 입력 (예: 0.0015 = 연 0.15%)
- `ticker_mapping`은 실제 거래 가능한 티커로 정확히 입력