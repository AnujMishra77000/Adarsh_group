import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import {
  changeContactLensFollowUpStatus,
  changeContactLensOrderStatus,
  getContactLensContext,
  saveContactLensOrder,
  saveContactLensWorkup,
  scheduleContactLensFollowUp
} from "@/features/visits/api";
import { listVendors } from "@/features/vendors/api";
import { getErrorMessage } from "@/lib/errors";
import { CRM_PATHS } from "@/lib/routes";
import type {
  ContactLensEyeAssessment,
  ContactLensEyePrescription,
  ContactLensWorkupPayload,
  DispensingOrderStatus,
  FollowUpInterval,
  FollowUpStatus,
  Visit
} from "@/types/visit";

type Tab = "workup" | "prescription" | "training" | "order" | "followup";
type SaveState = "idle" | "dirty" | "saving" | "saved" | "failed";

const TABS: Array<{ key: Tab; label: string }> = [
  { key: "workup", label: "Work-up" },
  { key: "prescription", label: "Prescription" },
  { key: "training", label: "Trial & Training" },
  { key: "order", label: "Order" },
  { key: "followup", label: "Follow-up" }
];

const EMPTY_WORKUP: ContactLensWorkupPayload = {
  state: "incomplete",
  indication: { type: null, other: null },
  assessment: { right: {}, left: {}, clinical_notes: null },
  prescription: { right: {}, left: {} },
  lens_details: {},
  trial_training: { trial_lens_dispensed: false, training_status: null, notes: null }
};

const ORDER_NEXT: Partial<Record<DispensingOrderStatus, DispensingOrderStatus>> = {
  draft: "ready_for_vendor",
  ready_for_vendor: "sent_to_vendor",
  sent_to_vendor: "in_production",
  in_production: "ready_for_delivery",
  ready_for_delivery: "delivered"
};

function inputClass() {
  return "h-10 w-full rounded-lg border border-pink-300/25 bg-matte-900 px-3 text-sm text-slate-100 outline-none focus:border-pink-200 disabled:opacity-60";
}

function statusLabel(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function ContactLensWorkspace({ visit, onDirtyChange }: { visit: Visit; onDirtyChange: (dirty: boolean) => void }) {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<Tab>("workup");
  const [form, setForm] = useState<ContactLensWorkupPayload>(EMPTY_WORKUP);
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [vendorId, setVendorId] = useState<number | null>(null);
  const [orderNotes, setOrderNotes] = useState("");
  const [expectedDeliveryDate, setExpectedDeliveryDate] = useState("");
  const [statusNotes, setStatusNotes] = useState("");
  const [followUpInterval, setFollowUpInterval] = useState<FollowUpInterval>("one_week");
  const [followUpDate, setFollowUpDate] = useState("");
  const [followUpNotes, setFollowUpNotes] = useState("");

  const contextQuery = useQuery({
    queryKey: ["visits", visit.id, "contact-lens"],
    queryFn: () => getContactLensContext(visit.id)
  });
  const vendorsQuery = useQuery({
    queryKey: ["vendors", "contact-lens-order"],
    queryFn: () => listVendors({ page: 1, page_size: 100, is_active: true }),
    enabled: tab === "order"
  });
  const context = contextQuery.data;

  useEffect(() => {
    if (!context || saveState === "dirty" || saveState === "failed") return;
    if (context.workup) {
      const { saved_at: _savedAt, saved_by: _savedBy, ...workup } = context.workup;
      setForm(workup);
    }
    setVendorId(context.order?.vendor_id ?? null);
    setOrderNotes(context.order?.order_notes ?? "");
    setExpectedDeliveryDate(context.order?.expected_delivery_date ?? "");
    setFollowUpInterval(context.follow_up?.interval ?? "one_week");
    setFollowUpDate(context.follow_up?.due_date ?? "");
    setFollowUpNotes(context.follow_up?.notes ?? "");
  }, [context, saveState]);

  const dirty = saveState === "dirty" || saveState === "failed";
  useEffect(() => onDirtyChange(dirty), [dirty, onDirtyChange]);
  useEffect(() => () => onDirtyChange(false), [onDirtyChange]);

  const markDirty = (next: ContactLensWorkupPayload) => {
    setForm(next);
    setSaveState("dirty");
    setError(null);
  };
  const setAssessment = (eye: "right" | "left", key: keyof ContactLensEyeAssessment, value: string) =>
    markDirty({ ...form, assessment: { ...form.assessment, [eye]: { ...form.assessment[eye], [key]: value || null } } });
  const setPrescription = (eye: "right" | "left", key: keyof ContactLensEyePrescription, value: string) =>
    markDirty({ ...form, prescription: { ...form.prescription, [eye]: { ...form.prescription[eye], [key]: value || null } } });

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ["visits", visit.id, "contact-lens"] });
    queryClient.invalidateQueries({ queryKey: ["visits", visit.id, "billing"] });
    queryClient.invalidateQueries({ queryKey: ["customer-record-detail"] });
  };
  const workupMutation = useMutation({
    mutationFn: () => saveContactLensWorkup(visit.id, form),
    onMutate: () => { setSaveState("saving"); setError(null); },
    onSuccess: () => { setSaveState("saved"); refresh(); },
    onError: (reason) => { setSaveState("failed"); setError(getErrorMessage(reason)); }
  });
  const orderMutation = useMutation({
    mutationFn: () => saveContactLensOrder(visit.id, {
      vendor_id: vendorId,
      lens_details: form.lens_details,
      order_notes: orderNotes || null,
      expected_delivery_date: expectedDeliveryDate || null
    }),
    onSuccess: refresh,
    onError: (reason) => setError(getErrorMessage(reason))
  });
  const orderStatusMutation = useMutation({
    mutationFn: (status: DispensingOrderStatus) => changeContactLensOrderStatus(visit.id, status, statusNotes || null),
    onSuccess: () => { setStatusNotes(""); refresh(); },
    onError: (reason) => setError(getErrorMessage(reason))
  });
  const followUpMutation = useMutation({
    mutationFn: () => scheduleContactLensFollowUp(visit.id, {
      interval: followUpInterval,
      due_date: followUpInterval === "custom" ? followUpDate || null : null,
      notes: followUpNotes || null
    }),
    onSuccess: refresh,
    onError: (reason) => setError(getErrorMessage(reason))
  });
  const followUpStatusMutation = useMutation({
    mutationFn: (status: FollowUpStatus) => changeContactLensFollowUpStatus(visit.id, status),
    onSuccess: refresh,
    onError: (reason) => setError(getErrorMessage(reason))
  });

  const billingUrl = useMemo(() => `${CRM_PATHS.billing}?${new URLSearchParams({
    customer_id: String(visit.customer_id),
    customer_query: visit.customer_business_id ?? "",
    visit_id: String(visit.id),
    contact_lens_order_id: String(context?.order?.id ?? ""),
    return_to: `${CRM_PATHS.visitWorkspace}/${visit.id}`
  }).toString()}`, [context?.order?.id, visit]);

  const selectTab = (next: Tab) => {
    if (dirty && !window.confirm("Leave this Contact Lens tab without saving changes?")) return;
    setTab(next);
  };

  if (contextQuery.isLoading) return <p className="text-sm text-slate-200">Loading Contact Lens workspace...</p>;
  if (contextQuery.isError) return <p className="text-sm text-rose-200">{getErrorMessage(contextQuery.error)}</p>;

  return (
    <div className="space-y-5">
      <div>
        <h3 className="text-lg font-semibold text-slate-100">Contact Lens Workspace</h3>
        <p className="text-sm text-slate-400">Clinical work-up, order, billing, and follow-up for this visit.</p>
      </div>
      <div className="flex flex-wrap gap-2 border-b border-slate-700/70 pb-3">
        {TABS.map((item) => (
          <button key={item.key} type="button" onClick={() => selectTab(item.key)} className={`rounded-lg border px-3 py-2 text-sm font-semibold ${tab === item.key ? "border-pink-300/45 bg-pink-400/10 text-pink-50" : "border-slate-600/60 text-slate-300"}`}>
            {item.label}
          </button>
        ))}
      </div>

      {tab === "workup" && <WorkupTab form={form} markDirty={markDirty} setAssessment={setAssessment} />}
      {tab === "prescription" && <PrescriptionTab form={form} markDirty={markDirty} setPrescription={setPrescription} />}
      {tab === "training" && <TrainingTab form={form} markDirty={markDirty} />}
      {tab === "order" && (
        <div className="space-y-4">
          {context?.order && <p className={`text-sm ${context.order.status === "cancelled" ? "text-rose-200" : context.order.is_delayed ? "text-amber-200" : "text-slate-200"}`}>{context.order.order_reference} · {statusLabel(context.order.status)}{context.order.is_delayed ? " · Delayed" : ""}</p>}
          <label className="block text-sm text-slate-200"><span className="mb-1 block text-xs uppercase text-slate-400">Vendor</span><select aria-label="Contact Lens Vendor" value={vendorId ?? ""} onChange={(event) => setVendorId(event.target.value ? Number(event.target.value) : null)} className={inputClass()}><option value="">Select vendor</option>{(vendorsQuery.data?.items ?? []).map((vendor) => <option key={vendor.id} value={vendor.id}>{vendor.vendor_name}</option>)}</select></label>
          <TextArea label="Order Notes" value={orderNotes} onChange={setOrderNotes} />
          <Field label="Expected Delivery Date" type="date" value={expectedDeliveryDate} onChange={setExpectedDeliveryDate} />
          {context?.order && !["delivered", "cancelled"].includes(context.order.status) && <TextArea label="Status Change Notes" value={statusNotes} onChange={setStatusNotes} />}
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={() => orderMutation.mutate()} className="rounded-lg border border-pink-300/35 px-3 py-2 text-sm font-semibold text-pink-100">{context?.order ? "Update Order" : "Create Order"}</button>
            {context?.order && ORDER_NEXT[context.order.status] && <button type="button" onClick={() => orderStatusMutation.mutate(ORDER_NEXT[context.order!.status]!)} className="rounded-lg border border-emerald-300/35 px-3 py-2 text-sm font-semibold text-emerald-100">Mark {statusLabel(ORDER_NEXT[context.order.status]!)}</button>}
            {context?.order && !["delivered", "cancelled"].includes(context.order.status) && <button type="button" onClick={() => orderStatusMutation.mutate("cancelled")} className="rounded-lg border border-rose-300/35 px-3 py-2 text-sm font-semibold text-rose-100">Cancel Order</button>}
            {context?.order && (context.active_bill_id ? <Link to={`${CRM_PATHS.billing}/view/${context.active_bill_id}?${new URLSearchParams({ return_to: `${CRM_PATHS.visitWorkspace}/${visit.id}` }).toString()}`} className="rounded-lg border border-indigo-300/35 px-3 py-2 text-sm font-semibold text-indigo-100">Open Bill</Link> : <Link to={billingUrl} className="rounded-lg border border-indigo-300/35 px-3 py-2 text-sm font-semibold text-indigo-100">Create Bill</Link>)}
          </div>
          {context?.order?.delivered_at && <p className="text-sm text-emerald-100">Delivered {new Date(context.order.delivered_at).toLocaleString()} by user #{context.order.delivered_by ?? "unknown"}</p>}
          {context?.order && (context.order.events?.length ?? 0) > 0 && <section><h4 className="text-sm font-semibold uppercase tracking-wide text-slate-300">Order Event History</h4><ul className="mt-2 space-y-2">{(context.order.events ?? []).map((event) => <li key={event.id} className="rounded-lg border border-slate-700/70 p-3 text-sm text-slate-200"><p className="font-semibold text-pink-100">{statusLabel(event.event)}</p><p className="text-xs text-slate-400">{new Date(event.occurred_at).toLocaleString()} · user #{event.user_id ?? "system"}</p>{event.notes && <p>{event.notes}</p>}</li>)}</ul></section>}
        </div>
      )}
      {tab === "followup" && (
        <div className="space-y-4">
          <label className="block text-sm text-slate-200"><span className="mb-1 block text-xs uppercase text-slate-400">Follow-up Interval</span><select aria-label="Follow-up Interval" value={followUpInterval} onChange={(event) => setFollowUpInterval(event.target.value as FollowUpInterval)} className={inputClass()}><option value="one_week">One week</option><option value="fifteen_days">Fifteen days</option><option value="one_month">One month</option><option value="custom">Custom date</option></select></label>
          {followUpInterval === "custom" && <Field label="Custom Follow-up Date" type="date" value={followUpDate} onChange={setFollowUpDate} />}
          <TextArea label="Follow-up Notes" value={followUpNotes} onChange={setFollowUpNotes} />
          {context?.follow_up && <p className="text-sm text-slate-200">Due {new Date(`${context.follow_up.due_date}T00:00:00`).toLocaleDateString()} · {statusLabel(context.follow_up.status)}</p>}
          <div className="flex flex-wrap gap-2"><button type="button" onClick={() => followUpMutation.mutate()} disabled={context?.follow_up?.status !== undefined && context.follow_up.status !== "pending"} className="rounded-lg border border-pink-300/35 px-3 py-2 text-sm font-semibold text-pink-100 disabled:opacity-50">Schedule Follow-up</button>{context?.follow_up?.status === "pending" && <><button type="button" onClick={() => followUpStatusMutation.mutate("completed")} className="rounded-lg border border-emerald-300/35 px-3 py-2 text-sm font-semibold text-emerald-100">Complete Follow-up</button><button type="button" onClick={() => followUpStatusMutation.mutate("cancelled")} className="rounded-lg border border-rose-300/35 px-3 py-2 text-sm font-semibold text-rose-100">Cancel Follow-up</button></>}</div>
        </div>
      )}

      {(tab === "workup" || tab === "prescription" || tab === "training") && (
        <div className="flex items-center gap-3 border-t border-slate-700/70 pt-4">
          <button type="button" onClick={() => workupMutation.mutate()} disabled={workupMutation.isPending} className="rounded-lg border border-emerald-300/35 bg-emerald-400/10 px-4 py-2 text-sm font-semibold text-emerald-100 disabled:opacity-50">Save Work-up</button>
          <select aria-label="Contact Lens Work-up State" value={form.state} onChange={(event) => markDirty({ ...form, state: event.target.value as ContactLensWorkupPayload["state"] })} className={`${inputClass()} max-w-[210px]`}><option value="incomplete">Incomplete</option><option value="complete">Complete</option></select>
          <span className="text-xs text-slate-400">{saveState === "saved" ? "Saved" : saveState === "saving" ? "Saving..." : saveState === "failed" ? "Save failed" : saveState === "dirty" ? "Unsaved changes" : ""}</span>
        </div>
      )}
      {error && <p role="alert" className="text-sm text-rose-200">{error}</p>}
    </div>
  );
}

function WorkupTab({ form, markDirty, setAssessment }: { form: ContactLensWorkupPayload; markDirty: (next: ContactLensWorkupPayload) => void; setAssessment: (eye: "right" | "left", key: keyof ContactLensEyeAssessment, value: string) => void }) {
  return <div className="space-y-4"><label className="block text-sm text-slate-200"><span className="mb-1 block text-xs uppercase text-slate-400">Indication</span><select aria-label="Contact Lens Indication" value={form.indication.type ?? ""} onChange={(event) => markDirty({ ...form, indication: { ...form.indication, type: event.target.value as ContactLensWorkupPayload["indication"]["type"] } })} className={inputClass()}><option value="">Select indication</option>{["cosmetic", "refractive", "keratoconus", "sports", "therapeutic", "other"].map((value) => <option key={value} value={value}>{statusLabel(value)}</option>)}</select></label>{form.indication.type === "other" && <Field label="Other Indication" value={form.indication.other ?? ""} onChange={(value) => markDirty({ ...form, indication: { ...form.indication, other: value || null } })} />}<div className="grid gap-4 lg:grid-cols-2">{(["right", "left"] as const).map((eye) => <section key={eye} className="space-y-3 rounded-lg border border-slate-700/70 p-4"><h4 className="font-semibold text-pink-100">{statusLabel(eye)} Eye Assessment</h4><Field label={`${statusLabel(eye)} Eye K Reading`} value={form.assessment[eye].k_reading ?? ""} onChange={(value) => setAssessment(eye, "k_reading", value)} /><Field label={`${statusLabel(eye)} Eye HVID`} value={form.assessment[eye].hvid_mm ?? ""} onChange={(value) => setAssessment(eye, "hvid_mm", value)} /><Field label={`${statusLabel(eye)} Eye Tear Film`} value={form.assessment[eye].tear_film ?? ""} onChange={(value) => setAssessment(eye, "tear_film", value)} /><Field label={`${statusLabel(eye)} Eye TBUT Seconds`} value={form.assessment[eye].tbut_seconds ?? ""} onChange={(value) => setAssessment(eye, "tbut_seconds", value)} /></section>)}</div><TextArea label="Clinical Notes" value={form.assessment.clinical_notes ?? ""} onChange={(value) => markDirty({ ...form, assessment: { ...form.assessment, clinical_notes: value || null } })} /></div>;
}

function PrescriptionTab({ form, markDirty, setPrescription }: { form: ContactLensWorkupPayload; markDirty: (next: ContactLensWorkupPayload) => void; setPrescription: (eye: "right" | "left", key: keyof ContactLensEyePrescription, value: string) => void }) {
  return <div className="space-y-4"><div className="grid gap-4 lg:grid-cols-2">{(["right", "left"] as const).map((eye) => <section key={eye} className="space-y-3 rounded-lg border border-slate-700/70 p-4"><h4 className="font-semibold text-pink-100">{statusLabel(eye)} Eye Prescription</h4><Field label={`${statusLabel(eye)} Eye Power`} value={form.prescription[eye].power ?? ""} onChange={(value) => setPrescription(eye, "power", value)} /><Field label={`${statusLabel(eye)} Eye Base Curve`} value={form.prescription[eye].base_curve_mm ?? ""} onChange={(value) => setPrescription(eye, "base_curve_mm", value)} /><Field label={`${statusLabel(eye)} Eye Diameter`} value={form.prescription[eye].diameter_mm ?? ""} onChange={(value) => setPrescription(eye, "diameter_mm", value)} /></section>)}</div><div className="grid gap-4 md:grid-cols-2"><Field label="Contact Lens Brand" value={form.lens_details.brand ?? ""} onChange={(value) => markDirty({ ...form, lens_details: { ...form.lens_details, brand: value || null } })} /><Field label="Contact Lens Material" value={form.lens_details.material ?? ""} onChange={(value) => markDirty({ ...form, lens_details: { ...form.lens_details, material: value || null } })} /><Field label="Replacement Schedule" value={form.lens_details.replacement_schedule ?? ""} onChange={(value) => markDirty({ ...form, lens_details: { ...form.lens_details, replacement_schedule: value || null } })} /><Field label="Wearing Schedule" value={form.lens_details.wearing_schedule ?? ""} onChange={(value) => markDirty({ ...form, lens_details: { ...form.lens_details, wearing_schedule: value || null } })} /></div></div>;
}

function TrainingTab({ form, markDirty }: { form: ContactLensWorkupPayload; markDirty: (next: ContactLensWorkupPayload) => void }) {
  return <div className="space-y-4"><label className="flex items-center gap-2 text-sm text-slate-200"><input aria-label="Trial Lens Dispensed" type="checkbox" checked={form.trial_training.trial_lens_dispensed} onChange={(event) => markDirty({ ...form, trial_training: { ...form.trial_training, trial_lens_dispensed: event.target.checked } })} /> Trial lens dispensed</label><label className="block text-sm text-slate-200"><span className="mb-1 block text-xs uppercase text-slate-400">Training Status</span><select aria-label="Training Status" value={form.trial_training.training_status ?? ""} onChange={(event) => markDirty({ ...form, trial_training: { ...form.trial_training, training_status: event.target.value || null } })} className={inputClass()}><option value="">Select status</option><option value="not_started">Not started</option><option value="in_progress">In progress</option><option value="completed">Completed</option></select></label><TextArea label="Training Notes" value={form.trial_training.notes ?? ""} onChange={(value) => markDirty({ ...form, trial_training: { ...form.trial_training, notes: value || null } })} /></div>;
}

function Field({ label, value, type = "text", onChange }: { label: string; value: string; type?: string; onChange: (value: string) => void }) {
  return <label className="block text-sm text-slate-200"><span className="mb-1 block text-xs uppercase text-slate-400">{label}</span><input aria-label={label} type={type} value={value} onChange={(event) => onChange(event.target.value)} className={inputClass()} /></label>;
}

function TextArea({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return <label className="block text-sm text-slate-200"><span className="mb-1 block text-xs uppercase text-slate-400">{label}</span><textarea aria-label={label} value={value} rows={3} onChange={(event) => onChange(event.target.value)} className="w-full rounded-lg border border-pink-300/25 bg-matte-900 px-3 py-2 text-sm text-slate-100 outline-none focus:border-pink-200" /></label>;
}
