from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.shops import get_shop_definition
from app.models.enums import DispensingOrderStatus, WhatsAppStatus
from app.models.shop import Shop
from app.schemas.customer import CustomerCreate
from app.schemas.dispensing_order import (
    DispensingOrderDraftUpdate,
    DispensingOrderSendVendorRequest,
    DispensingOrderStatusUpdate,
)
from app.schemas.vendor import VendorCreate
from app.schemas.visit import VisitCreate
from app.schemas.visit_prescription import PrescriptionFinalizeRequest, VisitPrescriptionDraftUpdate
from app.services.customer_service import CustomerService
from app.services.dispensing_order_service import DispensingOrderService
from app.services.vendor_service import VendorService
from app.services.visit_prescription_service import VisitPrescriptionService
from app.services.visit_service import VisitService
from tests.conftest import TEST_SHOP_ONE, TEST_SHOP_TWO


def _final_prescription() -> VisitPrescriptionDraftUpdate:
    return VisitPrescriptionDraftUpdate(
        data={
            "distance": {
                "right": {"sph": "-1.00", "cyl": "-0.50", "axis": "90", "va": "6/6"},
                "left": {"sph": "-0.75", "cyl": "-0.25", "axis": "80", "va": "6/6"},
            },
            "near": {
                "right": {"add": "+1.50", "va": "N6"},
                "left": {"add": "+1.50", "va": "N6"},
            },
            "pd": "62",
            "fitting_height": "18",
        },
        patient_instructions="Use for distance and reading.",
    )


def _create_finalized_visit(db_session: Session, make_user, shop_key: str = TEST_SHOP_ONE):
    if db_session.query(Shop).filter(Shop.code == shop_key).first() is None:
        definition = get_shop_definition(shop_key)
        assert definition is not None
        db_session.add(
            Shop(
                code=definition.code,
                display_name=definition.display_name,
                location_label=definition.location_label,
                center_type=definition.center_type,
                is_active=definition.is_active,
            )
        )
        db_session.commit()
    actor = make_user(f"phase-seven-{shop_key}@example.com", shop_key)
    patient = CustomerService(db_session, shop_key=shop_key).create_customer(
        payload=CustomerCreate(
            name=f"Phase Seven Patient {shop_key}",
            contact_no="9876500771",
            whatsapp_no="9876500771",
            whatsapp_opt_in=True,
            address="Private patient address",
        ),
        actor=actor,
    )
    visit = VisitService(db_session, shop_key=shop_key).start_visit(
        payload=VisitCreate(
            customer_id=patient.id,
            visit_date=datetime(2026, 6, 18, 11, 0, tzinfo=UTC),
            reason_for_visit="Private clinical reason",
            idempotency_key=f"phase-seven-{shop_key}",
        ),
        actor=actor,
    )
    prescription_service = VisitPrescriptionService(db_session, shop_key=shop_key)
    draft = prescription_service.save_draft(visit.id, _final_prescription(), actor)
    prescription = prescription_service.finalize(
        visit.id,
        draft.id,
        PrescriptionFinalizeRequest(confirmed=True),
        actor,
    )
    return actor, patient, visit, prescription


def _order_payload(vendor_id: int | None = None) -> DispensingOrderDraftUpdate:
    return DispensingOrderDraftUpdate(
        frame={
            "brand": "Ray-Ban",
            "model_number": "RX-5228",
            "colour_code": "2000",
            "frame_type": "Full rim",
            "barcode": "8901234567890",
            "a_size_mm": "52",
            "b_size_mm": "34",
            "dbl_mm": "17",
            "temple_length_mm": "140",
            "effective_diameter_mm": "56",
        },
        measurements={
            "right_monocular_pd_mm": "31",
            "left_monocular_pd_mm": "31",
            "total_pd_mm": "62",
            "right_fitting_height_mm": "18",
            "left_fitting_height_mm": "18",
            "right_segment_height_mm": "17",
            "left_segment_height_mm": "17",
            "pantoscopic_tilt_degrees": "8",
            "vertex_distance_mm": "12",
            "measured_by": "Optometrist One",
            "measurement_notes": "Measurements confirmed twice",
        },
        lens={
            "lens_type": "progressive",
            "brand": "Essilor",
            "material": "MR-8",
            "index": "1.60",
            "design": "Varilux Comfort",
            "coating": "Crizal Sapphire",
            "tint_or_photochromic": "Transitions Gen S",
        },
        vendor_id=vendor_id,
        manufacturing_instructions="Use supplied frame; verify centration before edging.",
    )


def test_dispensing_order_draft_links_exact_current_prescription_and_saves_all_sections(
    db_session: Session,
    make_user,
) -> None:
    actor, patient, visit, prescription = _create_finalized_visit(db_session, make_user)
    service = DispensingOrderService(db_session, shop_key=TEST_SHOP_ONE)

    created = service.save_draft(visit.id, _order_payload(), actor)
    context = service.get_context(visit.id, actor)

    assert created.customer_id == patient.id
    assert created.prescription_id == prescription.id
    assert created.prescription_version_number == 1
    assert created.status == DispensingOrderStatus.DRAFT
    assert created.frame.model_number == "RX-5228"
    assert created.measurements.total_pd_mm == 62
    assert created.lens.lens_type == "progressive"
    assert created.created_by == actor.id
    assert context.order is not None
    assert context.is_prescription_stale is False
    assert context.current_prescription_id == prescription.id


def test_order_requires_finalized_prescription_and_stale_version_needs_explicit_relink(
    db_session: Session,
    make_user,
) -> None:
    actor, _patient, visit, first = _create_finalized_visit(db_session, make_user)
    order_service = DispensingOrderService(db_session, shop_key=TEST_SHOP_ONE)
    order_service.save_draft(visit.id, _order_payload(), actor)
    prescription_service = VisitPrescriptionService(db_session, shop_key=TEST_SHOP_ONE)
    amendment = prescription_service.create_amendment(visit.id, first.id, actor)
    changed = _final_prescription()
    changed.data.distance.right.sph = "-1.25"
    prescription_service.save_draft(visit.id, changed, actor)
    second = prescription_service.finalize(
        visit.id,
        amendment.id,
        PrescriptionFinalizeRequest(confirmed=True),
        actor,
    )

    stale_context = order_service.get_context(visit.id, actor)
    assert stale_context.order is not None
    assert stale_context.order.prescription_id == first.id
    assert stale_context.is_prescription_stale is True

    with pytest.raises(AppException) as stale_document:
        order_service.generate_vendor_document(visit.id, actor)
    assert stale_document.value.code == "dispensing_order_prescription_stale"

    relinked = order_service.relink_current_prescription(visit.id, actor)
    assert relinked.prescription_id == second.id
    assert relinked.prescription_version_number == 2
    assert order_service.get_context(visit.id, actor).is_prescription_stale is False


def test_dispensing_order_status_transitions_are_controlled(db_session: Session, make_user) -> None:
    actor, _patient, visit, _prescription = _create_finalized_visit(db_session, make_user)
    service = DispensingOrderService(db_session, shop_key=TEST_SHOP_ONE)
    service.save_draft(visit.id, _order_payload(), actor)

    ready = service.change_status(
        visit.id,
        DispensingOrderStatusUpdate(status=DispensingOrderStatus.READY_FOR_VENDOR),
        actor,
    )
    assert ready.status == DispensingOrderStatus.READY_FOR_VENDOR

    with pytest.raises(AppException) as invalid_transition:
        service.change_status(
            visit.id,
            DispensingOrderStatusUpdate(status=DispensingOrderStatus.DELIVERED),
            actor,
        )
    assert invalid_transition.value.code == "dispensing_order_invalid_status_transition"


def test_editing_draft_invalidates_previously_generated_vendor_document(db_session: Session, make_user) -> None:
    actor, _patient, visit, _prescription = _create_finalized_visit(db_session, make_user)
    service = DispensingOrderService(db_session, shop_key=TEST_SHOP_ONE)
    service.save_draft(visit.id, _order_payload(), actor)
    order = service.repo.get_by_visit(visit.id, TEST_SHOP_ONE)
    assert order is not None
    order.vendor_document_file_path = "vendor_orders/outdated.pdf"
    service.repo.save(order)
    db_session.commit()

    changed = _order_payload()
    changed.frame.model_number = "RX-5228-UPDATED"
    updated = service.save_draft(visit.id, changed, actor)

    assert updated.frame.model_number == "RX-5228-UPDATED"
    assert updated.has_vendor_document is False


def test_cross_shop_cannot_read_or_download_dispensing_order(db_session: Session, make_user) -> None:
    actor, _patient, visit, _prescription = _create_finalized_visit(db_session, make_user)
    DispensingOrderService(db_session, shop_key=TEST_SHOP_ONE).save_draft(visit.id, _order_payload(), actor)
    other_actor = make_user("phase-seven-other@example.com", TEST_SHOP_TWO)

    with pytest.raises(AppException) as read_error:
        DispensingOrderService(db_session, shop_key=TEST_SHOP_TWO).get_context(visit.id, other_actor)
    assert read_error.value.status_code == 404

    with pytest.raises(AppException) as download_error:
        DispensingOrderService(db_session, shop_key=TEST_SHOP_TWO).get_vendor_document_for_download(
            visit.id,
            other_actor,
        )
    assert download_error.value.status_code == 404


def test_vendor_document_contains_fulfilment_data_but_excludes_private_patient_and_clinical_data(
    db_session: Session,
    make_user,
) -> None:
    actor, patient, visit, _prescription = _create_finalized_visit(db_session, make_user)
    service = DispensingOrderService(db_session, shop_key=TEST_SHOP_ONE)
    service.save_draft(visit.id, _order_payload(), actor)
    order = service.repo.get_by_visit(visit.id, TEST_SHOP_ONE)
    assert order is not None

    html = service.pdf_service._build_html(order=order, branch_name="Adarsh Optical Centre")

    assert order.order_reference in html
    assert "RX-5228" in html
    assert "Varilux Comfort" in html
    assert "-1.00" in html
    assert "Private patient address" not in html
    assert patient.contact_no not in html
    assert visit.reason_for_visit not in html
    assert patient.name not in html


def test_vendor_send_reuses_whatsapp_and_records_sent_status(
    db_session: Session,
    make_user,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor, _patient, visit, _prescription = _create_finalized_visit(db_session, make_user)
    vendor = VendorService(db_session, shop_key=TEST_SHOP_ONE).create_vendor(
        VendorCreate(vendor_name="Phase Seven Lab", whatsapp_no="9082967356"),
        actor,
    )
    service = DispensingOrderService(db_session, shop_key=TEST_SHOP_ONE)
    service.save_draft(visit.id, _order_payload(vendor.id), actor)
    service.change_status(
        visit.id,
        DispensingOrderStatusUpdate(status=DispensingOrderStatus.READY_FOR_VENDOR),
        actor,
    )
    file_path = tmp_path / "vendor-order.pdf"
    file_path.write_bytes(b"vendor-document")
    monkeypatch.setattr(settings, "media_root", str(tmp_path))
    monkeypatch.setattr(
        service.pdf_service,
        "generate_vendor_order_pdf",
        lambda **_kwargs: SimpleNamespace(file_path=file_path),
    )
    uploaded: list[Path] = []
    monkeypatch.setattr(service.whatsapp_service, "upload_media", lambda path: uploaded.append(Path(path)) or "media-7")
    monkeypatch.setattr(
        service.whatsapp_service,
        "send_document_message",
        lambda **_kwargs: SimpleNamespace(
            status=WhatsAppStatus.SENT,
            whatsapp_log_id=71,
            provider_message_id="wamid.phase7",
            error_message=None,
        ),
    )

    result = service.send_to_vendor(
        visit.id,
        DispensingOrderSendVendorRequest(caption="Spectacle order ready"),
        actor,
    )

    assert uploaded == [file_path]
    assert result.whatsapp_log_id == 71
    assert result.provider_message_id == "wamid.phase7"
    assert service.get_context(visit.id, actor).order.status == DispensingOrderStatus.SENT_TO_VENDOR
