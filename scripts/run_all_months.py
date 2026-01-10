#!/usr/bin/env python
"""
모든 월별 데이터에 대해 월별 분석 스크립트를 실행합니다.

사용법:
  python run_all_months.py
"""
import sys
from pathlib import Path
import argparse

# run_monthly.py에서 메인 루틴 함수를 가져옵니다.
# 경로 문제를 피하기 위해 프로젝트 루트를 sys.path에 추가합니다.
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from scripts.run_monthly import run_monthly_routine


def main():
    parser = argparse.ArgumentParser(
        description="모든 월에 대해 월별 포트폴리오 분석을 실행합니다.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--db", default="portfolio.db", help="SQLite DB 파일 경로")
    parser.add_argument("--output", default="charts", help="차트 저장 디렉토리")
    parser.add_argument("--purchase-day", type=int, default=26, help="매수 기준일")
    args = parser.parse_args()

    monthly_dir = Path("monthly")
    if not monthly_dir.exists():
        print(f"❌ 'monthly' 디렉토리를 찾을 수 없습니다.")
        sys.exit(1)

    # monthly 디렉토리에서 .yaml 파일 목록을 가져와 정렬합니다.
    yaml_files = sorted(list(monthly_dir.glob("*.yaml")))

    if not yaml_files:
        print("📂 'monthly' 디렉토리에 YAML 파일이 없습니다.")
        return

    print(f"🚀 총 {len(yaml_files)}개의 월에 대해 분석을 시작합니다.")
    print("=" * 80)

    for yaml_file in yaml_files:
        # 파일명에서 년-월(예: 2025-11)을 추출합니다.
        year_month = yaml_file.stem

        try:
            run_monthly_routine(
                year_month=year_month,
                yaml_path=str(yaml_file),
                db_path=args.db,
                output_dir=args.output,
                purchase_day=args.purchase_day,
                # run_all 사용 시 항상 모든 단계를 실행하도록 가정
                skip_import=False,
                skip_analyze=False,
                skip_visualize=False
            )
        except Exception as e:
            print(f"❌ {year_month} 처리 중 오류 발생: {e}")
            # 한 월에서 오류가 발생하더라도 다음 월을 계속 처리합니다.
            continue

    print("=" * 80)
    print("🎉 모든 월에 대한 분석이 완료되었습니다.")


if __name__ == "__main__":
    main()
