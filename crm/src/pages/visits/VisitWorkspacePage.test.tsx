import { screen, waitFor, within } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import {
  activateContactLensWorkup,
  completeVisit,
  createVisitPrescriptionAmendment,
  finalizeVisitPrescription,
  generateVisitPrescriptionPdf,
  getDispensingOrderContext,
  getContactLensContext,
  getVisitBillingContext,
  getVisit,
  getVisitPrescriptionReview,
  getVisitPrescriptionSummary,
  listVisitExamSectionHistory,
  listVisitExamSections,
  saveVisitExamSection,
  saveDispensingOrder,
  saveContactLensWorkup,
  relinkDispensingOrderPrescription,
  linkExistingBillToVisit,
  saveVisitPrescriptionDraft
} from "@/features/visits/api";
import { listVendors } from "@/features/vendors/api";
import { listBills } from "@/features/bills/api";
import { CRM_PATHS } from "@/lib/routes";
import { VisitWorkspacePage } from "@/pages/visits/VisitWorkspacePage";
import { renderWithProviders } from "@/test/render";

vi.mock("@/features/visits/api", () => ({
  activateContactLensWorkup: vi.fn(),
  getContactLensContext: vi.fn(),
  saveContactLensWorkup: vi.fn(),
  saveContactLensOrder: vi.fn(),
  changeContactLensOrderStatus: vi.fn(),
  scheduleContactLensFollowUp: vi.fn(),
  changeContactLensFollowUpStatus: vi.fn(),
  getVisit: vi.fn(),
  listVisitExamSectionHistory: vi.fn(),
  listVisitExamSections: vi.fn(),
  saveVisitExamSection: vi.fn(),
  getVisitPrescriptionSummary: vi.fn(),
  saveVisitPrescriptionDraft: vi.fn(),
  getVisitPrescriptionReview: vi.fn(),
  finalizeVisitPrescription: vi.fn(),
  createVisitPrescriptionAmendment: vi.fn(),
  generateVisitPrescriptionPdf: vi.fn(),
  completeVisit: vi.fn(),
  getDispensingOrderContext: vi.fn(),
  saveDispensingOrder: vi.fn(),
  relinkDispensingOrderPrescription: vi.fn(),
  changeDispensingOrderStatus: vi.fn(),
  generateDispensingOrderVendorDocument: vi.fn(),
  sendDispensingOrderToVendor: vi.fn(),
  getVisitBillingContext: vi.fn(),
  linkExistingBillToVisit: vi.fn()
}));

vi.mock("@/features/vendors/api", () => ({
  listVendors: vi.fn()
}));

vi.mock("@/features/bills/api", () => ({
  listBills: vi.fn()
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn()
  }
}));

const mockedGetVisit = vi.mocked(getVisit);
const mockedActivateContactLensWorkup = vi.mocked(activateContactLensWorkup);
const mockedGetContactLensContext = vi.mocked(getContactLensContext);
const mockedSaveContactLensWorkup = vi.mocked(saveContactLensWorkup);
const mockedListVisitExamSectionHistory = vi.mocked(listVisitExamSectionHistory);
const mockedListVisitExamSections = vi.mocked(listVisitExamSections);
const mockedSaveVisitExamSection = vi.mocked(saveVisitExamSection);
const mockedGetVisitPrescriptionSummary = vi.mocked(getVisitPrescriptionSummary);
const mockedSaveVisitPrescriptionDraft = vi.mocked(saveVisitPrescriptionDraft);
const mockedGetVisitPrescriptionReview = vi.mocked(getVisitPrescriptionReview);
const mockedFinalizeVisitPrescription = vi.mocked(finalizeVisitPrescription);
const mockedCreateVisitPrescriptionAmendment = vi.mocked(createVisitPrescriptionAmendment);
const mockedGenerateVisitPrescriptionPdf = vi.mocked(generateVisitPrescriptionPdf);
const mockedCompleteVisit = vi.mocked(completeVisit);
const mockedGetDispensingOrderContext = vi.mocked(getDispensingOrderContext);
const mockedSaveDispensingOrder = vi.mocked(saveDispensingOrder);
const mockedRelinkDispensingOrderPrescription = vi.mocked(relinkDispensingOrderPrescription);
const mockedListVendors = vi.mocked(listVendors);
const mockedGetVisitBillingContext = vi.mocked(getVisitBillingContext);
const mockedLinkExistingBillToVisit = vi.mocked(linkExistingBillToVisit);
const mockedListBills = vi.mocked(listBills);

const visit = {
  id: 12,
  shop_key: "adarsh-optical-centre",
  customer_id: 4,
  customer_name: "Riya Shah",
  customer_business_id: "CUST-20260617-000001",
  customer_contact_no: "9876500100",
  visit_date: "2026-06-17T11:30:00Z",
  reason_for_visit: "Blurred distance vision",
  referred_by: "Walk-in",
  assigned_examiner_id: 2,
  assigned_examiner_name: "Admin",
  visit_notes: "Draft visit",
  contact_lens_workup_requested: false,
  status: "draft",
  created_at: "2026-06-17T11:30:00Z",
  updated_at: "2026-06-17T11:30:00Z",
  created_by: 2,
  updated_by: 2
} as const;

const sectionKeys = [
  ["patient_visit", "Patient and Visit", "complete"],
  ["visual_acuity", "Visual Acuity", "incomplete"],
  ["objective_refraction", "Objective Refraction", "incomplete"],
  ["subjective_refraction", "Subjective Refraction", "incomplete"],
  ["binocular_vision", "Binocular Vision", "optional"],
  ["cycloplegic_refraction", "Cycloplegic Refraction", "not_applicable"],
  ["final_prescription", "Final Prescription", "incomplete"],
  ["potential_vision", "Potential Vision", "optional"],
  ["torch_light_evaluation", "Torch-Light Evaluation", "optional"],
  ["slit_lamp_evaluation", "Slit-Lamp Evaluation", "optional"],
  ["referral", "Referral", "not_applicable"],
  ["frame_dispensing", "Frame and Dispensing", "optional"],
  ["lens_order", "Lens Order", "optional"],
  ["contact_lens", "Contact Lens", "not_applicable"],
  ["billing", "Billing", "optional"],
  ["completion_follow_up", "Completion and Follow-Up", "incomplete"],
  ["iop_future", "IOP Future Module", "future"]
] as const;

const prescriptionData = {
  distance: {
    right: { sph: "-1.00", cyl: "-0.50", axis: "90", add: null, va: "6/6" },
    left: { sph: "-0.75", cyl: "-0.25", axis: "80", add: null, va: "6/6" }
  },
  near: {
    right: { sph: "+0.50", cyl: null, axis: null, add: "+1.50", va: "N6" },
    left: { sph: "+0.50", cyl: null, axis: null, add: "+1.50", va: "N6" }
  },
  pd: "62",
  fitting_height: "18"
};

const draftPrescription = {
  id: 31,
  visit_id: 12,
  customer_id: 4,
  version_number: 1,
  status: "draft",
  is_current: false,
  data: prescriptionData,
  patient_instructions: "Use for distance and reading.",
  amends_prescription_id: null,
  finalized_by: null,
  finalized_at: null,
  created_at: "2026-06-18T09:30:00Z",
  updated_at: "2026-06-18T09:30:00Z",
  created_by: 2,
  updated_by: 2,
  has_pdf: false
} as const;

const finalizedPrescription = {
  ...draftPrescription,
  status: "finalized",
  is_current: true,
  finalized_by: 2,
  finalized_at: "2026-06-18T10:00:00Z"
} as const;

const dispensingOrder = {
  id: 41,
  visit_id: 12,
  customer_id: 4,
  prescription_id: 31,
  prescription_version_number: 1,
  vendor_id: 8,
  vendor_name: "Clear View Lab",
  order_reference: "DO-20260618-ABCD1234",
  status: "draft",
  frame: {
    brand: "Ray-Ban",
    model_number: "RX-5228",
    colour_code: "2000",
    frame_type: "Full rim",
    barcode: "8901234567890",
    a_size_mm: "52",
    b_size_mm: "34",
    dbl_mm: "17",
    temple_length_mm: "140",
    effective_diameter_mm: "56"
  },
  measurements: {
    right_monocular_pd_mm: "31",
    left_monocular_pd_mm: "31",
    total_pd_mm: "62",
    right_fitting_height_mm: "18",
    left_fitting_height_mm: "18",
    right_segment_height_mm: "17",
    left_segment_height_mm: "17",
    pantoscopic_tilt_degrees: "8",
    vertex_distance_mm: "12",
    measured_by: "Admin",
    measurement_notes: "Confirmed twice"
  },
  lens: {
    lens_type: "progressive",
    brand: "Essilor",
    material: "MR-8",
    index: "1.60",
    design: "Varilux Comfort",
    coating: "Crizal Sapphire",
    tint_or_photochromic: "Transitions Gen S"
  },
  manufacturing_instructions: "Verify centration before edging.",
  has_vendor_document: false,
  sent_by: null,
  sent_at: null,
  created_by: 2,
  updated_by: 2,
  created_at: "2026-06-18T11:00:00Z",
  updated_at: "2026-06-18T11:00:00Z"
} as const;

function mockSections(contactLensVisible = false) {
  mockedGetVisitBillingContext.mockResolvedValue({
    visit_id: 12,
    customer_id: 4,
    dispensing_order_id: null,
    contact_lens_order_id: null,
    order_bill: null,
    contact_lens_order_bill: null,
    visit_bills: []
  });
  mockedListVisitExamSections.mockResolvedValue({
    visit_id: 12,
    sections: sectionKeys.map(([key, title, state], index) => ({
      key,
      title,
      description: `${title} section`,
      state,
      is_required: state === "incomplete" || key === "patient_visit",
      is_optional: state === "optional",
      is_disabled: key === "iop_future",
      is_visible: key !== "contact_lens" || contactLensVisible,
      payload: key === "visual_acuity" ? { notes: "Previous draft" } : {},
      saved_at: index === 0 ? "2026-06-17T11:35:00Z" : null,
      saved_by: index === 0 ? 2 : null
    })),
    total: sectionKeys.length
  });
}

function mockHistory() {
  mockedListVisitExamSectionHistory.mockResolvedValue({
    visit_id: 12,
    items: [
      {
        visit_id: 9,
        visit_date: "2026-05-01T10:00:00Z",
        section_key: "visual_acuity",
        title: "Visual Acuity",
        state: "complete",
        payload: {
          distance: {
            right: { unaided: "6/9" },
            left: { unaided: "6/12" },
            both: { unaided: "6/9" }
          }
        },
        saved_at: "2026-05-01T10:10:00Z",
        saved_by: 2
      }
    ],
    total: 1
  });
}

function renderVisitWorkspace() {
  renderWithProviders(
    <Routes>
      <Route path={`${CRM_PATHS.visitWorkspace}/:visitId`} element={<VisitWorkspacePage />} />
    </Routes>,
    { route: `${CRM_PATHS.visitWorkspace}/12` }
  );
}

describe("VisitWorkspacePage examination workspace", () => {
  it("activates the hidden Contact Lens section explicitly", async () => {
    mockedGetVisit.mockResolvedValue(visit);
    mockSections();
    mockHistory();
    mockedGetContactLensContext.mockResolvedValue({
      visit_id: 12,
      is_activated: false,
      workup: null,
      order: null,
      follow_up: null,
      active_bill_id: null
    } as never);
    mockedActivateContactLensWorkup.mockResolvedValue({
      visit_id: 12,
      is_activated: true,
      workup: null,
      order: null,
      follow_up: null,
      active_bill_id: null
    } as never);

    const { user } = renderWithProviders(
      <Routes>
        <Route path={`${CRM_PATHS.visitWorkspace}/:visitId`} element={<VisitWorkspacePage />} />
      </Routes>,
      { route: `${CRM_PATHS.visitWorkspace}/12` }
    );

    await user.click(await screen.findByRole("button", { name: /start contact lens work-up/i }));

    await waitFor(() => expect(mockedActivateContactLensWorkup).toHaveBeenCalledWith(12));
    expect(await screen.findByRole("heading", { name: /contact lens workspace/i })).toBeInTheDocument();
  });

  it("shows the five Contact Lens tabs and saves paired-eye work-up values", async () => {
    mockedGetVisit.mockResolvedValue({ ...visit, contact_lens_workup_requested: true });
    mockSections(true);
    mockHistory();
    const context = {
      visit_id: 12,
      is_activated: true,
      workup: {
        state: "incomplete",
        indication: { type: "refractive", other: null },
        assessment: {
          right: { k_reading: "43.25 / 44.00", hvid_mm: "11.8", tear_film: "Normal", tbut_seconds: "9" },
          left: { k_reading: "43.50 / 44.25", hvid_mm: "11.7", tear_film: "Mild dryness", tbut_seconds: "8" },
          clinical_notes: "Good candidate"
        },
        prescription: {
          right: { power: "-2.00", base_curve_mm: "8.6", diameter_mm: "14.2" },
          left: { power: "-1.75", base_curve_mm: "8.6", diameter_mm: "14.2" }
        },
        lens_details: {
          brand: "Acuvue Oasys",
          material: "Senofilcon A",
          replacement_schedule: "Fortnightly",
          wearing_schedule: "Daily wear"
        },
        trial_training: { trial_lens_dispensed: true, training_status: "completed", notes: "Independent" },
        saved_at: null,
        saved_by: null
      },
      order: null,
      follow_up: null,
      active_bill_id: null
    } as const;
    mockedGetContactLensContext.mockResolvedValue(context as never);
    mockedSaveContactLensWorkup.mockResolvedValue({ ...context.workup, state: "complete" } as never);

    const { user } = renderWithProviders(
      <Routes>
        <Route path={`${CRM_PATHS.visitWorkspace}/:visitId`} element={<VisitWorkspacePage />} />
      </Routes>,
      { route: `${CRM_PATHS.visitWorkspace}/12` }
    );

    await user.click(await screen.findByRole("button", { name: /^contact lens/i }));

    expect(await screen.findByRole("heading", { name: /contact lens workspace/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^work-up$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^prescription$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /trial & training/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^order$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^follow-up$/i })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /^prescription$/i }));
    expect(screen.getByLabelText(/right eye power/i)).toHaveValue("-2.00");
    expect(screen.getByLabelText(/left eye power/i)).toHaveValue("-1.75");
    await user.click(screen.getByRole("button", { name: /save work-up/i }));
    await waitFor(() => expect(mockedSaveContactLensWorkup).toHaveBeenCalledWith(
      12,
      expect.objectContaining({
        prescription: expect.objectContaining({
          right: expect.objectContaining({ power: "-2.00" }),
          left: expect.objectContaining({ power: "-1.75" })
        })
      })
    ));
  });

  it("renders visit context, section navigation, disabled IOP, and a section save action", async () => {
    mockedGetVisit.mockResolvedValue(visit);
    mockSections();
    mockHistory();

    renderVisitWorkspace();

    expect(await screen.findByRole("heading", { name: /visit workspace/i })).toBeInTheDocument();
    expect(screen.getByText(/riya shah/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /visual acuity/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /objective refraction/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /final prescription/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /billing/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /completion and follow-up/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /iop future module/i })).toBeDisabled();
    expect(screen.queryByText(/contact lens fitting details/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /save section/i })).toBeInTheDocument();
  });

  it("shows visible save failure state when section save fails", async () => {
    mockedGetVisit.mockResolvedValue(visit);
    mockSections();
    mockHistory();
    mockedSaveVisitExamSection.mockRejectedValue(new Error("Network down"));

    const { user } = renderWithProviders(
      <Routes>
        <Route path={`${CRM_PATHS.visitWorkspace}/:visitId`} element={<VisitWorkspacePage />} />
      </Routes>,
      { route: `${CRM_PATHS.visitWorkspace}/12` }
    );

    await screen.findByRole("button", { name: /save section/i });
    await user.click(screen.getByRole("button", { name: /save section/i }));

    expect(await screen.findByText(/save failed/i)).toBeInTheDocument();
    expect(screen.getByText(/network down/i)).toBeInTheDocument();
  });

  it("shows core visual-acuity fields and previous values without copying them into the draft", async () => {
    mockedGetVisit.mockResolvedValue(visit);
    mockSections();
    mockHistory();

    renderVisitWorkspace();

    expect(await screen.findByRole("heading", { name: /visit workspace/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /^distance vision$/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /^near vision$/i })).toBeInTheDocument();
    expect(screen.getAllByText(/both eyes/i)).toHaveLength(2);
    expect(screen.getAllByText(/contact lens/i).length).toBeGreaterThanOrEqual(2);
    const historyPanel = screen.getByTestId("previous-values-panel");
    expect(historyPanel).toBeInTheDocument();
    expect(within(historyPanel).getByText(/"unaided": "6\/9"/i)).toBeInTheDocument();
    expect(screen.getByText(/review only/i)).toBeInTheDocument();
  });

  it("shows objective refraction method options for normal refraction visits", async () => {
    mockedGetVisit.mockResolvedValue(visit);
    mockSections();
    mockHistory();

    const { user } = renderWithProviders(
      <Routes>
        <Route path={`${CRM_PATHS.visitWorkspace}/:visitId`} element={<VisitWorkspacePage />} />
      </Routes>,
      { route: `${CRM_PATHS.visitWorkspace}/12` }
    );

    await user.click(await screen.findByRole("button", { name: /objective refraction/i }));

    expect(screen.getByLabelText(/method/i)).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /autorefractometer/i })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /^retinoscopy$/i })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /^mohindra retinoscopy$/i })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /^dynamic retinoscopy$/i })).toBeInTheDocument();
  });

  it("shows binocular, torch-light, and slit-lamp advanced clinical fields", async () => {
    mockedGetVisit.mockResolvedValue(visit);
    mockSections();
    mockHistory();

    const { user } = renderWithProviders(
      <Routes>
        <Route path={`${CRM_PATHS.visitWorkspace}/:visitId`} element={<VisitWorkspacePage />} />
      </Routes>,
      { route: `${CRM_PATHS.visitWorkspace}/12` }
    );

    await user.click(await screen.findByRole("button", { name: /binocular vision/i }));

    expect(screen.getByLabelText(/ocular alignment/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/cover test distance/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^npc$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/worth four dot/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /torch-light evaluation/i }));

    expect(screen.getByText(/^lids$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/lids normal/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/lids abnormal finding/i)).toBeInTheDocument();
    expect(screen.getByText(/^pupil$/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /slit-lamp evaluation/i }));

    expect(screen.getByText(/right eye slit-lamp/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/right eye lens finding/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/right eye lens cataract grade/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/left eye cornea finding/i)).toBeInTheDocument();
  });

  it("keeps cycloplegic and referral fields conditional", async () => {
    mockedGetVisit.mockResolvedValue(visit);
    mockSections();
    mockHistory();

    const { user } = renderWithProviders(
      <Routes>
        <Route path={`${CRM_PATHS.visitWorkspace}/:visitId`} element={<VisitWorkspacePage />} />
      </Routes>,
      { route: `${CRM_PATHS.visitWorkspace}/12` }
    );

    await user.click(await screen.findByRole("button", { name: /cycloplegic refraction/i }));

    expect(screen.getByLabelText(/not done/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/drug used/i)).not.toBeInTheDocument();

    await user.click(screen.getByLabelText(/cycloplegic refraction performed/i));

    expect(screen.getByLabelText(/drug used/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/time instilled/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /cycloplegic refraction values/i })).toBeInTheDocument();

    vi.spyOn(window, "confirm").mockReturnValue(true);
    await user.click(screen.getByRole("button", { name: /referral/i }));

    expect(screen.queryByLabelText(/specialist type/i)).not.toBeInTheDocument();
    await user.click(screen.getByLabelText(/referral required/i));
    expect(screen.getByLabelText(/specialist type/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/referral status/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/follow-up information/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /iop future module/i })).toBeDisabled();
  });

  it("supports separate distance and near drafting, structured review, and explicit finalization", async () => {
    mockedGetVisit.mockResolvedValue(visit);
    mockSections();
    mockHistory();
    mockedGetVisitPrescriptionSummary.mockResolvedValue({
      visit_id: 12,
      current_version_id: null,
      draft_version_id: draftPrescription.id,
      versions: [draftPrescription]
    });
    mockedSaveVisitPrescriptionDraft.mockResolvedValue(draftPrescription);
    mockedGetVisitPrescriptionReview.mockResolvedValue({
      prescription: draftPrescription,
      patient: { id: 4, business_id: "CUST-20260617-000001", name: "Riya Shah" },
      visit: {
        id: 12,
        visit_date: visit.visit_date,
        reason_for_visit: visit.reason_for_visit,
        status: "draft",
        shop_key: visit.shop_key,
        branch_name: "Adarsh Optical Centre",
        branch_location: ""
      },
      examiner: { id: 2, name: "Admin" },
      core_examination_summary: {
        subjective_refraction: { state: "complete", payload: { eye_values: { right: { sph: "-1.00" } } } }
      },
      referral_summary: { specialist_type: "Ophthalmologist", referral_status: "Pending" },
      patient_instructions: draftPrescription.patient_instructions,
      warnings: ["Visual Acuity is incomplete"]
    });
    mockedFinalizeVisitPrescription.mockResolvedValue(finalizedPrescription);
    vi.spyOn(window, "confirm").mockReturnValue(true);

    const { user } = renderWithProviders(
      <Routes>
        <Route path={`${CRM_PATHS.visitWorkspace}/:visitId`} element={<VisitWorkspacePage />} />
      </Routes>,
      { route: `${CRM_PATHS.visitWorkspace}/12` }
    );

    await user.click(await screen.findByRole("button", { name: /final prescription/i }));

    expect(await screen.findByRole("heading", { name: /distance prescription/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /near prescription/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/distance prescription right sphere/i)).toHaveValue("-1.00");
    expect(screen.getByLabelText(/patient instructions/i)).toHaveValue("Use for distance and reading.");

    await user.click(screen.getByRole("button", { name: /save prescription draft/i }));
    await waitFor(() => expect(mockedSaveVisitPrescriptionDraft).toHaveBeenCalledWith(12, expect.any(Object)));

    await user.click(screen.getByRole("button", { name: /review prescription/i }));
    expect(await screen.findByRole("heading", { name: /finalization review/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /reviewed prescription values/i })).toBeInTheDocument();
    expect(screen.getByText(/adarsh optical centre/i)).toBeInTheDocument();
    expect(screen.getByText(/visual acuity is incomplete/i)).toBeInTheDocument();
    expect(screen.getByText(/ophthalmologist/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /finalize prescription/i }));
    expect(window.confirm).toHaveBeenCalledWith(expect.stringMatching(/cannot be edited/i));
    await waitFor(() => expect(mockedFinalizeVisitPrescription).toHaveBeenCalledWith(12, 31, { confirmed: true }));
  });

  it("shows current finalized versions read-only and starts amendments without overwriting history", async () => {
    mockedGetVisit.mockResolvedValue(visit);
    mockSections();
    mockHistory();
    mockedGetVisitPrescriptionSummary.mockResolvedValue({
      visit_id: 12,
      current_version_id: finalizedPrescription.id,
      draft_version_id: null,
      versions: [finalizedPrescription]
    });
    mockedCreateVisitPrescriptionAmendment.mockResolvedValue({
      ...draftPrescription,
      id: 32,
      version_number: 2,
      amends_prescription_id: finalizedPrescription.id
    });
    mockedGenerateVisitPrescriptionPdf.mockResolvedValue({
      visit_id: 12,
      prescription_id: 31,
      version_number: 1,
      pdf_url: "/api/v1/visits/12/prescription/pdf/download"
    });
    mockedCompleteVisit.mockResolvedValue({ ...visit, status: "completed" });
    vi.spyOn(window, "confirm").mockReturnValue(true);

    const { user } = renderWithProviders(
      <Routes>
        <Route path={`${CRM_PATHS.visitWorkspace}/:visitId`} element={<VisitWorkspacePage />} />
      </Routes>,
      { route: `${CRM_PATHS.visitWorkspace}/12` }
    );

    await user.click(await screen.findByRole("button", { name: /final prescription/i }));

    expect(await screen.findByText(/current version/i)).toBeInTheDocument();
    expect(screen.getByText(/version 1/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/distance prescription right sphere/i)).toBeDisabled();
    expect(screen.queryByRole("button", { name: /save prescription draft/i })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /start amendment/i }));
    await waitFor(() => expect(mockedCreateVisitPrescriptionAmendment).toHaveBeenCalledWith(12, 31));

    await user.click(screen.getByRole("button", { name: /generate patient pdf/i }));
    await waitFor(() => expect(mockedGenerateVisitPrescriptionPdf).toHaveBeenCalledWith(12));

    await user.click(screen.getByRole("button", { name: /complete visit/i }));
    expect(window.confirm).toHaveBeenCalledWith(expect.stringMatching(/complete this visit/i));
    await waitFor(() => expect(mockedCompleteVisit).toHaveBeenCalledWith(12, { confirmed: true }));
  });

  it("creates a spectacle-order draft with frame details and unit-labelled dispensing measurements", async () => {
    mockedGetVisit.mockResolvedValue(visit);
    mockSections();
    mockHistory();
    mockedGetDispensingOrderContext.mockResolvedValue({
      visit_id: 12,
      current_prescription_id: 31,
      current_prescription_version_number: 1,
      order: null,
      is_prescription_stale: false
    });
    mockedListVendors.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 100 });
    mockedSaveDispensingOrder.mockResolvedValue(dispensingOrder);

    const { user } = renderWithProviders(
      <Routes>
        <Route path={`${CRM_PATHS.visitWorkspace}/:visitId`} element={<VisitWorkspacePage />} />
      </Routes>,
      { route: `${CRM_PATHS.visitWorkspace}/12` }
    );

    await user.click(await screen.findByRole("button", { name: /frame and dispensing/i }));

    expect(await screen.findByText(/prescription version 1/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/frame brand/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/model number/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/a size \(mm\)/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/right monocular pd \(mm\)/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/pantoscopic tilt \(degrees\)/i)).toBeInTheDocument();

    await user.type(screen.getByLabelText(/frame brand/i), "Ray-Ban");
    await user.type(screen.getByLabelText(/model number/i), "RX-5228");
    await user.type(screen.getByLabelText(/right monocular pd \(mm\)/i), "31");
    await user.type(screen.getByLabelText(/left monocular pd \(mm\)/i), "31");
    await user.click(screen.getByRole("button", { name: /save spectacle order/i }));

    await waitFor(() =>
      expect(mockedSaveDispensingOrder).toHaveBeenCalledWith(
        12,
        expect.objectContaining({
          frame: expect.objectContaining({ brand: "Ray-Ban", model_number: "RX-5228" }),
          measurements: expect.objectContaining({ right_monocular_pd_mm: "31", left_monocular_pd_mm: "31" })
        })
      )
    );
  });

  it("shows lens/vendor controls and requires an explicit relink for a stale prescription", async () => {
    mockedGetVisit.mockResolvedValue(visit);
    mockSections();
    mockHistory();
    mockedGetDispensingOrderContext.mockResolvedValue({
      visit_id: 12,
      current_prescription_id: 32,
      current_prescription_version_number: 2,
      order: dispensingOrder,
      is_prescription_stale: true
    });
    mockedListVendors.mockResolvedValue({
      items: [
        {
          id: 8,
          vendor_name: "Clear View Lab",
          contact_person: "Lab Desk",
          whatsapp_no: "9082967356",
          address: null,
          is_active: true,
          created_at: "2026-06-18T10:00:00Z",
          updated_at: "2026-06-18T10:00:00Z"
        }
      ],
      total: 1,
      page: 1,
      page_size: 100
    });
    mockedRelinkDispensingOrderPrescription.mockResolvedValue({
      ...dispensingOrder,
      prescription_id: 32,
      prescription_version_number: 2
    });

    const { user } = renderWithProviders(
      <Routes>
        <Route path={`${CRM_PATHS.visitWorkspace}/:visitId`} element={<VisitWorkspacePage />} />
      </Routes>,
      { route: `${CRM_PATHS.visitWorkspace}/12` }
    );

    await user.click(await screen.findByRole("button", { name: /lens order/i }));

    expect(await screen.findByText(/older prescription version/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/lens type/i)).toHaveValue("progressive");
    expect(screen.getByLabelText(/^vendor$/i)).toHaveValue("8");
    expect(screen.getByLabelText(/manufacturing instructions/i)).toHaveValue("Verify centration before edging.");
    expect(screen.getByRole("button", { name: /send to vendor/i })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: /relink to version 2/i }));
    await waitFor(() => expect(mockedRelinkDispensingOrderPrescription).toHaveBeenCalledWith(12));
  });

  it("uses one shared billing handoff and links an existing official bill", async () => {
    mockedGetVisit.mockResolvedValue(visit);
    mockSections();
    mockHistory();
    mockedGetVisitBillingContext.mockResolvedValue({
      visit_id: 12,
      customer_id: 4,
      dispensing_order_id: 41,
      contact_lens_order_id: null,
      order_bill: null,
      contact_lens_order_bill: null,
      visit_bills: []
    });
    mockedListBills.mockResolvedValue({
      items: [
        {
          id: 71,
          bill_number: "BILL-20260618-0071",
          customer_id: 4,
          visit_id: null,
          dispensing_order_id: null,
          contact_lens_order_id: null,
          customer_name_snapshot: "Riya Shah",
          product_name: "Frame",
          frame_name: "Frame",
          whole_price: 5000,
          discount: 200,
          final_price: 4800,
          paid_amount: 2000,
          subtotal: 5000,
          discount_total: 200,
          tax_total: 0,
          grand_total: 4800,
          paid_total: 2000,
          balance_amount: 2800,
          payment_mode: "upi",
          payment_status: "partial",
          items: [],
          payments: [],
          delivery_date: null,
          notes: null,
          pdf_url: null,
          created_at: "2026-06-18T11:00:00Z",
          updated_at: "2026-06-18T11:00:00Z",
          created_by: 2,
          updated_by: 2,
          is_deleted: false,
          customer_name: "Riya Shah",
          customer_business_id: "CUST-20260617-000001",
          customer_contact_no: "9876500100"
        }
      ],
      total: 1,
      page: 1,
      page_size: 100
    });
    mockedLinkExistingBillToVisit.mockResolvedValue({} as never);

    const { user } = renderWithProviders(
      <Routes>
        <Route path={`${CRM_PATHS.visitWorkspace}/:visitId`} element={<VisitWorkspacePage />} />
      </Routes>,
      { route: `${CRM_PATHS.visitWorkspace}/12` }
    );

    await user.click(await screen.findByRole("button", { name: /billing/i }));

    expect(await screen.findByRole("heading", { name: /billing and payment/i })).toBeInTheDocument();
    const createLink = screen.getByRole("link", { name: /create bill/i });
    expect(createLink).toHaveAttribute("href", expect.stringContaining("visit_id=12"));
    expect(createLink).toHaveAttribute("href", expect.stringContaining("dispensing_order_id=41"));
    await user.selectOptions(screen.getByLabelText(/existing bill/i), "71");
    await user.click(screen.getByRole("button", { name: /link selected bill/i }));
    await waitFor(() =>
      expect(mockedLinkExistingBillToVisit).toHaveBeenCalledWith(12, {
        bill_id: 71,
        dispensing_order_id: 41
      })
    );
  });
});
