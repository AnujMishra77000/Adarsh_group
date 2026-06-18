import type { ExamSectionState } from "@/types/visit";

export const SECTION_STATE_LABELS: Record<ExamSectionState, string> = {
  incomplete: "Incomplete",
  complete: "Complete",
  optional: "Optional",
  not_applicable: "Not applicable",
  future: "Future"
};

export const SECTION_STATE_OPTIONS: Array<{ value: Exclude<ExamSectionState, "future">; label: string }> = [
  { value: "incomplete", label: "Incomplete" },
  { value: "complete", label: "Complete" },
  { value: "optional", label: "Optional" },
  { value: "not_applicable", label: "Not applicable" }
];

export type SectionFormKind =
  | "overview"
  | "eye-grid"
  | "binocular"
  | "cycloplegic"
  | "final-prescription"
  | "torch-light"
  | "slit-lamp"
  | "referral"
  | "dispensing"
  | "lens-order"
  | "billing"
  | "follow-up"
  | "generic";

export const SECTION_FORM_KIND: Record<string, SectionFormKind> = {
  patient_visit: "overview",
  visual_acuity: "eye-grid",
  objective_refraction: "eye-grid",
  subjective_refraction: "eye-grid",
  binocular_vision: "binocular",
  cycloplegic_refraction: "cycloplegic",
  final_prescription: "final-prescription",
  potential_vision: "eye-grid",
  torch_light_evaluation: "torch-light",
  slit_lamp_evaluation: "slit-lamp",
  referral: "referral",
  frame_dispensing: "dispensing",
  lens_order: "lens-order",
  contact_lens: "generic",
  billing: "billing",
  completion_follow_up: "follow-up"
};

export const ACUITY_OPTIONS = ["", "6/5", "6/6", "6/9", "6/12", "6/18", "6/24", "6/36", "6/60", "N5", "N6", "N8", "N10", "CF", "HM", "PL"];
export const REFRACTION_OPTIONS = [
  "",
  "Plano",
  "-0.25",
  "-0.50",
  "-0.75",
  "-1.00",
  "-1.25",
  "-1.50",
  "-2.00",
  "+0.25",
  "+0.50",
  "+0.75",
  "+1.00",
  "+1.25",
  "+1.50",
  "+2.00"
];
export const OBJECTIVE_METHOD_OPTIONS = [
  { value: "", label: "Select method" },
  { value: "autorefractometer", label: "Autorefractometer" },
  { value: "retinoscopy", label: "Retinoscopy" },
  { value: "mohindra_retinoscopy", label: "Mohindra retinoscopy" },
  { value: "dynamic_retinoscopy", label: "Dynamic retinoscopy" }
];
export const OCULAR_ALIGNMENT_OPTIONS = ["", "Orthophoria", "Esophoria", "Exophoria", "Esotropia", "Exotropia", "Hypertropia", "Hypotropia"];
export const COVER_TEST_OPTIONS = ["", "Orthophoria", "Eso", "Exo", "Hyper", "Hypo", "Intermittent deviation"];
export const WORTH_FOUR_DOT_OPTIONS = ["", "Fusion", "Suppression right eye", "Suppression left eye", "Diplopia"];
export const TORCH_FINDING_OPTIONS = [
  "",
  "Swelling",
  "Redness",
  "Discharge",
  "Opacity",
  "Foreign body",
  "Irregular pupil",
  "Other"
];
export const SLIT_LAMP_FINDING_OPTIONS = [
  "",
  "Cataract",
  "Dry eye",
  "Pterygium",
  "Keratitis",
  "Corneal scar",
  "Conjunctival congestion",
  "Anterior chamber reaction",
  "Other"
];
export const SLIT_LAMP_GRADE_OPTIONS = ["", "Trace", "Mild", "Moderate", "Severe"];
export const CATARACT_GRADE_OPTIONS = ["", "Grade 1", "Grade 2", "Grade 3", "Grade 4", "Mature", "Hypermature"];
export const REFERRAL_SPECIALIST_OPTIONS = [
  "",
  "Ophthalmologist",
  "Retina specialist",
  "Glaucoma specialist",
  "Cornea specialist",
  "Pediatric ophthalmologist",
  "Other"
];
export const REFERRAL_STATUS_OPTIONS = ["", "Pending", "Sent", "Completed", "Cancelled", "Follow-up planned"];
export const YES_NO_OPTIONS = ["", "Yes", "No"];
