from __future__ import annotations

from dataclasses import dataclass

from app.models.enums import ExamSectionState


@dataclass(frozen=True)
class ExamSectionDefinition:
    key: str
    title: str
    description: str
    state: ExamSectionState = ExamSectionState.INCOMPLETE
    is_required: bool = False
    is_optional: bool = False
    is_disabled: bool = False
    is_visible: bool = True


EXAM_SECTION_DEFINITIONS: tuple[ExamSectionDefinition, ...] = (
    ExamSectionDefinition(
        key="patient_visit",
        title="Patient and Visit",
        description="Patient identity, visit reason, examiner, and branch context.",
        state=ExamSectionState.COMPLETE,
        is_required=True,
    ),
    ExamSectionDefinition(
        key="visual_acuity",
        title="Visual Acuity",
        description="Distance and near acuity for right eye and left eye.",
        is_required=True,
    ),
    ExamSectionDefinition(
        key="objective_refraction",
        title="Objective Refraction",
        description="Autorefraction or retinoscopy findings before subjective refinement.",
        is_required=True,
    ),
    ExamSectionDefinition(
        key="subjective_refraction",
        title="Subjective Refraction",
        description="Subjective refraction values and patient response.",
        is_required=True,
    ),
    ExamSectionDefinition(
        key="binocular_vision",
        title="Binocular Vision",
        description="Binocular status and related observations.",
        state=ExamSectionState.OPTIONAL,
        is_optional=True,
    ),
    ExamSectionDefinition(
        key="cycloplegic_refraction",
        title="Cycloplegic Refraction",
        description="Cycloplegic values when this test is performed.",
        state=ExamSectionState.NOT_APPLICABLE,
        is_optional=True,
    ),
    ExamSectionDefinition(
        key="final_prescription",
        title="Final Prescription",
        description="Final optical prescription review values.",
        is_required=True,
    ),
    ExamSectionDefinition(
        key="potential_vision",
        title="Potential Vision",
        description="Potential vision assessment when clinically needed.",
        state=ExamSectionState.OPTIONAL,
        is_optional=True,
    ),
    ExamSectionDefinition(
        key="torch_light_evaluation",
        title="Torch-Light Evaluation",
        description="Torch-light anterior segment observations.",
        state=ExamSectionState.OPTIONAL,
        is_optional=True,
    ),
    ExamSectionDefinition(
        key="slit_lamp_evaluation",
        title="Slit-Lamp Evaluation",
        description="Slit-lamp findings and clinical notes.",
        state=ExamSectionState.OPTIONAL,
        is_optional=True,
    ),
    ExamSectionDefinition(
        key="referral",
        title="Referral",
        description="Referral details when the patient needs external care.",
        state=ExamSectionState.NOT_APPLICABLE,
        is_optional=True,
    ),
    ExamSectionDefinition(
        key="frame_dispensing",
        title="Frame and Dispensing",
        description="Frame selection and dispensing measurements.",
        state=ExamSectionState.OPTIONAL,
        is_optional=True,
    ),
    ExamSectionDefinition(
        key="lens_order",
        title="Lens Order",
        description="Lens order choices and vendor-ready order notes.",
        state=ExamSectionState.OPTIONAL,
        is_optional=True,
    ),
    ExamSectionDefinition(
        key="contact_lens",
        title="Contact Lens",
        description="Contact lens work-up when relevant for this visit.",
        state=ExamSectionState.NOT_APPLICABLE,
        is_optional=True,
        is_visible=False,
    ),
    ExamSectionDefinition(
        key="billing",
        title="Billing",
        description="Existing billing module handoff and payment status.",
        state=ExamSectionState.OPTIONAL,
        is_optional=True,
    ),
    ExamSectionDefinition(
        key="completion_follow_up",
        title="Completion and Follow-Up",
        description="Visit completion checklist and follow-up planning.",
        is_required=True,
    ),
    ExamSectionDefinition(
        key="iop_future",
        title="IOP Future Module",
        description="IOP is reserved for a future module and is disabled in this phase.",
        state=ExamSectionState.FUTURE,
        is_optional=True,
        is_disabled=True,
    ),
)

EXAM_SECTION_BY_KEY = {section.key: section for section in EXAM_SECTION_DEFINITIONS}


def get_exam_section_definition(section_key: str) -> ExamSectionDefinition | None:
    return EXAM_SECTION_BY_KEY.get(section_key.strip().lower())
