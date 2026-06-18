import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, ClipboardCheck, FileDown, GitBranch, LockKeyhole, Save } from "lucide-react";

import {
  completeVisit,
  createVisitPrescriptionAmendment,
  finalizeVisitPrescription,
  generateVisitPrescriptionPdf,
  getVisitPrescriptionReview,
  getVisitPrescriptionSummary,
  saveVisitPrescriptionDraft
} from "@/features/visits/api";
import { getErrorMessage } from "@/lib/errors";
import { ACUITY_OPTIONS, REFRACTION_OPTIONS } from "@/pages/visits/examSections";
import { EyeEntryGrid, type EyeEntryValue } from "@/pages/visits/components/EyeEntryGrid";
import type {
  FinalPrescriptionData,
  PrescriptionEyePair,
  PrescriptionEyeValues,
  Visit,
  VisitPrescription,
  VisitPrescriptionReview
} from "@/types/visit";

type Props = {
  visit: Visit;
  onDirtyChange: (dirty: boolean) => void;
};

const EMPTY_EYE: PrescriptionEyeValues = { sph: null, cyl: null, axis: null, add: null, va: null };
const EMPTY_DATA: FinalPrescriptionData = {
  distance: { right: { ...EMPTY_EYE }, left: { ...EMPTY_EYE } },
  near: { right: { ...EMPTY_EYE }, left: { ...EMPTY_EYE } },
  pd: null,
  fitting_height: null
};

function toGrid(value: PrescriptionEyePair): EyeEntryValue {
  return {
    right: Object.fromEntries(Object.entries(value.right).map(([key, item]) => [key, item ?? ""])),
    left: Object.fromEntries(Object.entries(value.left).map(([key, item]) => [key, item ?? ""]))
  };
}

function fromGrid(value: EyeEntryValue): PrescriptionEyePair {
  const normalize = (eye: "right" | "left"): PrescriptionEyeValues => ({
    sph: value[eye]?.sph?.trim() || null,
    cyl: value[eye]?.cyl?.trim() || null,
    axis: value[eye]?.axis?.trim() || null,
    add: value[eye]?.add?.trim() || null,
    va: value[eye]?.va?.trim() || null
  });
  return { right: normalize("right"), left: normalize("left") };
}

function statusLabel(value: string): string {
  return value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function sectionLabel(value: string): string {
  return value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function FinalPrescriptionWorkspace({ visit, onDirtyChange }: Props) {
  const queryClient = useQueryClient();
  const [data, setData] = useState<FinalPrescriptionData>(EMPTY_DATA);
  const [instructions, setInstructions] = useState("");
  const [review, setReview] = useState<VisitPrescriptionReview | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [savedMessage, setSavedMessage] = useState<string | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);

  const summaryQuery = useQuery({
    queryKey: ["visits", visit.id, "prescriptions"],
    queryFn: () => getVisitPrescriptionSummary(visit.id)
  });

  const versions = useMemo(() => summaryQuery.data?.versions ?? [], [summaryQuery.data?.versions]);
  const draft = versions.find((version) => version.status === "draft") ?? null;
  const current = versions.find((version) => version.is_current && version.status === "finalized") ?? null;
  const workingVersion = draft ?? current;
  const isReadOnly = !draft && current !== null;

  useEffect(() => {
    if (!workingVersion) {
      setData(EMPTY_DATA);
      setInstructions("");
      return;
    }
    setData(workingVersion.data);
    setInstructions(workingVersion.patient_instructions ?? "");
  }, [workingVersion]);

  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["visits", visit.id, "prescriptions"] }),
      queryClient.invalidateQueries({ queryKey: ["visits", visit.id, "exam-sections"] }),
      queryClient.invalidateQueries({ queryKey: ["visits", visit.id] }),
      queryClient.invalidateQueries({ queryKey: ["customer-record-detail"] })
    ]);
  };

  const saveMutation = useMutation({
    mutationFn: () =>
      saveVisitPrescriptionDraft(visit.id, {
        data,
        patient_instructions: instructions.trim() || null
      }),
    onSuccess: async () => {
      onDirtyChange(false);
      setSavedMessage("Prescription draft saved");
      setActionError(null);
      await refresh();
    },
    onError: (error) => setActionError(getErrorMessage(error))
  });

  const reviewMutation = useMutation({
    mutationFn: (version: VisitPrescription) => getVisitPrescriptionReview(visit.id, version.id),
    onSuccess: (value) => {
      setReview(value);
      setActionError(null);
    },
    onError: (error) => setActionError(getErrorMessage(error))
  });

  const finalizeMutation = useMutation({
    mutationFn: (version: VisitPrescription) => finalizeVisitPrescription(visit.id, version.id, { confirmed: true }),
    onSuccess: async () => {
      setReview(null);
      setSavedMessage("Prescription finalized");
      setActionError(null);
      await refresh();
    },
    onError: (error) => setActionError(getErrorMessage(error))
  });

  const amendmentMutation = useMutation({
    mutationFn: (version: VisitPrescription) => createVisitPrescriptionAmendment(visit.id, version.id),
    onSuccess: async () => {
      setReview(null);
      setSavedMessage("Amendment draft created");
      setActionError(null);
      await refresh();
    },
    onError: (error) => setActionError(getErrorMessage(error))
  });

  const pdfMutation = useMutation({
    mutationFn: () => generateVisitPrescriptionPdf(visit.id),
    onSuccess: (value) => {
      setPdfUrl(value.pdf_url);
      setActionError(null);
    },
    onError: (error) => setActionError(getErrorMessage(error))
  });

  const completionMutation = useMutation({
    mutationFn: () => completeVisit(visit.id, { confirmed: true }),
    onSuccess: async () => {
      setSavedMessage("Visit completed");
      setActionError(null);
      await refresh();
    },
    onError: (error) => setActionError(getErrorMessage(error))
  });

  const updatePair = (key: "distance" | "near", value: EyeEntryValue) => {
    setData((currentData) => ({ ...currentData, [key]: fromGrid(value) }));
    onDirtyChange(true);
    setSavedMessage(null);
    setReview(null);
  };

  if (summaryQuery.isLoading) {
    return <p className="text-sm text-slate-300">Loading prescription versions...</p>;
  }

  if (summaryQuery.isError) {
    return <p className="text-sm text-rose-200">{getErrorMessage(summaryQuery.error)}</p>;
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-2">
        {draft && (
          <span className="rounded-md border border-amber-300/30 bg-amber-400/10 px-2.5 py-1 text-xs font-semibold text-amber-100">
            Draft version {draft.version_number}
          </span>
        )}
        {current && (
          <span className="inline-flex items-center gap-1.5 rounded-md border border-emerald-300/30 bg-emerald-400/10 px-2.5 py-1 text-xs font-semibold text-emerald-100">
            <LockKeyhole size={13} /> Current version
          </span>
        )}
        {!workingVersion && <span className="text-sm text-slate-400">No prescription draft saved yet.</span>}
      </div>

      <EyeEntryGrid
        title="Distance Prescription"
        value={toGrid(data.distance)}
        fields={[
          { key: "sph", label: "Sphere", options: REFRACTION_OPTIONS },
          { key: "cyl", label: "Cylinder", options: REFRACTION_OPTIONS },
          { key: "axis", label: "Axis" },
          { key: "va", label: "Visual Acuity", options: ACUITY_OPTIONS }
        ]}
        disabled={isReadOnly}
        onChange={(value) => updatePair("distance", value)}
      />

      <EyeEntryGrid
        title="Near Prescription"
        value={toGrid(data.near)}
        fields={[
          { key: "sph", label: "Sphere", options: REFRACTION_OPTIONS },
          { key: "cyl", label: "Cylinder", options: REFRACTION_OPTIONS },
          { key: "axis", label: "Axis" },
          { key: "add", label: "Add", options: REFRACTION_OPTIONS },
          { key: "va", label: "Visual Acuity", options: ACUITY_OPTIONS }
        ]}
        disabled={isReadOnly}
        onChange={(value) => updatePair("near", value)}
      />

      <div className="grid gap-4 md:grid-cols-2">
        <label className="text-sm text-slate-200">
          <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-400">PD</span>
          <input
            aria-label="PD"
            disabled={isReadOnly}
            value={data.pd ?? ""}
            onChange={(event) => {
              setData((currentData) => ({ ...currentData, pd: event.target.value || null }));
              onDirtyChange(true);
            }}
            className="h-10 w-full rounded-lg border border-pink-300/25 bg-matte-900 px-3 text-sm text-slate-100 outline-none disabled:opacity-65"
          />
        </label>
        <label className="text-sm text-slate-200">
          <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-400">Fitting Height</span>
          <input
            aria-label="Fitting Height"
            disabled={isReadOnly}
            value={data.fitting_height ?? ""}
            onChange={(event) => {
              setData((currentData) => ({ ...currentData, fitting_height: event.target.value || null }));
              onDirtyChange(true);
            }}
            className="h-10 w-full rounded-lg border border-pink-300/25 bg-matte-900 px-3 text-sm text-slate-100 outline-none disabled:opacity-65"
          />
        </label>
      </div>

      <label className="block text-sm text-slate-200">
        <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-400">Patient Instructions</span>
        <textarea
          aria-label="Patient Instructions"
          disabled={isReadOnly}
          value={instructions}
          onChange={(event) => {
            setInstructions(event.target.value);
            onDirtyChange(true);
            setSavedMessage(null);
          }}
          rows={3}
          className="w-full rounded-lg border border-pink-300/25 bg-matte-900 px-3 py-2 text-sm text-slate-100 outline-none disabled:opacity-65"
        />
      </label>

      {actionError && <p className="rounded-lg border border-rose-300/25 bg-rose-400/10 p-3 text-sm text-rose-100">{actionError}</p>}
      {savedMessage && <p className="text-sm font-medium text-emerald-200">{savedMessage}</p>}

      <div className="flex flex-wrap gap-2 border-t border-slate-700/60 pt-4">
        {!isReadOnly && (
          <button
            type="button"
            onClick={() => saveMutation.mutate()}
            disabled={saveMutation.isPending}
            className="inline-flex items-center gap-2 rounded-lg bg-pink-500 px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"
          >
            <Save size={16} /> {saveMutation.isPending ? "Saving..." : "Save Prescription Draft"}
          </button>
        )}
        {draft && (
          <button
            type="button"
            onClick={() => reviewMutation.mutate(draft)}
            disabled={reviewMutation.isPending}
            className="inline-flex items-center gap-2 rounded-lg border border-indigo-300/35 bg-indigo-400/10 px-3 py-2 text-sm font-semibold text-indigo-100"
          >
            <ClipboardCheck size={16} /> Review Prescription
          </button>
        )}
        {isReadOnly && current && (
          <>
            <button
              type="button"
              onClick={() => amendmentMutation.mutate(current)}
              disabled={amendmentMutation.isPending}
              className="inline-flex items-center gap-2 rounded-lg border border-amber-300/35 bg-amber-400/10 px-3 py-2 text-sm font-semibold text-amber-100"
            >
              <GitBranch size={16} /> Start Amendment
            </button>
            <button
              type="button"
              onClick={() => pdfMutation.mutate()}
              disabled={pdfMutation.isPending}
              className="inline-flex items-center gap-2 rounded-lg border border-sky-300/35 bg-sky-400/10 px-3 py-2 text-sm font-semibold text-sky-100"
            >
              <FileDown size={16} /> Generate Patient PDF
            </button>
            {visit.status !== "completed" && (
              <button
                type="button"
                onClick={() => {
                  if (window.confirm("Complete this visit? Examination sections will become read-only.")) {
                    completionMutation.mutate();
                  }
                }}
                disabled={completionMutation.isPending}
                className="inline-flex items-center gap-2 rounded-lg border border-emerald-300/35 bg-emerald-400/10 px-3 py-2 text-sm font-semibold text-emerald-100"
              >
                <CheckCircle2 size={16} /> Complete Visit
              </button>
            )}
          </>
        )}
        {pdfUrl && (
          <a className="inline-flex items-center rounded-lg px-3 py-2 text-sm font-semibold text-sky-200 underline" href={pdfUrl}>
            Download current PDF
          </a>
        )}
      </div>

      {review && (
        <section className="space-y-4 border-t border-pink-300/20 pt-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-pink-200/80">Before finalization</p>
            <h4 className="mt-1 text-lg font-semibold text-slate-100">Finalization Review</h4>
          </div>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <ReviewFact label="Patient" value={`${review.patient.name} (${review.patient.business_id})`} />
            <ReviewFact label="Visit" value={new Date(review.visit.visit_date).toLocaleDateString()} />
            <ReviewFact label="Branch" value={review.visit.branch_name} />
            <ReviewFact label="Examiner" value={review.examiner.name} />
          </div>
          <ReviewedPrescriptionValues data={review.prescription.data} />
          {review.warnings.length > 0 && (
            <div className="border-l-2 border-amber-300 bg-amber-400/10 p-3 text-sm text-amber-100">
              <p className="mb-2 flex items-center gap-2 font-semibold"><AlertTriangle size={16} /> Important incomplete data</p>
              <ul className="space-y-1">
                {review.warnings.map((warning) => <li key={warning}>{warning}</li>)}
              </ul>
            </div>
          )}
          <div>
            <h5 className="text-sm font-semibold text-slate-100">Core examination summary</h5>
            <div className="mt-2 flex flex-wrap gap-2">
              {Object.entries(review.core_examination_summary).map(([key, value]) => (
                <span key={key} className="rounded-md border border-slate-600/70 px-2 py-1 text-xs text-slate-200">
                  {sectionLabel(key)}: {statusLabel(value.state)}
                </span>
              ))}
            </div>
          </div>
          {review.referral_summary && (
            <ReviewFact
              label="Referral"
              value={`${String(review.referral_summary.specialist_type ?? "Specialist")} · ${String(review.referral_summary.referral_status ?? "Pending")}`}
            />
          )}
          <ReviewFact label="Patient instructions" value={review.patient_instructions || "None recorded"} />
          <button
            type="button"
            onClick={() => {
              if (window.confirm("Finalize this prescription? It cannot be edited; corrections require an amendment.")) {
                finalizeMutation.mutate(review.prescription);
              }
            }}
            disabled={finalizeMutation.isPending}
            className="inline-flex items-center gap-2 rounded-lg bg-emerald-500 px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"
          >
            <LockKeyhole size={16} /> Finalize Prescription
          </button>
        </section>
      )}

      {versions.length > 0 && (
        <section className="border-t border-slate-700/60 pt-4">
          <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-300">Version History</h4>
          <div className="mt-2 space-y-2">
            {versions.map((version) => (
              <div key={version.id} className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-700/55 py-2 text-sm">
                <span className="font-medium text-slate-100">Version {version.version_number}</span>
                <span className="text-slate-300">{statusLabel(version.status)}{version.is_current ? " · Current" : ""}</span>
                <span className="text-xs text-slate-500">{new Date(version.updated_at).toLocaleString()}</span>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function ReviewFact({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-l-2 border-pink-300/35 pl-3">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-400">{label}</p>
      <p className="mt-1 text-sm text-slate-100">{value}</p>
    </div>
  );
}

function ReviewedPrescriptionValues({ data }: { data: FinalPrescriptionData }) {
  const value = (item: string | null) => item || "-";
  return (
    <div className="overflow-x-auto">
      <h5 className="mb-2 text-sm font-semibold text-slate-100">Reviewed Prescription Values</h5>
      <table className="w-full min-w-[680px] text-left text-sm">
        <thead className="border-b border-slate-600 text-xs uppercase text-slate-400">
          <tr>
            <th className="py-2 pr-3">Range</th>
            <th className="py-2 pr-3">Eye</th>
            <th className="py-2 pr-3">Sphere</th>
            <th className="py-2 pr-3">Cylinder</th>
            <th className="py-2 pr-3">Axis</th>
            <th className="py-2 pr-3">Add</th>
            <th className="py-2 pr-3">VA</th>
          </tr>
        </thead>
        <tbody>
          {(["distance", "near"] as const).flatMap((range) =>
            (["right", "left"] as const).map((eye) => {
              const values = data[range][eye];
              return (
                <tr key={`${range}-${eye}`} className="border-b border-slate-700/55">
                  <td className="py-2 pr-3 font-medium text-slate-200">{sectionLabel(range)}</td>
                  <td className="py-2 pr-3 text-slate-200">{sectionLabel(eye)}</td>
                  <td className="py-2 pr-3 text-slate-300">{value(values.sph)}</td>
                  <td className="py-2 pr-3 text-slate-300">{value(values.cyl)}</td>
                  <td className="py-2 pr-3 text-slate-300">{value(values.axis)}</td>
                  <td className="py-2 pr-3 text-slate-300">{range === "near" ? value(values.add) : "-"}</td>
                  <td className="py-2 pr-3 text-slate-300">{value(values.va)}</td>
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}
