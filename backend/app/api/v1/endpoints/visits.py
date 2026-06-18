from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_shop_key, require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.visit import VisitCreate, VisitListResponse, VisitRead
from app.schemas.contact_lens import (
    ContactLensContext,
    ContactLensFollowUpRead,
    ContactLensFollowUpSchedule,
    ContactLensFollowUpStatusUpdate,
    ContactLensOrderRead,
    ContactLensOrderStatusUpdate,
    ContactLensOrderUpdate,
    ContactLensWorkupRead,
    ContactLensWorkupUpdate,
)
from app.schemas.dispensing_order import (
    DispensingOrderContext,
    DispensingOrderDocumentResponse,
    DispensingOrderDraftUpdate,
    DispensingOrderRead,
    DispensingOrderSendVendorRequest,
    DispensingOrderSendVendorResponse,
    DispensingOrderStatusUpdate,
)
from app.schemas.visit_exam_section import (
    VisitExamSectionHistoryResponse,
    VisitExamSectionListResponse,
    VisitExamSectionRead,
    VisitExamSectionUpdate,
)
from app.schemas.visit_prescription import (
    PrescriptionFinalizeRequest,
    VisitCompletionRequest,
    VisitPrescriptionDraftUpdate,
    VisitPrescriptionPdfResponse,
    VisitPrescriptionRead,
    VisitPrescriptionReview,
    VisitPrescriptionSummary,
)
from app.schemas.bill import BillRead
from app.schemas.visit_billing import VisitBillLinkRequest, VisitBillingContext
from app.services.visit_exam_section_service import VisitExamSectionService
from app.services.contact_lens_service import ContactLensService
from app.services.dispensing_order_service import DispensingOrderService
from app.services.visit_prescription_service import VisitPrescriptionService
from app.services.visit_service import VisitService
from app.services.visit_billing_service import VisitBillingService

router = APIRouter(prefix="/visits", tags=["visits"])


@router.get("/{visit_id}/contact-lens", response_model=ContactLensContext)
def get_contact_lens_context(
    visit_id: int,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> ContactLensContext:
    return ContactLensService(db, shop_key).get_context(visit_id, current_user)


@router.post("/{visit_id}/contact-lens/activate", response_model=ContactLensContext)
def activate_contact_lens_workup(
    visit_id: int,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> ContactLensContext:
    return ContactLensService(db, shop_key).activate(visit_id, current_user)


@router.put("/{visit_id}/contact-lens/workup", response_model=ContactLensWorkupRead)
def save_contact_lens_workup(
    visit_id: int,
    payload: ContactLensWorkupUpdate,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> ContactLensWorkupRead:
    return ContactLensService(db, shop_key).save_workup(visit_id, payload, current_user)


@router.put("/{visit_id}/contact-lens/order", response_model=ContactLensOrderRead)
def save_contact_lens_order(
    visit_id: int,
    payload: ContactLensOrderUpdate,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> ContactLensOrderRead:
    return ContactLensService(db, shop_key).save_order(visit_id, payload, current_user)


@router.post("/{visit_id}/contact-lens/order/status", response_model=ContactLensOrderRead)
def change_contact_lens_order_status(
    visit_id: int,
    payload: ContactLensOrderStatusUpdate,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> ContactLensOrderRead:
    return ContactLensService(db, shop_key).change_order_status(visit_id, payload, current_user)


@router.put("/{visit_id}/contact-lens/follow-up", response_model=ContactLensFollowUpRead)
def schedule_contact_lens_follow_up(
    visit_id: int,
    payload: ContactLensFollowUpSchedule,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> ContactLensFollowUpRead:
    return ContactLensService(db, shop_key).schedule_follow_up(visit_id, payload, current_user)


@router.post("/{visit_id}/contact-lens/follow-up/status", response_model=ContactLensFollowUpRead)
def change_contact_lens_follow_up_status(
    visit_id: int,
    payload: ContactLensFollowUpStatusUpdate,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> ContactLensFollowUpRead:
    return ContactLensService(db, shop_key).change_follow_up_status(visit_id, payload.status, current_user)


@router.get("/{visit_id}/billing", response_model=VisitBillingContext)
def get_visit_billing_context(
    visit_id: int,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> VisitBillingContext:
    return VisitBillingService(db, shop_key).get_context(visit_id, current_user)


@router.post("/{visit_id}/billing/link", response_model=BillRead)
def link_existing_bill_to_visit(
    visit_id: int,
    payload: VisitBillLinkRequest,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> BillRead:
    return VisitBillingService(db, shop_key).link_existing_bill(visit_id, payload, current_user)


@router.get("/{visit_id}/dispensing-order", response_model=DispensingOrderContext)
def get_dispensing_order_context(
    visit_id: int,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> DispensingOrderContext:
    return DispensingOrderService(db, shop_key).get_context(visit_id, current_user)


@router.put("/{visit_id}/dispensing-order", response_model=DispensingOrderRead)
def save_dispensing_order(
    visit_id: int,
    payload: DispensingOrderDraftUpdate,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> DispensingOrderRead:
    return DispensingOrderService(db, shop_key).save_draft(visit_id, payload, current_user)


@router.post("/{visit_id}/dispensing-order/relink-current", response_model=DispensingOrderRead)
def relink_dispensing_order_prescription(
    visit_id: int,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> DispensingOrderRead:
    return DispensingOrderService(db, shop_key).relink_current_prescription(visit_id, current_user)


@router.post("/{visit_id}/dispensing-order/status", response_model=DispensingOrderRead)
def change_dispensing_order_status(
    visit_id: int,
    payload: DispensingOrderStatusUpdate,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> DispensingOrderRead:
    return DispensingOrderService(db, shop_key).change_status(visit_id, payload, current_user)


@router.post("/{visit_id}/dispensing-order/vendor-document", response_model=DispensingOrderDocumentResponse)
def generate_dispensing_order_vendor_document(
    visit_id: int,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> DispensingOrderDocumentResponse:
    return DispensingOrderService(db, shop_key).generate_vendor_document(visit_id, current_user)


@router.get("/{visit_id}/dispensing-order/vendor-document/download")
def download_dispensing_order_vendor_document(
    visit_id: int,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> FileResponse:
    file_path = DispensingOrderService(db, shop_key).get_vendor_document_for_download(visit_id, current_user)
    return FileResponse(path=file_path, media_type="application/pdf", filename=file_path.name)


@router.post("/{visit_id}/dispensing-order/send-vendor", response_model=DispensingOrderSendVendorResponse)
def send_dispensing_order_to_vendor(
    visit_id: int,
    payload: DispensingOrderSendVendorRequest,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> DispensingOrderSendVendorResponse:
    return DispensingOrderService(db, shop_key).send_to_vendor(visit_id, payload, current_user)


@router.post("", response_model=VisitRead, status_code=status.HTTP_201_CREATED)
def start_visit(
    payload: VisitCreate,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> VisitRead:
    service = VisitService(db, shop_key=shop_key)
    return service.start_visit(payload=payload, actor=current_user)


@router.get("/customer/{customer_id}", response_model=VisitListResponse)
def list_customer_visits(
    customer_id: int,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> VisitListResponse:
    _ = current_user
    service = VisitService(db, shop_key=shop_key)
    return service.list_customer_visits(customer_id=customer_id)


@router.get("/{visit_id}/exam-sections", response_model=VisitExamSectionListResponse)
def list_visit_exam_sections(
    visit_id: int,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> VisitExamSectionListResponse:
    service = VisitExamSectionService(db, shop_key=shop_key)
    return service.list_sections(visit_id=visit_id, actor=current_user)


@router.get("/{visit_id}/exam-section-history", response_model=VisitExamSectionHistoryResponse)
def list_visit_exam_section_history(
    visit_id: int,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> VisitExamSectionHistoryResponse:
    service = VisitExamSectionService(db, shop_key=shop_key)
    return service.list_previous_core_sections(visit_id=visit_id, actor=current_user)


@router.put("/{visit_id}/exam-sections/{section_key}", response_model=VisitExamSectionRead)
def save_visit_exam_section(
    visit_id: int,
    section_key: str,
    payload: VisitExamSectionUpdate,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> VisitExamSectionRead:
    service = VisitExamSectionService(db, shop_key=shop_key)
    return service.save_section(visit_id=visit_id, section_key=section_key, payload=payload, actor=current_user)


@router.get("/{visit_id}/prescriptions", response_model=VisitPrescriptionSummary)
def get_visit_prescriptions(
    visit_id: int,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> VisitPrescriptionSummary:
    return VisitPrescriptionService(db, shop_key=shop_key).get_summary(visit_id, current_user)


@router.put("/{visit_id}/prescriptions/draft", response_model=VisitPrescriptionRead)
def save_visit_prescription_draft(
    visit_id: int,
    payload: VisitPrescriptionDraftUpdate,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> VisitPrescriptionRead:
    return VisitPrescriptionService(db, shop_key=shop_key).save_draft(visit_id, payload, current_user)


@router.get("/{visit_id}/prescriptions/{prescription_id}/review", response_model=VisitPrescriptionReview)
def review_visit_prescription(
    visit_id: int,
    prescription_id: int,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> VisitPrescriptionReview:
    return VisitPrescriptionService(db, shop_key=shop_key).get_review(visit_id, prescription_id, current_user)


@router.post("/{visit_id}/prescriptions/{prescription_id}/finalize", response_model=VisitPrescriptionRead)
def finalize_visit_prescription(
    visit_id: int,
    prescription_id: int,
    payload: PrescriptionFinalizeRequest,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> VisitPrescriptionRead:
    return VisitPrescriptionService(db, shop_key=shop_key).finalize(
        visit_id,
        prescription_id,
        payload,
        current_user,
    )


@router.post("/{visit_id}/prescriptions/{prescription_id}/amend", response_model=VisitPrescriptionRead)
def amend_visit_prescription(
    visit_id: int,
    prescription_id: int,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> VisitPrescriptionRead:
    return VisitPrescriptionService(db, shop_key=shop_key).create_amendment(
        visit_id,
        prescription_id,
        current_user,
    )


@router.post("/{visit_id}/prescription/pdf", response_model=VisitPrescriptionPdfResponse)
def generate_current_visit_prescription_pdf(
    visit_id: int,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> VisitPrescriptionPdfResponse:
    return VisitPrescriptionService(db, shop_key=shop_key).generate_pdf(visit_id, current_user)


@router.get("/{visit_id}/prescription/pdf/download")
def download_current_visit_prescription_pdf(
    visit_id: int,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> FileResponse:
    pdf_file = VisitPrescriptionService(db, shop_key=shop_key).get_pdf_file_for_download(visit_id, current_user)
    return FileResponse(path=pdf_file, media_type="application/pdf", filename=pdf_file.name)


@router.post("/{visit_id}/complete", response_model=VisitRead)
def complete_visit(
    visit_id: int,
    payload: VisitCompletionRequest,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> VisitRead:
    return VisitPrescriptionService(db, shop_key=shop_key).complete_visit(visit_id, payload, current_user)


@router.get("/{visit_id}", response_model=VisitRead)
def get_visit(
    visit_id: int,
    db: Session = Depends(get_db),
    shop_key: str = Depends(get_shop_key),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
) -> VisitRead:
    service = VisitService(db, shop_key=shop_key)
    return service.get_visit(visit_id=visit_id, actor=current_user)
