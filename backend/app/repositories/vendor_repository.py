from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.vendor import Vendor


class VendorRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(
        self,
        page: int,
        page_size: int,
        search: str | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[Vendor], int]:
        query = self.db.query(Vendor)

        if is_active is not None:
            query = query.filter(Vendor.is_active.is_(is_active))

        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Vendor.vendor_name.ilike(pattern),
                    Vendor.contact_person.ilike(pattern),
                    Vendor.whatsapp_no.ilike(pattern),
                )
            )

        total = query.count()
        items = (
            query.order_by(Vendor.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def get_by_id(self, vendor_id: int) -> Vendor | None:
        return self.db.query(Vendor).filter(Vendor.id == vendor_id).first()

    def create(self, vendor: Vendor) -> Vendor:
        self.db.add(vendor)
        self.db.flush()
        return vendor

    def save(self, vendor: Vendor) -> Vendor:
        self.db.add(vendor)
        self.db.flush()
        return vendor
