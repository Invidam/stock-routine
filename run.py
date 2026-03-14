#!/usr/bin/env python
"""
포트폴리오 분석 통합 CLI

사용법:
  python run.py --month 2026-02              # 한 달 (이미 된 건 스킵)
  python run.py                              # 전체 (이미 된 건 스킵)
  python run.py --month 2026-02 --force      # 강제 재실행
  python run.py --only analyze               # 분석만 전체 재실행
"""
import argparse
import sqlite3
import sys
from pathlib import Path
from datetime import datetime

from data.init_db import init_database
from data.importer import import_month
from core.analyze_portfolio import analyze_month_portfolio
from visualization.visualize_portfolio import visualize_portfolio


def is_imported(year_month: str, db_path: str) -> bool:
    """purchase_history에 해당 월 데이터가 존재하는지 확인"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM purchase_history WHERE year_month = ?",
            (year_month,)
        )
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
    except:
        return False


def is_analyzed(year_month: str, db_path: str) -> bool:
    """analyzed_holdings에 해당 월 데이터가 존재하는지 확인"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM analyzed_holdings ah
            JOIN months m ON ah.month_id = m.id
            WHERE m.year_month = ?
        """, (year_month,))
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
    except:
        return False


def run(
    year_month: str,
    yaml_path: str,
    db_path: str = "portfolio.db",
    output_dir: str = "charts",
    purchase_day: int = 26,
    force: bool = False,
    only: str = None,
):
    """단일 월 파이프라인 실행"""
    print(f"\n{'=' * 60}")
    print(f"📅 {year_month} 포트폴리오 분석")
    print(f"{'=' * 60}")

    # Import
    if only is None or only == "import":
        if force or not is_imported(year_month, db_path):
            print("\n📥 [1/3] 데이터 임포트")
            try:
                import_month(yaml_path, db_path, purchase_day, overwrite=force)
            except Exception as e:
                print(f"❌ 임포트 실패: {e}")
                return False
        else:
            print(f"\n⏭️  [1/3] 임포트 스킵 ({year_month} 이미 존재)")

    # Analyze
    if only is None or only == "analyze":
        if force or not is_analyzed(year_month, db_path):
            print("\n📊 [2/3] 포트폴리오 분석")
            try:
                analyze_month_portfolio(
                    year_month=year_month,
                    db_path=db_path,
                    overwrite=force,
                    analyze_by_account=True,
                    analyze_total=True
                )
            except Exception as e:
                print(f"❌ 분석 실패: {e}")
                return False
        else:
            print(f"\n⏭️  [2/3] 분석 스킵 ({year_month} 이미 분석됨)")

    # Visualize (항상 실행 - 빠르므로)
    if only is None or only == "visualize":
        print("\n📈 [3/3] 시각화")
        try:
            visualize_portfolio(year_month, db_path, output_dir)
        except Exception as e:
            print(f"❌ 시각화 실패: {e}")
            return False

    print(f"\n✅ {year_month} 완료!")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="포트폴리오 분석 통합 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python run.py --month 2026-02              # 한 달 (이미 된 건 스킵)
  python run.py                              # 전체 (이미 된 건 스킵)
  python run.py --month 2026-02 --force      # 강제 재실행
  python run.py --only analyze               # 분석만 전체 재실행
        """
    )

    parser.add_argument("--month", help="분석할 월 (YYYY-MM). 없으면 전체 실행")
    parser.add_argument("--force", action="store_true", help="강제 재실행 (이미 된 것도 다시)")
    parser.add_argument("--only", choices=["import", "analyze", "visualize"], help="특정 단계만 실행")
    parser.add_argument("--db", default="portfolio.db", help="DB 경로 (기본값: portfolio.db)")
    parser.add_argument("--output", default="charts", help="차트 저장 디렉토리 (기본값: charts)")
    parser.add_argument("--purchase-day", type=int, default=26, help="매수 기준일 (기본값: 26일)")

    args = parser.parse_args()

    # DB 초기화
    if not Path(args.db).exists():
        print("🔧 데이터베이스 초기화 중...")
        init_database(args.db)

    if args.month:
        # 단일 월 실행
        yaml_path = f"monthly/{args.month}.yaml"
        if not args.only or args.only == "import":
            if not Path(yaml_path).exists():
                print(f"❌ YAML 파일을 찾을 수 없습니다: {yaml_path}")
                sys.exit(1)

        run(
            year_month=args.month,
            yaml_path=yaml_path,
            db_path=args.db,
            output_dir=args.output,
            purchase_day=args.purchase_day,
            force=args.force,
            only=args.only,
        )
    else:
        # 전체 월 실행
        monthly_dir = Path("monthly")
        if not monthly_dir.exists():
            print("❌ 'monthly' 디렉토리를 찾을 수 없습니다.")
            sys.exit(1)

        yaml_files = sorted([
            f for f in monthly_dir.glob("*.yaml")
            if not f.stem.startswith("example")
        ])

        if not yaml_files:
            print("📂 'monthly' 디렉토리에 YAML 파일이 없습니다.")
            return

        # 전체 실행 + force일 때만 DB 재생성
        if args.force:
            import os
            if Path(args.db).exists():
                print(f"🗑️  기존 DB 삭제: {args.db}")
                os.remove(args.db)
            init_database(args.db)

        print(f"🚀 총 {len(yaml_files)}개월 분석 시작")
        print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        for yaml_file in yaml_files:
            year_month = yaml_file.stem
            try:
                run(
                    year_month=year_month,
                    yaml_path=str(yaml_file),
                    db_path=args.db,
                    output_dir=args.output,
                    purchase_day=args.purchase_day,
                    force=args.force,
                    only=args.only,
                )
            except Exception as e:
                print(f"❌ {year_month} 오류: {e}")
                continue

        print(f"\n{'=' * 60}")
        print("🎉 전체 분석 완료!")


if __name__ == "__main__":
    main()
