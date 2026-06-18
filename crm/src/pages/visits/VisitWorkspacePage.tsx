import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, FileText, Receipt } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";

import {
  activateContactLensWorkup,
  changeVisitFollowUpStatus,
  createVisitFollowUp,
  getVisit,
  listVisitExamSectionHistory,
  listVisitExamSections,
  listVisitFollowUps,
  saveVisitExamSection
} from "@/features/visits/api";
import { getErrorMessage } from "@/lib/errors";
import { CRM_PATHS } from "@/lib/routes";
import {
  ACUITY_OPTIONS,
  CATARACT_GRADE_OPTIONS,
  COVER_TEST_OPTIONS,
  OBJECTIVE_METHOD_OPTIONS,
  OCULAR_ALIGNMENT_OPTIONS,
  REFRACTION_OPTIONS,
  REFERRAL_SPECIALIST_OPTIONS,
  REFERRAL_STATUS_OPTIONS,
  SECTION_FORM_KIND,
  SECTION_STATE_OPTIONS,
  SLIT_LAMP_FINDING_OPTIONS,
  SLIT_LAMP_GRADE_OPTIONS,
  TORCH_FINDING_OPTIONS,
  WORTH_FOUR_DOT_OPTIONS,
  YES_NO_OPTIONS
} from "@/pages/visits/examSections";
import { ClinicalSelect } from "@/pages/visits/components/ClinicalSelect";
import { ExamSectionNav } from "@/pages/visits/components/ExamSectionNav";
import { EyeEntryGrid, type EyeEntryValue } from "@/pages/visits/components/EyeEntryGrid";
import { SectionSaveBar } from "@/pages/visits/components/SectionSaveBar";
import { FinalPrescriptionWorkspace } from "@/pages/visits/components/FinalPrescriptionWorkspace";
import { DispensingOrderWorkspace } from "@/pages/visits/components/DispensingOrderWorkspace";
import { VisitBillingWorkspace } from "@/pages/visits/components/VisitBillingWorkspace";
import { ContactLensWorkspace } from "@/pages/visits/components/ContactLensWorkspace";
import type {
  ExamSectionState,
  FollowUpReminderState,
  FollowUpType,
  VisitExamSection,
  VisitExamSectionHistoryItem
} from "@/types/visit";

type EditableExamSectionState = Exclude<ExamSectionState, "future">;
type SectionPayload = Record<string, unknown>;
type SaveState = "idle" | "dirty" | "saving" | "saved" | "failed";

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString([], {
    dateStyle: "medium",
    timeStyle: "short"
  });
}

function formatStatus(value: string): string {
  return value.replace(/_/g, " ");
}

function editableState(state: ExamSectionState): EditableExamSectionState {
  return state === "future" ? "incomplete" : state;
}

function isRecord(value: unknown): value is SectionPayload {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function readString(payload: SectionPayload, key: string): string {
  const value = payload[key];
  return typeof value === "string" ? value : "";
}

function readBoolean(payload: SectionPayload, key: string): boolean {
  return payload[key] === true;
}

function readEyeGrid(payload: SectionPayload): EyeEntryValue {
  const value = payload.eye_values;
  return isRecord(value) ? (value as EyeEntryValue) : {};
}

function readNamedEyeGrid(payload: SectionPayload, key: string): EyeEntryValue {
  const value = payload[key];
  return isRecord(value) ? (value as EyeEntryValue) : {};
}

function readRecord(payload: SectionPayload, key: string): SectionPayload {
  const value = payload[key];
  return isRecord(value) ? value : {};
}

function readNestedRecord(payload: SectionPayload, firstKey: string, secondKey: string): SectionPayload {
  const parent = readRecord(payload, firstKey);
  const value = parent[secondKey];
  return isRecord(value) ? value : {};
}

function readDeepRecord(payload: SectionPayload, firstKey: string, secondKey: string, thirdKey: string): SectionPayload {
  const parent = readNestedRecord(payload, firstKey, secondKey);
  const value = parent[thirdKey];
  return isRecord(value) ? value : {};
}

function readFirstString(payload: SectionPayload, key: string): string {
  const value = payload[key];
  if (Array.isArray(value)) {
    const first = value.find((item) => typeof item === "string" && item.trim().length > 0);
    return typeof first === "string" ? first : "";
  }
  return typeof value === "string" ? value : "";
}

function withPayloadValue(payload: SectionPayload, key: string, value: unknown): SectionPayload {
  return { ...payload, [key]: value };
}

function textInputClass() {
  return "h-10 w-full rounded-lg border border-pink-300/25 bg-matte-900 px-3 text-sm text-slate-100 outline-none focus:border-pink-200";
}

function textAreaClass() {
  return "w-full rounded-lg border border-pink-300/25 bg-matte-900 px-3 py-2 text-sm text-slate-100 outline-none focus:border-pink-200";
}

export function VisitWorkspacePage() {
  const params = useParams<{ visitId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const visitId = Number(params.visitId);

  const [activeSectionKey, setActiveSectionKey] = useState("visual_acuity");
  const [draftPayload, setDraftPayload] = useState<SectionPayload>({});
  const [draftState, setDraftState] = useState<EditableExamSectionState>("incomplete");
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [saveError, setSaveError] = useState<string | null>(null);
  const [prescriptionDirty, setPrescriptionDirty] = useState(false);
  const [contactLensDirty, setContactLensDirty] = useState(false);

  const visitQuery = useQuery({
    queryKey: ["visits", visitId],
    queryFn: () => getVisit(visitId),
    enabled: Number.isFinite(visitId) && visitId > 0
  });

  const sectionsQuery = useQuery({
    queryKey: ["visits", visitId, "exam-sections"],
    queryFn: () => listVisitExamSections(visitId),
    enabled: Number.isFinite(visitId) && visitId > 0
  });

  const historyQuery = useQuery({
    queryKey: ["visits", visitId, "exam-section-history"],
    queryFn: () => listVisitExamSectionHistory(visitId),
    enabled: Number.isFinite(visitId) && visitId > 0
  });

  const saveMutation = useMutation({
    mutationFn: ({ sectionKey, state, payload }: { sectionKey: string; state: EditableExamSectionState; payload: SectionPayload }) =>
      saveVisitExamSection(visitId, sectionKey, { state, payload })
  });
  const activateContactLensMutation = useMutation({
    mutationFn: () => activateContactLensWorkup(visitId),
    onSuccess: (context) => {
      queryClient.setQueryData(["visits", visitId, "contact-lens"], context);
      setActiveSectionKey("contact_lens");
      queryClient.invalidateQueries({ queryKey: ["visits", visitId, "exam-sections"] });
      queryClient.invalidateQueries({ queryKey: ["visits", visitId] });
    }
  });

  const sections = useMemo(() => sectionsQuery.data?.sections ?? [], [sectionsQuery.data?.sections]);
  const activeSection = useMemo(
    () => sections.find((section) => section.key === activeSectionKey) ?? sections.find((section) => !section.is_disabled) ?? null,
    [activeSectionKey, sections]
  );
  const activeHistory = useMemo(
    () => (historyQuery.data?.items ?? []).filter((item) => item.section_key === activeSection?.key),
    [activeSection?.key, historyQuery.data?.items]
  );
  const isFinalPrescriptionSection = activeSection?.key === "final_prescription";
  const isDispensingOrderSection = activeSection?.key === "frame_dispensing" || activeSection?.key === "lens_order";
  const isBillingSection = activeSection?.key === "billing";
  const isContactLensSection = activeSection?.key === "contact_lens";
  const isFollowUpSection = activeSection?.key === "completion_follow_up";

  useEffect(() => {
    if (!activeSection) {
      return;
    }
    setActiveSectionKey(activeSection.key);
    setDraftPayload(activeSection.payload ?? {});
    setDraftState(editableState(activeSection.state));
    setSaveState("idle");
    setSaveError(null);
  }, [activeSection]);

  useEffect(() => {
    const handler = (event: BeforeUnloadEvent) => {
      if (saveState !== "dirty" && saveState !== "failed" && !prescriptionDirty && !contactLensDirty) {
        return;
      }
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [contactLensDirty, prescriptionDirty, saveState]);

  if (!Number.isFinite(visitId) || visitId <= 0) {
    return (
      <section className="rounded-2xl border border-rose-300/25 bg-matte-850/90 p-5 text-sm text-rose-100 shadow-neon-ring">
        Visit not found.
      </section>
    );
  }

  const markDirty = (nextPayload: SectionPayload) => {
    setDraftPayload(nextPayload);
    setSaveState("dirty");
    setSaveError(null);
  };

  const updateField = (key: string, value: unknown) => markDirty(withPayloadValue(draftPayload, key, value));

  const handleSectionSelect = (section: VisitExamSection) => {
    if (section.is_disabled) {
      return;
    }
    if (
      (saveState === "dirty" || saveState === "failed" || prescriptionDirty || contactLensDirty) &&
      !window.confirm("Leave this section without saving changes?")
    ) {
      return;
    }
    setPrescriptionDirty(false);
    setContactLensDirty(false);
    setActiveSectionKey(section.key);
  };

  const handleBack = () => {
    if (
      (saveState === "dirty" || saveState === "failed" || prescriptionDirty || contactLensDirty) &&
      !window.confirm("Leave this visit without saving changes?")
    ) {
      return;
    }
    navigate(CRM_PATHS.customers);
  };

  const handleSave = async () => {
    if (!activeSection || activeSection.is_disabled) {
      return;
    }
    setSaveState("saving");
    setSaveError(null);

    try {
      await saveMutation.mutateAsync({
        sectionKey: activeSection.key,
        state: draftState,
        payload: draftPayload
      });
      setSaveState("saved");
      queryClient.invalidateQueries({ queryKey: ["visits", visitId, "exam-sections"] });
      queryClient.invalidateQueries({ queryKey: ["customer-record-detail"] });
    } catch (error) {
      setSaveState("failed");
      setSaveError(getErrorMessage(error));
    }
  };

  return (
    <div className="space-y-6">
      <section className="sticky top-0 z-20 rounded-2xl border border-pink-300/20 bg-matte-900/95 p-4 shadow-neon-ring backdrop-blur">
        <button
          type="button"
          onClick={handleBack}
          className="mb-4 inline-flex items-center gap-2 rounded-lg border border-slate-500/45 px-3 py-2 text-sm font-medium text-slate-200 hover:border-pink-300/35"
        >
          <ArrowLeft size={16} />
          Patient Search
        </button>

        {visitQuery.isLoading && <p className="text-sm text-slate-200">Opening visit...</p>}
        {visitQuery.isError && <p className="text-sm text-rose-200">{getErrorMessage(visitQuery.error)}</p>}

        {visitQuery.data && (
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-pink-200/80">
                {formatStatus(visitQuery.data.status)}
              </p>
              <h2 className="mt-1 text-2xl font-semibold text-slate-100">Visit Workspace</h2>
              <p className="mt-1 text-sm text-slate-300">
                {visitQuery.data.customer_name ?? "Patient"} · {visitQuery.data.customer_business_id ?? "-"} ·{" "}
                {formatDateTime(visitQuery.data.visit_date)}
              </p>
              <p className="mt-1 text-sm text-slate-400">{visitQuery.data.reason_for_visit}</p>
            </div>

            <div className="flex flex-wrap gap-2">
              <Link
                to={`${CRM_PATHS.prescriptions}?${new URLSearchParams({
                  customer_id: String(visitQuery.data.customer_id),
                  customer_query: visitQuery.data.customer_business_id ?? "",
                  contact_no: visitQuery.data.customer_contact_no ?? ""
                }).toString()}`}
                className="inline-flex items-center gap-2 rounded-lg border border-indigo-300/35 bg-indigo-400/10 px-3 py-2 text-sm font-medium text-indigo-100"
              >
                <FileText size={16} />
                Prescription
              </Link>
              <Link
                to={`${CRM_PATHS.billing}?${new URLSearchParams({
                  customer_id: String(visitQuery.data.customer_id),
                  customer_query: visitQuery.data.customer_business_id ?? "",
                  visit_id: String(visitQuery.data.id),
                  return_to: `${CRM_PATHS.visitWorkspace}/${visitQuery.data.id}`
                }).toString()}`}
                className="inline-flex items-center gap-2 rounded-lg border border-emerald-300/35 bg-emerald-400/10 px-3 py-2 text-sm font-medium text-emerald-100"
              >
                <Receipt size={16} />
                Billing
              </Link>
            </div>
          </div>
        )}
      </section>

      {sectionsQuery.isLoading && (
        <section className="rounded-2xl border border-pink-300/20 bg-matte-850/90 p-5 text-sm text-slate-200 shadow-neon-ring">
          Loading examination sections...
        </section>
      )}
      {sectionsQuery.isError && (
        <section className="rounded-2xl border border-rose-300/25 bg-matte-850/90 p-5 text-sm text-rose-100 shadow-neon-ring">
          {getErrorMessage(sectionsQuery.error)}
        </section>
      )}

      {visitQuery.data && activeSection && (
        <div className="grid gap-5 xl:grid-cols-[300px_minmax(0,1fr)]">
          <ExamSectionNav
            sections={sections}
            activeKey={activeSection.key}
            onSelect={handleSectionSelect}
            onActivateContactLens={() => activateContactLensMutation.mutate()}
            activatingContactLens={activateContactLensMutation.isPending}
          />

          <section className="space-y-4 rounded-2xl border border-pink-300/20 bg-matte-850/90 p-5 shadow-neon-ring">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-pink-200/80">
                  {activeSection.is_required ? "Required" : activeSection.is_optional ? "Optional" : "Section"}
                </p>
                <h3 className="mt-1 text-xl font-semibold text-slate-100">{activeSection.title}</h3>
                <p className="mt-1 text-sm text-slate-300">{activeSection.description}</p>
              </div>

              {!isFinalPrescriptionSection && !isDispensingOrderSection && !isBillingSection && !isContactLensSection && !isFollowUpSection && <label className="block min-w-[210px] text-sm text-slate-200">
                <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-400">Section State</span>
                <select
                  value={draftState}
                  onChange={(event) => {
                    setDraftState(event.target.value as EditableExamSectionState);
                    setSaveState("dirty");
                    setSaveError(null);
                  }}
                  className="h-10 w-full rounded-lg border border-pink-300/25 bg-matte-900 px-3 text-sm text-slate-100 outline-none focus:border-pink-200"
                >
                  {SECTION_STATE_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>}
            </div>

            {isFinalPrescriptionSection ? (
              <FinalPrescriptionWorkspace visit={visitQuery.data} onDirtyChange={setPrescriptionDirty} />
            ) : isDispensingOrderSection ? (
              <DispensingOrderWorkspace
                visit={visitQuery.data}
                mode={activeSection.key === "frame_dispensing" ? "frame" : "lens"}
                onDirtyChange={setPrescriptionDirty}
              />
            ) : isBillingSection ? (
              <VisitBillingWorkspace visit={visitQuery.data} />
            ) : isContactLensSection ? (
              <ContactLensWorkspace visit={visitQuery.data} onDirtyChange={setContactLensDirty} />
            ) : isFollowUpSection ? (
              <OperationalFollowUpWorkspace visitId={visitQuery.data.id} />
            ) : (
              <>
                <PreviousValuesPanel items={activeHistory} isLoading={historyQuery.isLoading} />
                {renderSectionForm(activeSection.key, draftPayload, updateField)}
                <SectionSaveBar
                  saveState={saveState}
                  errorMessage={saveError}
                  disabled={activeSection.is_disabled}
                  onSave={handleSave}
                />
              </>
            )}
          </section>
        </div>
      )}
    </div>
  );
}

function OperationalFollowUpWorkspace({ visitId }: { visitId: number }) {
  const queryClient = useQueryClient();
  const [taskType, setTaskType] = useState<FollowUpType>("custom");
  const [dueDate, setDueDate] = useState("");
  const [assignedStaffId, setAssignedStaffId] = useState("");
  const [reminderState, setReminderState] = useState<FollowUpReminderState>("not_scheduled");
  const [notes, setNotes] = useState("");
  const [completionNotes, setCompletionNotes] = useState("");
  const [error, setError] = useState<string | null>(null);

  const followUpsQuery = useQuery({
    queryKey: ["visits", visitId, "follow-ups"],
    queryFn: () => listVisitFollowUps(visitId)
  });
  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ["visits", visitId, "follow-ups"] });
    queryClient.invalidateQueries({ queryKey: ["customer-record-detail"] });
  };
  const createMutation = useMutation({
    mutationFn: () => createVisitFollowUp(visitId, {
      task_type: taskType,
      due_date: dueDate,
      assigned_staff_id: assignedStaffId ? Number(assignedStaffId) : null,
      reminder_state: reminderState,
      notes: notes || null
    }),
    onSuccess: () => {
      setNotes("");
      setError(null);
      refresh();
    },
    onError: (reason) => setError(getErrorMessage(reason))
  });
  const statusMutation = useMutation({
    mutationFn: ({ taskId, status }: { taskId: number; status: "completed" | "cancelled" }) =>
      changeVisitFollowUpStatus(visitId, taskId, {
        status,
        completion_notes: status === "completed" ? completionNotes || null : null
      }),
    onSuccess: () => {
      setCompletionNotes("");
      setError(null);
      refresh();
    },
    onError: (reason) => setError(getErrorMessage(reason))
  });

  return (
    <div className="space-y-5">
      <div>
        <h4 className="text-lg font-semibold text-slate-100">Operational Follow-ups</h4>
        <p className="text-sm text-slate-400">Schedule clinical reviews here. Use the existing Campaigns and communication tools for outbound reminders.</p>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <label className="text-sm text-slate-200"><span className="mb-1 block text-xs uppercase text-slate-400">Follow-up Type</span><select aria-label="Follow-up Type" value={taskType} onChange={(event) => setTaskType(event.target.value as FollowUpType)} className={textInputClass()}><option value="contact_lens">Contact lens</option><option value="progressive_adaptation">Progressive adaptation</option><option value="pediatric_review">Pediatric review</option><option value="referral_follow_up">Referral follow-up</option><option value="dry_eye_review">Dry-eye review</option><option value="custom">Custom</option></select></label>
        <TextField label="Due Date" type="date" value={dueDate} onChange={setDueDate} />
        <TextField label="Assigned Staff ID" type="number" value={assignedStaffId} onChange={setAssignedStaffId} />
        <label className="text-sm text-slate-200"><span className="mb-1 block text-xs uppercase text-slate-400">Reminder State</span><select aria-label="Reminder State" value={reminderState} onChange={(event) => setReminderState(event.target.value as FollowUpReminderState)} className={textInputClass()}><option value="not_scheduled">Not scheduled</option><option value="scheduled">Scheduled</option><option value="sent">Sent</option><option value="failed">Failed</option></select></label>
        <div className="md:col-span-2"><TextAreaField label="Follow-up Notes" value={notes} onChange={setNotes} /></div>
      </div>
      <button type="button" disabled={!dueDate || createMutation.isPending} onClick={() => createMutation.mutate()} className="rounded-lg border border-pink-300/35 px-4 py-2 text-sm font-semibold text-pink-100 disabled:opacity-50">Schedule Follow-up</button>
      {error && <p role="alert" className="text-sm text-rose-200">{error}</p>}
      {followUpsQuery.isLoading && <p className="text-sm text-slate-300">Loading follow-ups...</p>}
      {(followUpsQuery.data?.items ?? []).length > 0 && (
        <section className="space-y-3 border-t border-slate-700/60 pt-4">
          <TextAreaField label="Completion Notes" value={completionNotes} onChange={setCompletionNotes} />
          {(followUpsQuery.data?.items ?? []).map((task) => (
            <article key={task.id} className="rounded-lg border border-slate-700/70 bg-matte-900/60 p-3 text-sm text-slate-200">
              <p className="font-semibold text-pink-100">{formatStatus(task.task_type)} · due {new Date(`${task.due_date}T00:00:00`).toLocaleDateString()}</p>
              <p className="text-xs text-slate-400">{formatStatus(task.status)} · reminder {formatStatus(task.reminder_state)}{task.assigned_staff_id ? ` · staff #${task.assigned_staff_id}` : ""}</p>
              {task.notes && <p className="mt-1">{task.notes}</p>}
              {task.completion_notes && <p className="mt-1 text-emerald-100">Completed: {task.completion_notes}</p>}
              {task.status === "pending" && <div className="mt-3 flex gap-2"><button type="button" onClick={() => statusMutation.mutate({ taskId: task.id, status: "completed" })} className="rounded-md border border-emerald-300/35 px-2 py-1 text-emerald-100">Complete</button><button type="button" onClick={() => statusMutation.mutate({ taskId: task.id, status: "cancelled" })} className="rounded-md border border-rose-300/35 px-2 py-1 text-rose-100">Cancel</button></div>}
            </article>
          ))}
        </section>
      )}
    </div>
  );
}

function renderSectionForm(
  sectionKey: string,
  payload: SectionPayload,
  updateField: (key: string, value: unknown) => void
) {
  const kind = SECTION_FORM_KIND[sectionKey] ?? "generic";

  if (kind === "overview") {
    return (
      <div className="grid gap-3 md:grid-cols-2">
        <ReadOnlyFact label="Visit saved under" value="Patient and branch context" />
        <ReadOnlyFact label="Edit source" value="Use patient record or visit start flow" />
        <TextAreaField label="Workspace notes" value={readString(payload, "notes")} onChange={(value) => updateField("notes", value)} />
      </div>
    );
  }

  if (kind === "binocular") {
    return <BinocularVisionForm payload={payload} updateField={updateField} />;
  }

  if (kind === "eye-grid") {
    if (sectionKey === "visual_acuity") {
      return (
        <div className="space-y-4">
          <EyeEntryGrid
            title="Distance Vision"
            value={readNamedEyeGrid(payload, "distance")}
            rows={["right", "left", "both"]}
            fields={[
              { key: "unaided", label: "Unaided", options: ACUITY_OPTIONS },
              { key: "aided", label: "Aided", options: ACUITY_OPTIONS },
              { key: "pinhole", label: "Pinhole", options: ACUITY_OPTIONS },
              { key: "contact_lens", label: "Contact Lens", options: ACUITY_OPTIONS }
            ]}
            onChange={(value) => updateField("distance", value)}
          />
          <EyeEntryGrid
            title="Near Vision"
            value={readNamedEyeGrid(payload, "near")}
            rows={["right", "left", "both"]}
            fields={[
              { key: "unaided", label: "Unaided", options: ACUITY_OPTIONS },
              { key: "aided", label: "Aided", options: ACUITY_OPTIONS },
              { key: "contact_lens", label: "Contact Lens", options: ACUITY_OPTIONS }
            ]}
            onChange={(value) => updateField("near", value)}
          />
          <TextAreaField label="Visual Acuity Notes" value={readString(payload, "notes")} onChange={(value) => updateField("notes", value)} />
        </div>
      );
    }

    if (sectionKey === "objective_refraction") {
      return (
        <div className="space-y-4">
          <label className="block max-w-sm text-sm text-slate-200">
            <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-400">Method</span>
            <select
              value={readString(payload, "method")}
              onChange={(event) => updateField("method", event.target.value)}
              className="h-10 w-full rounded-lg border border-pink-300/25 bg-matte-900 px-3 text-sm text-slate-100 outline-none focus:border-pink-200"
            >
              {OBJECTIVE_METHOD_OPTIONS.map((option) => (
                <option key={option.value || "blank"} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <EyeEntryGrid
            title="Objective Refraction"
            value={readEyeGrid(payload)}
            fields={[
              { key: "sph", label: "Sphere", options: REFRACTION_OPTIONS },
              { key: "cyl", label: "Cylinder", options: REFRACTION_OPTIONS },
              { key: "axis", label: "Axis" },
              { key: "va", label: "Visual Acuity", options: ACUITY_OPTIONS }
            ]}
            onChange={(value) => updateField("eye_values", value)}
          />
          <TextAreaField label="Objective Refraction Notes" value={readString(payload, "notes")} onChange={(value) => updateField("notes", value)} />
        </div>
      );
    }

    if (sectionKey === "subjective_refraction") {
      return (
        <div className="space-y-4">
          <EyeEntryGrid
            title="Subjective Refraction"
            value={readEyeGrid(payload)}
            fields={[
              { key: "sph", label: "Sphere", options: REFRACTION_OPTIONS },
              { key: "cyl", label: "Cylinder", options: REFRACTION_OPTIONS },
              { key: "axis", label: "Axis" },
              { key: "va", label: "Visual Acuity", options: ACUITY_OPTIONS }
            ]}
            onChange={(value) => updateField("eye_values", value)}
          />
          <TextAreaField label="Subjective Refraction Notes" value={readString(payload, "notes")} onChange={(value) => updateField("notes", value)} />
        </div>
      );
    }

    if (sectionKey === "potential_vision") {
      return (
        <div className="space-y-4">
          <EyeEntryGrid
            title="Potential Vision"
            value={readEyeGrid(payload)}
            fields={[{ key: "potential_va", label: "Potential Vision", options: ACUITY_OPTIONS }]}
            onChange={(value) => updateField("eye_values", value)}
          />
          <TextAreaField label="Potential Vision Notes" value={readString(payload, "notes")} onChange={(value) => updateField("notes", value)} />
        </div>
      );
    }

    return (
      <div className="space-y-4">
        <EyeEntryGrid
          title={sectionKey === "potential_vision" ? "Potential Vision" : "Right and Left Eye"}
          value={readEyeGrid(payload)}
          fields={[{ key: "value", label: "Value" }]}
          onChange={(value) => updateField("eye_values", value)}
        />
        <TextAreaField label="Clinical Notes" value={readString(payload, "notes")} onChange={(value) => updateField("notes", value)} />
      </div>
    );
  }

  if (kind === "cycloplegic") {
    return <CycloplegicForm payload={payload} updateField={updateField} />;
  }

  if (kind === "final-prescription") {
    return (
      <div className="space-y-4">
        <EyeEntryGrid
          title="Final Prescription Review"
          value={readEyeGrid(payload)}
          fields={[
            { key: "sph", label: "SPH", options: REFRACTION_OPTIONS },
            { key: "cyl", label: "CYL", options: REFRACTION_OPTIONS },
            { key: "axis", label: "Axis" },
            { key: "add", label: "ADD", options: REFRACTION_OPTIONS },
            { key: "va", label: "VA", options: ACUITY_OPTIONS }
          ]}
          onChange={(value) => updateField("eye_values", value)}
        />
        <TextAreaField label="Prescription Notes" value={readString(payload, "notes")} onChange={(value) => updateField("notes", value)} />
      </div>
    );
  }

  if (kind === "torch-light") {
    return <TorchLightForm payload={payload} updateField={updateField} />;
  }

  if (kind === "slit-lamp") {
    return <SlitLampForm payload={payload} updateField={updateField} />;
  }

  if (kind === "referral") {
    return <ReferralForm payload={payload} updateField={updateField} />;
  }

  if (kind === "dispensing") {
    return (
      <div className="grid gap-4 md:grid-cols-2">
        <TextField label="Frame Model" value={readString(payload, "frame_model")} onChange={(value) => updateField("frame_model", value)} />
        <TextField label="Frame Size" value={readString(payload, "frame_size")} onChange={(value) => updateField("frame_size", value)} />
        <TextField label="PD" value={readString(payload, "pd")} onChange={(value) => updateField("pd", value)} />
        <TextField label="Fitting Height" value={readString(payload, "fitting_height")} onChange={(value) => updateField("fitting_height", value)} />
        <div className="md:col-span-2">
          <TextAreaField label="Dispensing Notes" value={readString(payload, "notes")} onChange={(value) => updateField("notes", value)} />
        </div>
      </div>
    );
  }

  if (kind === "lens-order") {
    return (
      <div className="grid gap-4 md:grid-cols-2">
        <TextField label="Lens Type" value={readString(payload, "lens_type")} onChange={(value) => updateField("lens_type", value)} />
        <TextField label="Coating" value={readString(payload, "coating")} onChange={(value) => updateField("coating", value)} />
        <TextField label="Vendor / Lab" value={readString(payload, "vendor")} onChange={(value) => updateField("vendor", value)} />
        <ClinicalSelect
          label="Order Sent"
          value={readString(payload, "order_sent")}
          options={YES_NO_OPTIONS}
          onChange={(value) => updateField("order_sent", value)}
        />
        <div className="md:col-span-2">
          <TextAreaField label="Lens Order Notes" value={readString(payload, "notes")} onChange={(value) => updateField("notes", value)} />
        </div>
      </div>
    );
  }

  if (kind === "billing") {
    return (
      <div className="space-y-4">
        <p className="rounded-lg border border-emerald-300/20 bg-emerald-400/10 p-3 text-sm text-emerald-100">
          Billing totals and payments continue to come from the existing billing module.
        </p>
        <TextField label="Linked Bill Number" value={readString(payload, "bill_number")} onChange={(value) => updateField("bill_number", value)} />
        <TextAreaField label="Billing Notes" value={readString(payload, "notes")} onChange={(value) => updateField("notes", value)} />
      </div>
    );
  }

  if (kind === "follow-up") {
    return (
      <div className="grid gap-4 md:grid-cols-2">
        <TextField
          label="Follow-up Date"
          type="date"
          value={readString(payload, "follow_up_date")}
          onChange={(value) => updateField("follow_up_date", value)}
        />
        <TextField label="Follow-up Reason" value={readString(payload, "follow_up_reason")} onChange={(value) => updateField("follow_up_reason", value)} />
        <div className="md:col-span-2">
          <TextAreaField label="Completion Notes" value={readString(payload, "notes")} onChange={(value) => updateField("notes", value)} />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <TextAreaField label="Section Notes" value={readString(payload, "notes")} onChange={(value) => updateField("notes", value)} />
      <ClinicalSelect
        label="Not Done"
        value={readString(payload, "not_done")}
        options={YES_NO_OPTIONS}
        onChange={(value) => updateField("not_done", value)}
      />
    </div>
  );
}

function BinocularVisionForm({ payload, updateField }: { payload: SectionPayload; updateField: (key: string, value: unknown) => void }) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <ClinicalSelect
        label="Ocular Alignment"
        value={readString(payload, "ocular_alignment")}
        options={OCULAR_ALIGNMENT_OPTIONS}
        onChange={(value) => updateField("ocular_alignment", value)}
      />
      <ClinicalSelect
        label="Cover Test Distance"
        value={readString(payload, "cover_test_distance")}
        options={COVER_TEST_OPTIONS}
        onChange={(value) => updateField("cover_test_distance", value)}
      />
      <ClinicalSelect
        label="Cover Test Near"
        value={readString(payload, "cover_test_near")}
        options={COVER_TEST_OPTIONS}
        onChange={(value) => updateField("cover_test_near", value)}
      />
      <TextField label="NPC" value={readString(payload, "npc")} onChange={(value) => updateField("npc", value)} />
      <TextField label="Vergence BO" value={readString(payload, "vergence_bo")} onChange={(value) => updateField("vergence_bo", value)} />
      <TextField label="Vergence BI" value={readString(payload, "vergence_bi")} onChange={(value) => updateField("vergence_bi", value)} />
      <TextField label="Stereoacuity" value={readString(payload, "stereoacuity")} onChange={(value) => updateField("stereoacuity", value)} />
      <TextField label="NRA" value={readString(payload, "nra")} onChange={(value) => updateField("nra", value)} />
      <TextField label="PRA" value={readString(payload, "pra")} onChange={(value) => updateField("pra", value)} />
      <TextField
        label="Accommodation Amplitude"
        value={readString(payload, "accommodation_amplitude")}
        onChange={(value) => updateField("accommodation_amplitude", value)}
      />
      <ClinicalSelect
        label="Worth Four Dot"
        value={readString(payload, "worth_four_dot")}
        options={WORTH_FOUR_DOT_OPTIONS}
        onChange={(value) => updateField("worth_four_dot", value)}
      />
      <div className="md:col-span-2">
        <TextAreaField label="Binocular Vision Notes" value={readString(payload, "notes")} onChange={(value) => updateField("notes", value)} />
      </div>
    </div>
  );
}

function CycloplegicForm({ payload, updateField }: { payload: SectionPayload; updateField: (key: string, value: unknown) => void }) {
  const notDone = readBoolean(payload, "not_done");
  const performed = readBoolean(payload, "performed");
  const showPerformedFields = performed && !notDone;

  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-2">
        <CheckboxField label="Not Done" checked={notDone} onChange={(checked) => updateField("not_done", checked)} />
        <CheckboxField
          label="Cycloplegic refraction performed"
          checked={performed}
          onChange={(checked) => updateField("performed", checked)}
        />
      </div>
      {showPerformedFields && (
        <div className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <TextField label="Drug Used" value={readString(payload, "drug_used")} onChange={(value) => updateField("drug_used", value)} />
            <TextField
              label="Time Instilled"
              type="time"
              value={readString(payload, "time_instilled")}
              onChange={(value) => updateField("time_instilled", value)}
            />
          </div>
          <EyeEntryGrid
            title="Cycloplegic Refraction Values"
            value={readEyeGrid(payload)}
            fields={[
              { key: "sph", label: "SPH", options: REFRACTION_OPTIONS },
              { key: "cyl", label: "CYL", options: REFRACTION_OPTIONS },
              { key: "axis", label: "Axis" },
              { key: "va", label: "VA", options: ACUITY_OPTIONS }
            ]}
            onChange={(value) => updateField("eye_values", value)}
          />
        </div>
      )}
      <TextAreaField label="Cycloplegic Notes" value={readString(payload, "notes")} onChange={(value) => updateField("notes", value)} />
    </div>
  );
}

const TORCH_STRUCTURES = [
  { key: "lids", label: "Lids" },
  { key: "conjunctiva", label: "Conjunctiva" },
  { key: "cornea", label: "Cornea" },
  { key: "pupil", label: "Pupil" }
] as const;

function TorchLightForm({ payload, updateField }: { payload: SectionPayload; updateField: (key: string, value: unknown) => void }) {
  const findings = readRecord(payload, "findings");
  const updateStructure = (key: string, value: SectionPayload) => {
    updateField("findings", { ...findings, [key]: value });
  };

  return (
    <div className="grid gap-4 md:grid-cols-2">
      {TORCH_STRUCTURES.map((structure) => {
        const current = readNestedRecord(payload, "findings", structure.key);
        return (
          <div key={structure.key} className="space-y-3 rounded-xl border border-pink-300/20 bg-matte-800/70 p-4">
            <h4 className="text-sm font-semibold uppercase tracking-wide text-pink-100">{structure.label}</h4>
            <CheckboxField
              label={`${structure.label} Normal`}
              checked={readBoolean(current, "normal")}
              onChange={(checked) =>
                updateStructure(
                  structure.key,
                  checked ? { ...current, normal: true, abnormal_findings: [], notes: "" } : { ...current, normal: false }
                )
              }
            />
            <ClinicalSelect
              label={`${structure.label} Abnormal Finding`}
              value={readFirstString(current, "abnormal_findings")}
              options={TORCH_FINDING_OPTIONS}
              onChange={(value) =>
                updateStructure(structure.key, {
                  ...current,
                  normal: value ? false : readBoolean(current, "normal"),
                  abnormal_findings: value ? [value] : []
                })
              }
            />
            <TextAreaField
              label={`${structure.label} Other / Notes`}
              value={readString(current, "notes")}
              onChange={(value) => updateStructure(structure.key, { ...current, normal: value ? false : readBoolean(current, "normal"), notes: value })}
            />
          </div>
        );
      })}
    </div>
  );
}

const SLIT_LAMP_EYES = [
  { key: "right", label: "Right Eye" },
  { key: "left", label: "Left Eye" }
] as const;

const SLIT_LAMP_STRUCTURES = [
  { key: "eyelids_lashes", label: "Eyelids and Lashes" },
  { key: "conjunctiva", label: "Conjunctiva" },
  { key: "cornea", label: "Cornea" },
  { key: "anterior_chamber", label: "Anterior Chamber" },
  { key: "iris", label: "Iris" },
  { key: "lens", label: "Lens" }
] as const;

function SlitLampForm({ payload, updateField }: { payload: SectionPayload; updateField: (key: string, value: unknown) => void }) {
  const eyes = readRecord(payload, "eyes");
  const updateStructure = (eyeKey: string, structureKey: string, value: SectionPayload) => {
    const eyePayload = readNestedRecord(payload, "eyes", eyeKey);
    updateField("eyes", {
      ...eyes,
      [eyeKey]: {
        ...eyePayload,
        [structureKey]: value
      }
    });
  };

  return (
    <div className="space-y-5">
      {SLIT_LAMP_EYES.map((eye) => (
        <section key={eye.key} className="space-y-3 rounded-xl border border-pink-300/20 bg-matte-800/70 p-4">
          <h4 className="text-sm font-semibold uppercase tracking-wide text-pink-100">{eye.label} Slit-Lamp</h4>
          <div className="grid gap-4 lg:grid-cols-2">
            {SLIT_LAMP_STRUCTURES.map((structure) => {
              const current = readDeepRecord(payload, "eyes", eye.key, structure.key);
              const labelPrefix = `${eye.label} ${structure.label}`;
              return (
                <div key={`${eye.key}-${structure.key}`} className="space-y-3 rounded-lg border border-slate-700/60 bg-matte-900/60 p-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-300">{structure.label}</p>
                  <CheckboxField
                    label={`${labelPrefix} Normal`}
                    checked={readBoolean(current, "normal")}
                    onChange={(checked) =>
                      updateStructure(
                        eye.key,
                        structure.key,
                        checked
                          ? { ...current, normal: true, findings: [], notes: "", cataract_grade: "", grade: "" }
                          : { ...current, normal: false }
                      )
                    }
                  />
                  <ClinicalSelect
                    label={`${labelPrefix} Finding`}
                    value={readFirstString(current, "findings")}
                    options={SLIT_LAMP_FINDING_OPTIONS}
                    onChange={(value) =>
                      updateStructure(eye.key, structure.key, {
                        ...current,
                        normal: value ? false : readBoolean(current, "normal"),
                        findings: value ? [value] : []
                      })
                    }
                  />
                  <ClinicalSelect
                    label={`${labelPrefix} Grade`}
                    value={readString(current, "grade")}
                    options={SLIT_LAMP_GRADE_OPTIONS}
                    onChange={(value) =>
                      updateStructure(eye.key, structure.key, {
                        ...current,
                        normal: value ? false : readBoolean(current, "normal"),
                        grade: value
                      })
                    }
                  />
                  {structure.key === "lens" && (
                    <ClinicalSelect
                      label={`${labelPrefix} Cataract Grade`}
                      value={readString(current, "cataract_grade")}
                      options={CATARACT_GRADE_OPTIONS}
                      onChange={(value) =>
                        updateStructure(eye.key, structure.key, {
                          ...current,
                          normal: value ? false : readBoolean(current, "normal"),
                          cataract_grade: value
                        })
                      }
                    />
                  )}
                  <TextAreaField
                    label={`${labelPrefix} Other Findings`}
                    value={readString(current, "notes")}
                    onChange={(value) =>
                      updateStructure(eye.key, structure.key, {
                        ...current,
                        normal: value ? false : readBoolean(current, "normal"),
                        notes: value
                      })
                    }
                  />
                </div>
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}

function ReferralForm({ payload, updateField }: { payload: SectionPayload; updateField: (key: string, value: unknown) => void }) {
  const referralRequired = readBoolean(payload, "referral_required");
  return (
    <div className="space-y-4">
      <CheckboxField
        label="Referral required"
        checked={referralRequired}
        onChange={(checked) => updateField("referral_required", checked)}
      />
      {referralRequired && (
        <div className="grid gap-4 md:grid-cols-2">
          <ClinicalSelect
            label="Specialist Type"
            value={readString(payload, "specialist_type")}
            options={REFERRAL_SPECIALIST_OPTIONS}
            onChange={(value) => updateField("specialist_type", value)}
          />
          <ClinicalSelect
            label="Referral Status"
            value={readString(payload, "referral_status")}
            options={REFERRAL_STATUS_OPTIONS}
            onChange={(value) => updateField("referral_status", value)}
          />
          <div className="md:col-span-2">
            <TextAreaField label="Referral Notes" value={readString(payload, "notes")} onChange={(value) => updateField("notes", value)} />
          </div>
          <div className="md:col-span-2">
            <TextAreaField
              label="Follow-up Information"
              value={readString(payload, "follow_up")}
              onChange={(value) => updateField("follow_up", value)}
            />
          </div>
        </div>
      )}
    </div>
  );
}

function PreviousValuesPanel({ items, isLoading }: { items: VisitExamSectionHistoryItem[]; isLoading: boolean }) {
  if (isLoading) {
    return (
      <div className="rounded-xl border border-slate-600/45 bg-matte-800/70 p-4 text-sm text-slate-300">
        Loading previous visit values...
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="rounded-xl border border-slate-600/45 bg-matte-800/70 p-4 text-sm text-slate-300">
        No previous visit values for this section.
      </div>
    );
  }

  return (
    <div data-testid="previous-values-panel" className="space-y-3 rounded-xl border border-indigo-300/25 bg-indigo-400/10 p-4">
      <div>
        <h4 className="text-sm font-semibold uppercase tracking-wide text-indigo-100">Previous Visit Values</h4>
        <p className="mt-1 text-xs text-indigo-100/75">Review only. Values are not copied into this visit.</p>
      </div>
      <div className="grid gap-3 lg:grid-cols-2">
        {items.slice(0, 4).map((item) => (
          <article key={`${item.visit_id}-${item.section_key}-${item.saved_at ?? ""}`} className="rounded-lg border border-indigo-200/20 bg-matte-900/75 p-3">
            <p className="text-xs uppercase tracking-wide text-slate-400">{new Date(item.visit_date).toLocaleDateString()}</p>
            <p className="mt-1 text-sm font-medium text-slate-100">{item.title}</p>
            <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap rounded-md bg-matte-950/75 p-2 text-xs text-slate-200">
              {JSON.stringify(item.payload, null, 2)}
            </pre>
          </article>
        ))}
      </div>
    </div>
  );
}

function ReadOnlyFact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-pink-300/20 bg-matte-800/70 p-4">
      <p className="text-xs uppercase tracking-wide text-slate-400">{label}</p>
      <p className="mt-2 text-sm text-slate-100">{value}</p>
    </div>
  );
}

function TextField({
  label,
  value,
  type = "text",
  onChange
}: {
  label: string;
  value: string;
  type?: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block text-sm text-slate-200">
      <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-400">{label}</span>
      <input type={type} value={value} onChange={(event) => onChange(event.target.value)} className={textInputClass()} />
    </label>
  );
}

function TextAreaField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="block text-sm text-slate-200">
      <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-400">{label}</span>
      <textarea rows={4} value={value} onChange={(event) => onChange(event.target.value)} className={textAreaClass()} />
    </label>
  );
}

function CheckboxField({ label, checked, onChange }: { label: string; checked: boolean; onChange: (checked: boolean) => void }) {
  return (
    <label className="flex items-center gap-2 text-sm text-slate-200">
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
      {label}
    </label>
  );
}
