"""
테스트 9: purchase_history 저장/삭제 로직
- save_purchase 정확성
- delete_purchase_history
- overwrite 모드
"""
import sqlite3
import pytest
from data.import_monthly_purchases import save_purchase, delete_purchase_history


class TestSavePurchase:
    """purchase_history 테이블 저장"""

    def test_basic_save(self, populated_db):
        """기본 저장"""
        calc_result = {
            'purchase_date': '2025-03-26',
            'quantity': 0.5,
            'price_krw': 850000.0,
            'leftover': 50000,
            'currency': 'USD',
            'exchange_rate': 1420.0,
        }

        # ISA 계좌의 account_id 찾기
        conn = sqlite3.connect(populated_db)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM accounts WHERE name='ISA' LIMIT 1")
        acc_id = cursor.fetchone()[0]
        conn.close()

        save_purchase(
            ticker='AAPL',
            asset_type='STOCK',
            year_month='2025-03',
            calc_result=calc_result,
            input_amount=400_000,
            account_name='ISA',
            note='테스트',
            db_path=populated_db,
        )

        conn = sqlite3.connect(populated_db)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM purchase_history WHERE ticker='AAPL' AND year_month='2025-03'"
        )
        row = cursor.fetchone()
        conn.close()

        assert row is not None

    def test_save_without_account(self, populated_db):
        """계좌 없이 저장 (account_id=None)"""
        calc_result = {
            'purchase_date': '2025-03-26',
            'quantity': 1.0,
            'price_krw': 100000.0,
            'leftover': 0,
            'currency': 'KRW',
            'exchange_rate': None,
        }

        save_purchase(
            ticker='TEST',
            asset_type='STOCK',
            year_month='2025-03',
            calc_result=calc_result,
            input_amount=100_000,
            account_name=None,
            note=None,
            db_path=populated_db,
        )

        conn = sqlite3.connect(populated_db)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT account_id FROM purchase_history WHERE ticker='TEST'"
        )
        row = cursor.fetchone()
        conn.close()

        assert row[0] is None


class TestDeletePurchaseHistory:
    """월별 구매 기록 삭제"""

    def test_delete_specific_month(self, populated_db):
        """특정 월만 삭제"""
        conn = sqlite3.connect(populated_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM purchase_history WHERE year_month='2025-01'")
        before = cursor.fetchone()[0]
        conn.close()

        assert before > 0

        delete_purchase_history('2025-01', populated_db)

        conn = sqlite3.connect(populated_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM purchase_history WHERE year_month='2025-01'")
        after = cursor.fetchone()[0]
        # 다른 월은 유지
        cursor.execute("SELECT COUNT(*) FROM purchase_history WHERE year_month='2025-02'")
        other = cursor.fetchone()[0]
        conn.close()

        assert after == 0
        assert other > 0

    def test_delete_nonexistent_month(self, populated_db):
        """없는 월 삭제 → 에러 없음"""
        delete_purchase_history('2099-12', populated_db)  # 에러 없이 통과


class TestCashHandling:
    """CASH 자산 처리"""

    def test_cash_quantity_equals_amount(self, initialized_db):
        """CASH: quantity = amount, price = 1.0"""
        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()

        # months, accounts 생성
        cursor.execute("INSERT INTO months (year_month) VALUES ('2025-01')")
        month_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO accounts (month_id, name, type, broker, fee) VALUES (?, 'ISA', 'ISA', '한투', 0.0)",
            (month_id,))
        conn.commit()
        conn.close()

        calc_result = {
            'purchase_date': '2025-01-26',
            'quantity': 100_000,  # 금액 = 수량
            'price_krw': 1.0,
            'leftover': 0,
            'currency': 'KRW',
            'exchange_rate': None,
        }

        save_purchase(
            ticker='CMA',
            asset_type='CASH',
            year_month='2025-01',
            calc_result=calc_result,
            input_amount=100_000,
            account_name='ISA',
            note=None,
            db_path=initialized_db,
        )

        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()
        cursor.execute("SELECT quantity, input_amount, price_at_purchase FROM purchase_history WHERE ticker='CMA'")
        row = cursor.fetchone()
        conn.close()

        assert row[0] == 100_000  # quantity = amount
        assert row[1] == 100_000
        assert row[2] == pytest.approx(1.0)