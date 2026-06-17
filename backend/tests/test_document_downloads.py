from __future__ import annotations

import tempfile
import unittest
import importlib
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.exceptions import AppException
from app.db.base import Base
from app.models.bill import Bill
from app.models.customer import Customer
from app.models.enums import PaymentMode, PaymentStatus, UserRole
from app.models.prescription import Prescription
from app.models.user import User
from app.services.bill_service import BillService
from app.services.prescription_service import PrescriptionService


SHOP_ONE = "adarsh-optical-centre"
SHOP_TWO = "adarsh-eye-boutique"


class DocumentDownloadSecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.media_root = Path(self.temp_dir.name)
        self.setting_patcher = patch.object(settings, "media_root", str(self.media_root))
        self.setting_patcher.start()
        self.addCleanup(self.setting_patcher.stop)

        self.engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        Base.metadata.create_all(self.engine)
        self.addCleanup(self.engine.dispose)
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        self.db: Session = self.SessionLocal()
        self.addCleanup(self.db.close)

        self.actor_one = self._create_user("admin-one@example.com", SHOP_ONE)
        self.actor_two = self._create_user("admin-two@example.com", SHOP_TWO)
        self.customer_sequence = 0

    def _create_user(self, email: str, shop_key: str) -> User:
        user = User(
            email=email,
            full_name="Admin",
            password_hash="not-used",
            role=UserRole.ADMIN,
            shop_key=shop_key,
            is_active=True,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def _create_customer(self, shop_key: str) -> Customer:
        self.customer_sequence += 1
        customer = Customer(
            shop_key=shop_key,
            customer_id=f"CUST-{shop_key}-{self.customer_sequence}",
            name="Customer",
            contact_no="9999999999",
        )
        self.db.add(customer)
        self.db.commit()
        self.db.refresh(customer)
        return customer

    def _create_fake_pdf(self, relative_path: str) -> str:
        file_path = self.media_root / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(b"%PDF-1.4\n% test\n")
        return relative_path

    def _create_bill(self, shop_key: str) -> Bill:
        customer = self._create_customer(shop_key)
        bill = Bill(
            bill_number=f"BILL-{shop_key}",
            customer_id=customer.id,
            customer_name_snapshot=customer.name,
            product_name="Frame",
            whole_price=Decimal("100.00"),
            discount=Decimal("0.00"),
            final_price=Decimal("100.00"),
            paid_amount=Decimal("100.00"),
            balance_amount=Decimal("0.00"),
            payment_mode=PaymentMode.CASH,
            payment_status=PaymentStatus.PAID,
            pdf_file_path=self._create_fake_pdf(f"invoices/{shop_key}.pdf"),
        )
        self.db.add(bill)
        self.db.commit()
        self.db.refresh(bill)
        return bill

    def _create_prescription(self, shop_key: str) -> Prescription:
        customer = self._create_customer(shop_key)
        prescription = Prescription(
            customer_id=customer.id,
            prescription_date=date.today(),
            pdf_file_path=self._create_fake_pdf(f"prescriptions/{shop_key}.pdf"),
        )
        self.db.add(prescription)
        self.db.commit()
        self.db.refresh(prescription)
        return prescription

    def test_user_from_another_shop_cannot_download_bill_pdf(self) -> None:
        bill = self._create_bill(SHOP_ONE)

        with self.assertRaises(AppException) as raised:
            BillService(self.db, shop_key=SHOP_TWO).get_pdf_file_for_download(
                bill_id=bill.id,
                actor=self.actor_two,
            )

        self.assertEqual(raised.exception.status_code, 404)

    def test_user_from_another_shop_cannot_download_prescription_pdf(self) -> None:
        prescription = self._create_prescription(SHOP_ONE)

        with self.assertRaises(AppException) as raised:
            PrescriptionService(self.db, shop_key=SHOP_TWO).get_pdf_file_for_download(
                prescription_id=prescription.id,
                actor=self.actor_two,
            )

        self.assertEqual(raised.exception.status_code, 404)

    def test_user_from_same_shop_can_resolve_document_files(self) -> None:
        bill = self._create_bill(SHOP_ONE)
        prescription = self._create_prescription(SHOP_ONE)

        bill_path = BillService(self.db, shop_key=SHOP_ONE).get_pdf_file_for_download(
            bill_id=bill.id,
            actor=self.actor_one,
        )
        prescription_path = PrescriptionService(self.db, shop_key=SHOP_ONE).get_pdf_file_for_download(
            prescription_id=prescription.id,
            actor=self.actor_one,
        )

        self.assertTrue(bill_path.is_file())
        self.assertTrue(prescription_path.is_file())

    def test_media_static_files_are_not_mounted_in_production(self) -> None:
        with patch.object(settings, "environment", "production"):
            import app.main as main_module

            main_module = importlib.reload(main_module)
            route_paths = [getattr(route, "path", None) for route in main_module.app.routes]

        self.assertNotIn(settings.media_url_prefix, route_paths)

        with patch.object(settings, "environment", "development"):
            importlib.reload(main_module)


if __name__ == "__main__":
    unittest.main()
