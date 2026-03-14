# Stock Portfolio Routine

개인 투자 포트폴리오 통합 분석 시스템
주식형 ETF, 채권, 현금성 자산을 모두 포함한 Net Worth 분석 및 리포트 자동화

## 프라이버시 설정 (GitHub 공개 시)

### 자동 제외 항목 (.gitignore)
- `monthly/*.yaml` - 실제 투자 데이터 파일
- `portfolio.db` - 투자 내역이 저장된 데이터베이스
- `charts/*.png` - 생성된 차트 이미지 (재생성 가능)

### 예시 파일 제공
- `monthly/example-2025-01.yaml` - 상세한 주석이 포함된 예시 파일
- `example-`로 시작하는 파일만 Git에 포함됩니다

---

## 주요 기능

- **다중 계좌 지원**: ISA, IRP, 연금저축, 일반 계좌 등 통합 관리
- **다양한 자산 유형**: 주식형 ETF, 채권형 ETF, 개별 주식, 현금성 자산(적금, 청약)
- **ETF 내부 분석**: yfinance를 통한 ETF 구성 종목 및 섹터 분석
- **개별 주식 지원**: AMZN, GOOGL, TSLA 등 자동 감지 (`quoteType == 'EQUITY'`)
- **적립식 투자 추적**: 월별 투자 금액 → 수량 자동 계산 → 현재가 기준 평가
- **적금 수익률 계산**: 현금성 자산의 이자 반영 평가액 자동 계산 (단리/복리 지원)
- **환율 자동 적용**: 미국 ETF/주식의 원화 환산 자동 계산
- **시각화**: 자산 배분 도넛 차트, 섹터 막대 차트, Top Holdings, 자산 추이
- **웹 대시보드**: Streamlit 기반 인터랙티브 대시보드 ([상세 문서](./streamlit_app/ARCHITECTURE.md))

---

## 시스템 구조

```
stock-routine/
├── run.py                             # 통합 CLI (import → analyze → visualize)
├── app.py                             # Streamlit 앱 엔트리포인트
├── core/                              # 핵심 비즈니스 로직
│   ├── analyze_portfolio.py           # 포트폴리오 분석 (핵심)
│   ├── evaluate_accumulative.py       # 적립식 투자 평가 (수량 × 현재가)
│   ├── interest_calculator.py         # 적금 이자 계산 (단리/복리)
│   └── portfolio_data.py              # CLI/Web 공통 데이터 조회 레이어
├── data/                              # 데이터 레이어
│   ├── init_db.py                     # DB 초기화
│   └── importer.py                    # YAML → DB 통합 임포트
├── visualization/                     # 시각화
│   └── visualize_portfolio.py         # Matplotlib 차트 생성
├── streamlit_app/                     # 웹 대시보드
│   ├── data_loader.py                 # 캐싱 래퍼 (portfolio_data 소비)
│   ├── components/                    # Plotly 차트 컴포넌트
│   ├── pages/                         # 3개 페이지
│   └── utils/                         # 유틸리티
├── monthly/                           # 월별 데이터 (YAML)
├── charts/                            # 생성된 차트 이미지
├── tests/                             # 테스트 (75개)
├── portfolio.db                       # SQLite 데이터베이스
└── requirements.txt                   # 의존성 목록
```

> 파이프라인 상세, DB 스키마, 설계 결정 등 기술 문서는 [AGENT.md](./AGENT.md) 참조

---

## 빠른 시작

### 1. 환경 설정

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m data.init_db
```

### 2. 테스트 환경 (Example 데이터)

```bash
# example 파일을 일반 형식으로 복사
cp monthly/example-2025-01.yaml monthly/2025-01.yaml

# 테스트 데이터로 전체 파이프라인 실행
python run.py --month 2025-01

# Streamlit 앱 실행
.venv/bin/streamlit run app.py
```

**테스트 데이터 삭제:**
```bash
rm monthly/2025-01.yaml
rm portfolio.db
python -m data.init_db
rm -rf charts/*
```

### 3. 월별 데이터 준비

`monthly/2025-12.yaml` 파일 작성:

```yaml
accounts:
  - name: "투자 (절세)"
    type: "ISA"
    broker: "토스증권"
    fee: 0.0015
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
        ticker_mapping: "일반적금"
        amount: 300000
        asset_type: "CASH"
        interest_rate: 0.077
        interest_type: "simple"  # 단리(기본값) 또는 compound(복리)
```

자세한 YAML 형식은 `monthly/README.md` 참고

---

## 사용법

### 통합 CLI (권장)

```bash
# 한 달 실행 (이미 된 건 자동 스킵)
python run.py --month 2025-12

# 전체 월 실행
python run.py

# 강제 재실행 (이미 된 것도 다시)
python run.py --month 2025-12 --force

# 특정 단계만 실행
python run.py --only analyze
python run.py --only visualize

# 다른 날짜 주가 기준
python run.py --month 2025-12 --purchase-day 18
```

### 적립식 투자 평가

```bash
python -m core.evaluate_accumulative            # 기본 리포트
python -m core.evaluate_accumulative --detailed  # 상세 리포트
```

### 웹 대시보드

```bash
streamlit run app.py
# http://localhost:8501
```

### 시나리오별 워크플로우

```bash
# 분석만 재실행 (임포트 생략)
python run.py --month 2025-12 --only analyze

# 차트만 재생성
python run.py --month 2025-12 --only visualize
```

---

## 크론 자동화

```bash
# crontab -e
0 9 1 * * cd /path/to/stock-routine && .venv/bin/python run.py --month $(date +\%Y-\%m) >> logs/cron.log 2>&1
```

---

## 주요 출력 예시

### Net Worth 섹션

```
총 자산: 1,469,982원

1. 위험 자산 (주식형)    :    819,982원 ( 55.8%)
2. 안전 자산 (채권형)    :    300,000원 ( 20.4%)
3. 현금성 자산 (적금)    :    350,000원 ( 23.8%)
```

### 통합 보유 상위 항목

```
[채권] TLT                              :    300,000원 ( 20.4%)
[현금] 일반적금                             :    300,000원 ( 20.4%)
[주식] 삼성전자 (005930.KS)                 :    150,000원 ( 10.2%)
[주식] NVDA [from: SPY,QQQ]             :     49,190원 (  3.3%)
```

---

## CLI 옵션 요약

### run.py
- `--month`: 분석할 월 (YYYY-MM, 없으면 전체 실행)
- `--force`: 강제 재실행 (이미 된 것도 다시)
- `--only`: 특정 단계만 실행 (`import`, `analyze`, `visualize`)
- `--purchase-day`: 매수 기준일 (기본값: 26)
- `--db`: DB 파일 경로 (기본값: portfolio.db)
- `--output`: 차트 저장 디렉토리 (기본값: charts)

---

## 문제 해결

```bash
# DB 초기화
rm portfolio.db && python -m data.init_db

# 특정 월 데이터 삭제 후 재임포트
sqlite3 portfolio.db "DELETE FROM months WHERE year_month = '2025-12';"
python run.py --month 2025-12

# 주가 조회 실패 시 다른 날짜로 재시도
python run.py --month 2025-12 --purchase-day 25 --force
```

---

## 다중 Mac 환경 설정 (iCloud 동기화)

개인 투자 데이터(`monthly/*.yaml`)는 Git에 포함되지 않으므로, 여러 Mac에서 작업할 경우 iCloud를 통해 자동 동기화합니다.

```
iCloud Drive/stock-routine-private/monthly/   ← 실제 파일 (자동 동기화)
        ↑ 심볼릭 링크
stock-routine/monthly/                        ← 프로젝트에서 접근
```

### 초기 설정 (각 Mac에서 1회)

```bash
./setup.sh
```

`setup.sh`가 하는 일:
1. iCloud에 `stock-routine-private/monthly/` 디렉토리 생성
2. 기존 yaml 파일을 iCloud로 이동 (example/README 제외)
3. `monthly/` → iCloud 심볼릭 링크 생성

전제 조건: 양쪽 Mac이 동일한 Apple ID로 iCloud 로그인 + iCloud Drive 활성화

---

## 향후 계획

- [x] 웹 대시보드 (Streamlit)
- [x] 키보드 단축키 지원
- [x] "전체 기간" 통합 기능
- [x] 적금 수익률 계산 (단리/복리)
- [ ] 텔레그램 봇 연동 (차트 이미지 자동 전송)
- [ ] 리밸런싱 추천 알고리즘
- [ ] 포트폴리오 백테스팅 기능

## 라이선스

MIT License
