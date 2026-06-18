from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.shop_scope import assign_shop_scope, shop_filter
from app.models.visit import Visit
from app.models.visit_exam_section import VisitExamSection


class VisitExamSectionRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_for_visit(self, visit_id: int, shop_key: str) -> list[VisitExamSection]:
        return (
            self.db.query(VisitExamSection)
            .filter(VisitExamSection.visit_id == visit_id, shop_filter(self.db, VisitExamSection, shop_key))
            .order_by(VisitExamSection.id.asc())
            .all()
        )

    def get_for_visit(self, visit_id: int, section_key: str, shop_key: str) -> VisitExamSection | None:
        return (
            self.db.query(VisitExamSection)
            .filter(
                VisitExamSection.visit_id == visit_id,
                VisitExamSection.section_key == section_key,
                shop_filter(self.db, VisitExamSection, shop_key),
            )
            .first()
        )

    def list_previous_for_customer(
        self,
        customer_id: int,
        current_visit_id: int,
        section_keys: set[str],
        shop_key: str,
    ) -> list[VisitExamSection]:
        return (
            self.db.query(VisitExamSection)
            .join(Visit, Visit.id == VisitExamSection.visit_id)
            .filter(
                Visit.customer_id == customer_id,
                Visit.id != current_visit_id,
                VisitExamSection.section_key.in_(section_keys),
                shop_filter(self.db, VisitExamSection, shop_key),
                shop_filter(self.db, Visit, shop_key),
            )
            .order_by(Visit.visit_date.desc(), VisitExamSection.updated_at.desc())
            .all()
        )

    def create(self, section: VisitExamSection) -> VisitExamSection:
        assign_shop_scope(section, self.db, section.shop_key)
        self.db.add(section)
        self.db.flush()
        return section

    def save(self, section: VisitExamSection) -> VisitExamSection:
        assign_shop_scope(section, self.db, section.shop_key)
        self.db.add(section)
        self.db.flush()
        return section
