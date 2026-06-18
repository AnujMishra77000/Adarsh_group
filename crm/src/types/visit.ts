export type VisitStatus = "draft" | "in_progress" | "completed" | "cancelled";
export type ExamSectionState = "incomplete" | "complete" | "optional" | "not_applicable" | "future";

export type Visit = {
  id: number;
  shop_key: string;
  customer_id: number;
  customer_name: string | null;
  customer_business_id: string | null;
  customer_contact_no: string | null;
  visit_date: string;
  reason_for_visit: string;
  referred_by: string | null;
  assigned_examiner_id: number | null;
  assigned_examiner_name: string | null;
  visit_notes: string | null;
  contact_lens_workup_requested: boolean;
  status: VisitStatus;
  created_at: string;
  updated_at: string;
  created_by: number | null;
  updated_by: number | null;
};

export type VisitPayload = {
  customer_id: number;
  visit_date?: string | null;
  reason_for_visit: string;
  referred_by?: string | null;
  assigned_examiner_id?: number | null;
  visit_notes?: string | null;
  contact_lens_workup_requested?: boolean;
  status?: Extract<VisitStatus, "draft" | "in_progress">;
  idempotency_key?: string | null;
};

export type VisitListResponse = {
  items: Visit[];
  total: number;
};

export type VisitExamSection = {
  key: string;
  title: string;
  description: string;
  state: ExamSectionState;
  is_required: boolean;
  is_optional: boolean;
  is_disabled: boolean;
  is_visible: boolean;
  payload: Record<string, unknown>;
  saved_at: string | null;
  saved_by: number | null;
};

export type VisitExamSectionListResponse = {
  visit_id: number;
  sections: VisitExamSection[];
  total: number;
};

export type VisitExamSectionPayload = {
  state: Exclude<ExamSectionState, "future">;
  payload: Record<string, unknown>;
};

export type VisitExamSectionHistoryItem = {
  visit_id: number;
  visit_date: string;
  section_key: string;
  title: string;
  state: ExamSectionState;
  payload: Record<string, unknown>;
  saved_at: string | null;
  saved_by: number | null;
};

export type VisitExamSectionHistoryResponse = {
  visit_id: number;
  items: VisitExamSectionHistoryItem[];
  total: number;
};

export type PrescriptionVersionStatus = "draft" | "finalized" | "superseded" | "cancelled";

export type PrescriptionEyeValues = {
  sph: string | null;
  cyl: string | null;
  axis: string | null;
  add: string | null;
  va: string | null;
};

export type PrescriptionEyePair = {
  right: PrescriptionEyeValues;
  left: PrescriptionEyeValues;
};

export type FinalPrescriptionData = {
  distance: PrescriptionEyePair;
  near: PrescriptionEyePair;
  pd: string | null;
  fitting_height: string | null;
};

export type VisitPrescriptionDraftPayload = {
  data: FinalPrescriptionData;
  patient_instructions: string | null;
};

export type VisitPrescription = VisitPrescriptionDraftPayload & {
  id: number;
  visit_id: number;
  customer_id: number;
  version_number: number;
  status: PrescriptionVersionStatus;
  is_current: boolean;
  amends_prescription_id: number | null;
  finalized_by: number | null;
  finalized_at: string | null;
  created_at: string;
  updated_at: string;
  created_by: number | null;
  updated_by: number | null;
  has_pdf: boolean;
};

export type VisitPrescriptionSummary = {
  visit_id: number;
  current_version_id: number | null;
  draft_version_id: number | null;
  versions: VisitPrescription[];
};

export type VisitPrescriptionReview = {
  prescription: VisitPrescription;
  patient: { id: number; business_id: string; name: string };
  visit: {
    id: number;
    visit_date: string;
    reason_for_visit: string;
    status: VisitStatus;
    shop_key: string;
    branch_name: string;
    branch_location: string;
  };
  examiner: { id: number; name: string };
  core_examination_summary: Record<string, { state: ExamSectionState; payload: Record<string, unknown> }>;
  referral_summary: Record<string, unknown> | null;
  patient_instructions: string | null;
  warnings: string[];
};

export type VisitPrescriptionPdfResponse = {
  visit_id: number;
  prescription_id: number;
  version_number: number;
  pdf_url: string;
};

export type DispensingOrderStatus =
  | "draft"
  | "ready_for_vendor"
  | "sent_to_vendor"
  | "in_production"
  | "ready_for_delivery"
  | "delivered"
  | "cancelled";

export type LensType =
  | "single_vision"
  | "bifocal"
  | "progressive"
  | "office_lens"
  | "occupational_lens"
  | "sunglass_lens";

export type FrameSelection = {
  brand?: string | null;
  model_number?: string | null;
  colour_code?: string | null;
  frame_type?: string | null;
  barcode?: string | null;
  a_size_mm?: string | null;
  b_size_mm?: string | null;
  dbl_mm?: string | null;
  temple_length_mm?: string | null;
  effective_diameter_mm?: string | null;
};

export type DispensingMeasurements = {
  right_monocular_pd_mm?: string | null;
  left_monocular_pd_mm?: string | null;
  total_pd_mm?: string | null;
  right_fitting_height_mm?: string | null;
  left_fitting_height_mm?: string | null;
  right_segment_height_mm?: string | null;
  left_segment_height_mm?: string | null;
  pantoscopic_tilt_degrees?: string | null;
  vertex_distance_mm?: string | null;
  measured_by?: string | null;
  measurement_notes?: string | null;
};

export type LensSpecification = {
  lens_type?: LensType | null;
  brand?: string | null;
  material?: string | null;
  index?: string | null;
  design?: string | null;
  coating?: string | null;
  tint_or_photochromic?: string | null;
};

export type DispensingOrderPayload = {
  frame: FrameSelection;
  measurements: DispensingMeasurements;
  lens: LensSpecification;
  vendor_id: number | null;
  manufacturing_instructions: string | null;
  expected_delivery_date?: string | null;
};

export type OrderStatusEvent = {
  id: number;
  event: string;
  previous_status: DispensingOrderStatus | null;
  status: DispensingOrderStatus;
  user_id: number | null;
  notes: string | null;
  occurred_at: string;
};

export type DispensingOrder = DispensingOrderPayload & {
  id: number;
  visit_id: number;
  customer_id: number;
  prescription_id: number;
  prescription_version_number: number;
  vendor_name: string | null;
  order_reference: string;
  status: DispensingOrderStatus;
  has_vendor_document: boolean;
  sent_by: number | null;
  sent_at: string | null;
  delivered_by?: number | null;
  delivered_at?: string | null;
  is_delayed?: boolean;
  events?: OrderStatusEvent[];
  created_by: number | null;
  updated_by: number | null;
  created_at: string;
  updated_at: string;
};

export type DispensingOrderContext = {
  visit_id: number;
  current_prescription_id: number | null;
  current_prescription_version_number: number | null;
  order: DispensingOrder | null;
  is_prescription_stale: boolean;
};

export type DispensingOrderDocumentResponse = {
  order_id: number;
  download_url: string;
};

export type DispensingOrderSendResponse = {
  message: string;
  whatsapp_log_id: number | null;
  provider_message_id: string | null;
};

export type VisitBillSummary = {
  id: number;
  bill_number: string;
  visit_id: number | null;
  dispensing_order_id: number | null;
  grand_total: number;
  paid_total: number;
  balance_amount: number;
  payment_status: "pending" | "partial" | "paid";
  has_invoice: boolean;
};

export type VisitBillingContext = {
  visit_id: number;
  customer_id: number;
  dispensing_order_id: number | null;
  contact_lens_order_id: number | null;
  order_bill: VisitBillSummary | null;
  contact_lens_order_bill: VisitBillSummary | null;
  visit_bills: VisitBillSummary[];
};

export type FollowUpInterval = "one_week" | "fifteen_days" | "one_month" | "custom";
export type FollowUpStatus = "pending" | "completed" | "cancelled";
export type FollowUpType =
  | "contact_lens"
  | "progressive_adaptation"
  | "pediatric_review"
  | "referral_follow_up"
  | "dry_eye_review"
  | "custom";
export type FollowUpReminderState = "not_scheduled" | "scheduled" | "sent" | "failed";

export type ContactLensEyeAssessment = {
  k_reading?: string | null;
  hvid_mm?: string | null;
  tear_film?: string | null;
  tbut_seconds?: string | null;
};

export type ContactLensEyePrescription = {
  power?: string | null;
  base_curve_mm?: string | null;
  diameter_mm?: string | null;
};

export type ContactLensDetails = {
  brand?: string | null;
  material?: string | null;
  replacement_schedule?: string | null;
  wearing_schedule?: string | null;
};

export type ContactLensWorkupPayload = {
  state: Exclude<ExamSectionState, "future">;
  indication: { type?: "cosmetic" | "refractive" | "keratoconus" | "sports" | "therapeutic" | "other" | null; other?: string | null };
  assessment: {
    right: ContactLensEyeAssessment;
    left: ContactLensEyeAssessment;
    clinical_notes?: string | null;
  };
  prescription: {
    right: ContactLensEyePrescription;
    left: ContactLensEyePrescription;
  };
  lens_details: ContactLensDetails;
  trial_training: {
    trial_lens_dispensed: boolean;
    training_status?: string | null;
    notes?: string | null;
  };
};

export type ContactLensWorkup = ContactLensWorkupPayload & {
  saved_at: string | null;
  saved_by: number | null;
};

export type ContactLensOrderPayload = {
  vendor_id: number | null;
  lens_details: ContactLensDetails;
  order_notes: string | null;
  expected_delivery_date?: string | null;
};

export type ContactLensOrder = ContactLensOrderPayload & {
  id: number;
  visit_id: number;
  customer_id: number;
  vendor_name: string | null;
  order_reference: string;
  status: DispensingOrderStatus;
  workup_snapshot: Record<string, unknown>;
  delivered_by?: number | null;
  delivered_at?: string | null;
  is_delayed?: boolean;
  events?: OrderStatusEvent[];
  created_by: number | null;
  updated_by: number | null;
  created_at: string;
  updated_at: string;
};

export type ContactLensFollowUp = {
  id: number;
  customer_id: number;
  visit_id: number;
  contact_lens_order_id: number | null;
  task_type: FollowUpType;
  interval: FollowUpInterval | null;
  due_date: string;
  status: FollowUpStatus;
  assigned_staff_id: number | null;
  reminder_state: FollowUpReminderState;
  notes: string | null;
  completion_notes: string | null;
  completed_by: number | null;
  completed_at: string | null;
  created_by: number | null;
  updated_by: number | null;
  created_at: string;
  updated_at: string;
};

export type FollowUpCreatePayload = {
  task_type: FollowUpType;
  due_date: string;
  assigned_staff_id?: number | null;
  reminder_state: FollowUpReminderState;
  notes?: string | null;
};

export type FollowUpListResponse = {
  visit_id: number;
  items: ContactLensFollowUp[];
  total: number;
};

export type ContactLensContext = {
  visit_id: number;
  is_activated: boolean;
  workup: ContactLensWorkup | null;
  order: ContactLensOrder | null;
  follow_up: ContactLensFollowUp | null;
  active_bill_id: number | null;
};
