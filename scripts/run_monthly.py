#!/usr/bin/env python
"""
월별 포트폴리오 분석 자동화 스크립트
크론에서 실행하기 위한 통합 모듈

사용법:
  python run_monthly.py --month 2025-11 --yaml monthly/2025-11.yaml
  python run_monthly.py --month 2025-12 --yaml monthly/2025-12.yaml --purchase-day 18

크론 예시:
  # 매월 1일 오전 9시에 실행 (26일 주가 기준)
  0 9 1 * * cd /path/to/stock-routine && python run_monthly.py --month $(date +\%Y-\%m) --yaml monthly/$(date +\%Y-\%m).yaml
"""
import argparse
import sys
from pathlib import Path
from datetime import datetime

# 로컬 모듈 임포트
from data.init_db import init_database
from data.import_monthly_data import import_monthly_data
from data.import_monthly_purchases import import_monthly_purchases
from core.analyze_portfolio import analyze_month_portfolio
from visualization.visualize_portfolio import visualize_portfolio


def run_monthly_routine(
    year_month: str,
    yaml_path: str,
    db_path: str = "portfolio.db",
    output_dir: str = "charts",
    purchase_day: int = 26,
    skip_import: bool = False,
    skip_analyze: bool = False,
    skip_visualize: bool = False
):
    """
    월별 포트폴리오 분석 루틴 실행

    Args:
        year_month: 분석할 월 (YYYY-MM)
        yaml_path: 월별 YAML 파일 경로
        db_path: SQLite DB 파일 경로
        output_dir: 차트 저장 디렉토리
        purchase_day: 매수 기준일 (기본값: 26일)
        skip_import: True면 import 스킵
        skip_analyze: True면 analyze 스킵
        skip_visualize: True면 visualize 스킵
    """
    print("=" * 80)
    print(f"📅 {year_month}월 포트폴리오 자동 분석 시작")
    print(f"⏰ 실행 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # DB 초기화 확인
    db_file = Path(db_path)
    if not db_file.exists():
        print("🔧 데이터베이스 파일이 없습니다. 초기화 중...")
        init_database(db_path)

    # Step 1: YAML Import
    if not skip_import:
        print("\n📥 [1/4] 데이터 임포트 시작")
        print("-" * 80)
        try:
            # Step 1-1: 계좌 및 holdings 정보 저장
            print("  [1-1] 계좌 정보 임포트 중...")
            import_monthly_data(yaml_path, db_path, overwrite=True)
            print("  ✅ 계좌 정보 임포트 완료")

            # Step 1-2: 주가 조회 및 purchase_history 저장
            print(f"\n  [1-2] 주가 조회 및 매수 수량 계산 중 (기준일: {purchase_day}일)...")
            import_monthly_purchases(yaml_path, db_path, purchase_day, overwrite=True)
            print("  ✅ 주가 조회 및 매수 데이터 저장 완료")

            print("\n✅ 전체 데이터 임포트 완료")
        except Exception as e:
            print(f"❌ 데이터 임포트 실패: {e}")
            sys.exit(1)
    else:
        print("\n⏭️  [1/4] 데이터 임포트 스킵")

    # Step 2: Portfolio Analysis
    if not skip_analyze:
        print("\n📊 [2/4] 포트폴리오 분석 시작")
        print("-" * 80)
        try:
            analyze_month_portfolio(
                year_month=year_month,
                db_path=db_path,
                overwrite=True,
                analyze_by_account=True,
                analyze_total=True
            )
            print("✅ 포트폴리오 분석 완료")
        except Exception as e:
            print(f"❌ 포트폴리오 분석 실패: {e}")
            sys.exit(1)
    else:
        print("\n⏭️  [2/4] 포트폴리오 분석 스킵")

    # Step 3: Visualization
    if not skip_visualize:
        print("\n📈 [3/4] 시각화 시작")
        print("-" * 80)
        try:
            visualize_portfolio(year_month, db_path, output_dir)
            print("✅ 시각화 완료")
        except Exception as e:
            print(f"❌ 시각화 실패: {e}")
            sys.exit(1)
    else:
        print("\n⏭️  [3/4] 시각화 스킵")

    # 완료 메시지
    print("\n" + "=" * 80)
    print(f"✅ {year_month}월 포트폴리오 자동 분석 완료!")
    print(f"📂 차트 저장 경로: {output_dir}/")
    print(f"💾 데이터베이스: {db_path}")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="월별 포트폴리오 분석 자동화 스크립트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 기본 실행 (26일 주가 기준)
  python run_monthly.py --month 2025-11 --yaml monthly/2025-11.yaml

  # 다른 날짜 주가 기준 (예: 12월 18일)
  python run_monthly.py --month 2025-12 --yaml monthly/2025-12.yaml --purchase-day 18

  # import만 실행
  python run_monthly.py --month 2025-11 --yaml monthly/2025-11.yaml --skip-analyze --skip-visualize

  # analyze만 실행
  python run_monthly.py --month 2025-11 --yaml monthly/2025-11.yaml --skip-import --skip-visualize

크론 설정 예시:
  # 매월 1일 오전 9시에 실행 (26일 주가 기준)
  0 9 1 * * cd /path/to/stock-routine && python run_monthly.py --month $(date +\\%Y-\\%m) --yaml monthly/$(date +\\%Y-\\%m).yaml >> logs/cron.log 2>&1
        """
    )

    parser.add_argument("--month", required=True, help="분석할 월 (YYYY-MM)")
    parser.add_argument("--yaml", required=True, help="월별 YAML 파일 경로 (예: monthly/2025-11.yaml)")
    parser.add_argument("--db", default="portfolio.db", help="SQLite DB 파일 경로 (기본값: portfolio.db)")
    parser.add_argument("--output", default="charts", help="차트 저장 디렉토리 (기본값: charts)")
    parser.add_argument("--purchase-day", type=int, default=26, help="매수 기준일 (기본값: 26일)")
    parser.add_argument("--skip-import", action="store_true", help="데이터 임포트 스킵")
    parser.add_argument("--skip-analyze", action="store_true", help="포트폴리오 분석 스킵")
    parser.add_argument("--skip-visualize", action="store_true", help="시각화 스킵")

    args = parser.parse_args()

    # YAML 파일 존재 확인
    if not args.skip_import:
        yaml_file = Path(args.yaml)
        if not yaml_file.exists():
            print(f"❌ YAML 파일을 찾을 수 없습니다: {args.yaml}")
            sys.exit(1)

    # 실행
    run_monthly_routine(
        year_month=args.month,
        yaml_path=args.yaml,
        db_path=args.db,
        output_dir=args.output,
        purchase_day=args.purchase_day,
        skip_import=args.skip_import,
        skip_analyze=args.skip_analyze,
        skip_visualize=args.skip_visualize
    )


if __name__ == "__main__":
    main()
