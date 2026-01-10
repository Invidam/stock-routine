# 🚀 실행 가이드 (How to Run)

포트폴리오 분석 시스템을 실행하는 방법을 단계별로 설명합니다.

## 📦 초기 설정 (최초 1회)

### 1. DB 초기화

```bash
python -m data.init_db
```

**출력:**
```
✅ 데이터베이스 초기화 완료: portfolio.db
   - months 테이블 생성
   - accounts 테이블 생성
   - holdings 테이블 생성
   - purchase_history 테이블 생성
   - analyzed_holdings 테이블 생성
   - analyzed_sectors 테이블 생성
```

## 📅 월별 루틴 (매월 실행)

### 방법 1: 통합 스크립트 (권장)

**기본 실행 (26일 주가 기준):**
```bash
python scripts/run_monthly.py --month 2025-11 --yaml monthly/2025-11.yaml
```

**다른 날짜 주가 기준 (예: 12월 18일):**
```bash
python scripts/run_monthly.py --month 2025-12 --yaml monthly/2025-12.yaml --purchase-day 18
```

**실행 단계:**
1. ✅ 계좌 및 holdings 정보 임포트 (YAML → DB)
2. ✅ 주가 조회 및 수량 계산 (purchase_history 저장)
3. ✅ 포트폴리오 분석 (ETF 확장, 섹터 분석)
4. ✅ 시각화 차트 생성 (4종류)

### 방법 2: 단계별 실행

#### Step 1: 데이터 임포트
```bash
# 1-1. 계좌/보유 항목 임포트
python -m data.import_monthly_data monthly/2025-11.yaml --overwrite

# 1-2. 주가 조회 및 수량 계산
python -m data.import_monthly_purchases monthly/2025-11.yaml --purchase-day 26
```

#### Step 2: 포트폴리오 분석
```bash
python -m core.analyze_portfolio --month 2025-11 --overwrite
```

**옵션:**
- `--exclude-cash`: CASH 자산 제외하고 분석
- `--skip-account`: 계좌별 분석 생략 (전체 분석만)
- `--skip-total`: 전체 분석 생략 (계좌별 분석만)

#### Step 3: 시각화
```bash
python -m visualization.visualize_portfolio --month 2025-11
```

**생성되는 차트:**
- `charts/2025-11_asset_allocation.png` - 자산 배분 (도넛 차트)
- `charts/2025-11_sectors.png` - 섹터별 분포
- `charts/2025-11_top_holdings.png` - 상위 보유 종목
- `charts/cumulative_asset_trend.png` - 누적 자산 추이

## 🔍 데이터 조회

### 월별 데이터 확인

**저장된 월 목록:**
```bash
python -m data.query_db --list
```

**특정 월 상세 조회:**
```bash
python -m data.query_db --month 2025-11
```

**티커별 집계:**
```bash
python -m data.query_db --month 2025-11 --ticker
```

### 적립식 투자 현황 평가

**기본 리포트:**
```bash
python -m core.evaluate_accumulative
```

**상세 리포트:**
```bash
python -m core.evaluate_accumulative --detailed
```

**출력 내용:**
- 종목별 보유 수량, 평단가, 현재가
- 평가금액 및 손익
- 총 투자금액 및 수익률

## 📂 파일별 역할

### 핵심 실행 파일

| 파일 | 역할 | 사용 시점 |
|------|------|----------|
| `data/init_db.py` | DB 초기화 | 최초 1회 |
| `scripts/run_monthly.py` | **통합 실행 스크립트** | **매월 1회** (권장) |
| `data/import_monthly_data.py` | 계좌/holdings 임포트 | 수동 실행 시 |
| `data/import_monthly_purchases.py` | 주가 조회 및 수량 계산 | 수동 실행 시 |
| `core/analyze_portfolio.py` | 포트폴리오 분석 | 수동 실행 시 |
| `visualization/visualize_portfolio.py` | 차트 생성 | 수동 실행 시 |
| `data/query_db.py` | DB 데이터 조회 | 필요할 때 |
| `core/evaluate_accumulative.py` | 적립식 투자 평가 | 필요할 때 |

### 데이터 파일

- `monthly/*.yaml` - 월별 포트폴리오 데이터
- `portfolio.db` - SQLite 데이터베이스
- `charts/*.png` - 생성된 차트 이미지

## 🔄 일반적인 워크플로우

### 시나리오 1: 새로운 월 데이터 추가

```bash
# 1. YAML 파일 작성
# monthly/2025-12.yaml 생성

# 2. 통합 스크립트 실행
python scripts/run_monthly.py --month 2025-12 --yaml monthly/2025-12.yaml --purchase-day 18

# 3. 차트 확인
# charts/ 디렉토리에서 생성된 PNG 파일 확인
```

### 시나리오 2: 기존 데이터 재분석

```bash
# 데이터는 그대로 두고 분석만 다시 실행
python scripts/run_monthly.py --month 2025-11 --yaml monthly/2025-11.yaml --skip-import
```

### 시나리오 3: 차트만 재생성

```bash
# 분석 결과는 그대로 두고 시각화만 다시 실행
python scripts/run_monthly.py --month 2025-11 --yaml monthly/2025-11.yaml --skip-import --skip-analyze
```

### 시나리오 4: 적립식 투자 현황 확인

```bash
# 현재 보유 중인 모든 종목의 평가액 확인
python -m core.evaluate_accumulative --detailed
```

## ⚙️ 크론 자동화 설정

```bash
# crontab -e
# 매월 1일 오전 9시에 자동 실행 (26일 주가 기준)
0 9 1 * * cd /path/to/stock-routine && python scripts/run_monthly.py --month $(date +\%Y-\%m) --yaml monthly/$(date +\%Y-\%m).yaml >> logs/cron.log 2>&1
```

## 🐛 문제 해결

### DB 초기화 다시 하기
```bash
rm portfolio.db
python -m data.init_db
```

### 중복 데이터 제거
```bash
# 특정 월 데이터 삭제 후 재임포트
sqlite3 portfolio.db "DELETE FROM months WHERE year_month = '2025-11';"
python scripts/run_monthly.py --month 2025-11 --yaml monthly/2025-11.yaml
```

### 주가 조회 실패 시
```bash
# 다른 날짜로 재시도
python -m data.import_monthly_purchases monthly/2025-11.yaml --purchase-day 25
```

## 📌 주요 옵션 요약

### run_monthly.py
- `--month`: 분석할 월 (YYYY-MM) **[필수]**
- `--yaml`: YAML 파일 경로 **[필수]**
- `--purchase-day`: 매수 기준일 (기본값: 26)
- `--skip-import`: 데이터 임포트 건너뛰기
- `--skip-analyze`: 포트폴리오 분석 건너뛰기
- `--skip-visualize`: 시각화 건너뛰기
- `--db`: DB 파일 경로 (기본값: portfolio.db)
- `--output`: 차트 저장 디렉토리 (기본값: charts)

### analyze_portfolio.py
- `--month`: 분석할 월 (YYYY-MM) **[필수]**
- `--overwrite`: 기존 분석 데이터 덮어쓰기
- `--exclude-cash`: CASH 자산 제외
- `--skip-account`: 계좌별 분석 생략
- `--skip-total`: 전체 분석 생략

### visualize_portfolio.py
- `--month`: 시각화할 월 (YYYY-MM) **[필수]**
- `--db`: DB 파일 경로 (기본값: portfolio.db)
- `--output`: 차트 저장 디렉토리 (기본값: charts)
