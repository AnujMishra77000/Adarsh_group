import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, FileDown, Receipt, RefreshCw, Save, Send } from "lucide-react";
import { Link } from "react-router-dom";

import {
  changeDispensingOrderStatus,
  downloadDispensingOrderVendorDocument,
  generateDispensingOrderVendorDocument,
  getDispensingOrderContext,
  getVisitBillingContext,
  relinkDispensingOrderPrescription,
  saveDispensingOrder,
  sendDispensingOrderToVendor
} from "@/features/visits/api";
import { listVendors } from "@/features/vendors/api";
import { getErrorMessage } from "@/lib/errors";
import { CRM_PATHS } from "@/lib/routes";
import type {
  DispensingMeasurements,
  DispensingOrderPayload,
  DispensingOrderStatus,
  FrameSelection,
  LensSpecification,
  Visit
} from "@/types/visit";

type Props = {
  visit: Visit;
  mode: "frame" | "lens";
  onDirtyChange: (dirty: boolean) => void;
};

const EMPTY_ORDER: DispensingOrderPayload = {
  frame: {},
  measurements: {},
  lens: {},
  vendor_id: null,
  manufacturing_instructions: null,
  expected_delivery_date: null
};

const LENS_TYPES = [
  ["single_vision", "Single vision"],
  ["bifocal", "Bifocal"],
  ["progressive", "Progressive"],
  ["office_lens", "Office lens"],
  ["occupational_lens", "Occupational lens"],
  ["sunglass_lens", "Sunglass lens"]
] as const;

const STATUS_NEXT: Partial<Record<DispensingOrderStatus, { status: DispensingOrderStatus; label: string }>> = {
  sent_to_vendor: { status: "in_production", label: "Mark In Production" },
  in_production: { status: "ready_for_delivery", label: "Mark Ready for Delivery" },
  ready_for_delivery: { status: "delivered", label: "Mark Delivered" }
};

function inputClass() {
  return "h-10 w-full rounded-lg border border-pink-300/25 bg-matte-900 px-3 text-sm text-slate-100 outline-none focus:border-pink-200 disabled:opacity-60";
}

function statusLabel(value: string): string {
  return value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function DispensingOrderWorkspace({ visit, mode, onDirtyChange }: Props) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<DispensingOrderPayload>(EMPTY_ORDER);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [statusNotes, setStatusNotes] = useState("");

  const contextQuery = useQuery({
    queryKey: ["visits", visit.id, "dispensing-order"],
    queryFn: () => getDispensingOrderContext(visit.id)
  });
  const vendorsQuery = useQuery({
    queryKey: ["vendors", "dispensing-order"],
    queryFn: () => listVendors({ page: 1, page_size: 100, is_active: true })
  });
  const billingQuery = useQuery({
    queryKey: ["visits", visit.id, "billing"],
    queryFn: () => getVisitBillingContext(visit.id),
    enabled: Boolean(contextQuery.data?.order)
  });

  const context = contextQuery.data;
  const order = context?.order ?? null;
  const canEdit = !order || order.status === "draft" || order.status === "ready_for_vendor";

  useEffect(() => {
    if (!context) return;
    setForm(
      context.order
        ? {
            frame: context.order.frame,
            measurements: context.order.measurements,
            lens: context.order.lens,
            vendor_id: context.order.vendor_id,
            manufacturing_instructions: context.order.manufacturing_instructions,
            expected_delivery_date: context.order.expected_delivery_date
          }
        : EMPTY_ORDER
    );
  }, [context]);

  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["visits", visit.id, "dispensing-order"] }),
      queryClient.invalidateQueries({ queryKey: ["visits", visit.id, "exam-sections"] }),
      queryClient.invalidateQueries({ queryKey: ["visits", visit.id, "billing"] })
    ]);
  };

  const succeed = async (nextMessage: string) => {
    setMessage(nextMessage);
    setError(null);
    onDirtyChange(false);
    await refresh();
  };

  const saveMutation = useMutation({
    mutationFn: () => saveDispensingOrder(visit.id, form),
    onSuccess: () => succeed("Spectacle order saved"),
    onError: (value) => setError(getErrorMessage(value))
  });
  const relinkMutation = useMutation({
    mutationFn: () => relinkDispensingOrderPrescription(visit.id),
    onSuccess: () => succeed("Order relinked to the current prescription"),
    onError: (value) => setError(getErrorMessage(value))
  });
  const statusMutation = useMutation({
    mutationFn: (status: DispensingOrderStatus) => changeDispensingOrderStatus(visit.id, status, statusNotes || null),
    onSuccess: (value) => {
      setStatusNotes("");
      succeed(`Order status changed to ${statusLabel(value.status)}`);
    },
    onError: (value) => setError(getErrorMessage(value))
  });
  const documentMutation = useMutation({
    mutationFn: () => generateDispensingOrderVendorDocument(visit.id),
    onSuccess: () => succeed("Vendor document generated"),
    onError: (value) => setError(getErrorMessage(value))
  });
  const sendMutation = useMutation({
    mutationFn: () => sendDispensingOrderToVendor(visit.id),
    onSuccess: (value) => succeed(value.message),
    onError: (value) => setError(getErrorMessage(value))
  });
  const downloadMutation = useMutation({
    mutationFn: () => downloadDispensingOrderVendorDocument(visit.id),
    onSuccess: (blob) => {
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${order?.order_reference ?? "spectacle-order"}.pdf`;
      anchor.click();
      URL.revokeObjectURL(url);
    },
    onError: (value) => setError(getErrorMessage(value))
  });

  const dirty = () => {
    onDirtyChange(true);
    setMessage(null);
    setError(null);
  };
  const updateFrame = (key: keyof FrameSelection, value: string) => {
    setForm((current) => ({ ...current, frame: { ...current.frame, [key]: value || null } }));
    dirty();
  };
  const updateMeasurement = (key: keyof DispensingMeasurements, value: string) => {
    setForm((current) => ({ ...current, measurements: { ...current.measurements, [key]: value || null } }));
    dirty();
  };
  const updateLens = (key: keyof LensSpecification, value: string) => {
    setForm((current) => ({ ...current, lens: { ...current.lens, [key]: value || null } }));
    dirty();
  };

  if (contextQuery.isLoading) return <p className="text-sm text-slate-300">Loading spectacle order...</p>;
  if (contextQuery.isError) return <p className="text-sm text-rose-200">{getErrorMessage(contextQuery.error)}</p>;

  if (!context?.current_prescription_id) {
    return (
      <div className="border-l-2 border-amber-300 bg-amber-400/10 p-4 text-sm text-amber-100">
        Finalize the visit prescription before creating a spectacle order.
      </div>
    );
  }

  const nextStatus = order ? STATUS_NEXT[order.status] : undefined;
  const vendorSelected = form.vendor_id !== null;
  const lensTypeSelected = Boolean(form.lens.lens_type);
  const returnTo = `${CRM_PATHS.visitWorkspace}/${visit.id}`;
  const billingPath = billingQuery.data?.order_bill
    ? `${CRM_PATHS.billing}/view/${billingQuery.data.order_bill.id}?${new URLSearchParams({ return_to: returnTo }).toString()}`
    : `${CRM_PATHS.billing}?${new URLSearchParams({
        customer_id: String(visit.customer_id),
        customer_query: visit.customer_business_id ?? "",
        visit_id: String(visit.id),
        ...(order ? { dispensing_order_id: String(order.id) } : {}),
        return_to: returnTo
      }).toString()}`;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-700/60 pb-4">
        <span className="rounded-md border border-indigo-300/30 bg-indigo-400/10 px-2.5 py-1 text-xs font-semibold text-indigo-100">
          Prescription version {order?.prescription_version_number ?? context.current_prescription_version_number}
        </span>
        {order && (
          <>
            <span className="rounded-md border border-slate-500/50 px-2.5 py-1 text-xs font-semibold text-slate-200">
              {order.order_reference}
            </span>
            <span className={`rounded-md border px-2.5 py-1 text-xs font-semibold ${order.status === "cancelled" ? "border-rose-300/40 bg-rose-400/10 text-rose-100" : order.is_delayed ? "border-amber-300/40 bg-amber-400/10 text-amber-100" : "border-emerald-300/30 bg-emerald-400/10 text-emerald-100"}`}>
              {statusLabel(order.status)}
            </span>
            {order.is_delayed && <span className="text-xs font-semibold text-amber-200">Delayed</span>}
          </>
        )}
      </div>

      {context.is_prescription_stale && order && (
        <div className="border-l-2 border-amber-300 bg-amber-400/10 p-3 text-sm text-amber-100">
          <p className="flex items-center gap-2 font-semibold"><AlertTriangle size={16} /> This order uses an older prescription version.</p>
          <p className="mt-1 text-amber-100/85">Review the amendment, then relink explicitly before generating or sending vendor documents.</p>
          <button
            type="button"
            onClick={() => relinkMutation.mutate()}
            disabled={!canEdit || relinkMutation.isPending}
            className="mt-3 inline-flex items-center gap-2 rounded-lg border border-amber-200/40 px-3 py-2 font-semibold disabled:opacity-50"
          >
            <RefreshCw size={15} /> Relink to version {context.current_prescription_version_number}
          </button>
        </div>
      )}

      {mode === "frame" ? (
        <>
          <FieldGroup title="Frame Selection">
            <TextField label="Frame Brand" value={form.frame.brand} disabled={!canEdit} onChange={(value) => updateFrame("brand", value)} />
            <TextField label="Model Number" value={form.frame.model_number} disabled={!canEdit} onChange={(value) => updateFrame("model_number", value)} />
            <TextField label="Colour Code" value={form.frame.colour_code} disabled={!canEdit} onChange={(value) => updateFrame("colour_code", value)} />
            <TextField label="Frame Type" value={form.frame.frame_type} disabled={!canEdit} onChange={(value) => updateFrame("frame_type", value)} />
            <TextField label="Barcode" value={form.frame.barcode} disabled={!canEdit} onChange={(value) => updateFrame("barcode", value)} />
            <TextField label="A Size (mm)" type="number" value={form.frame.a_size_mm} disabled={!canEdit} onChange={(value) => updateFrame("a_size_mm", value)} />
            <TextField label="B Size (mm)" type="number" value={form.frame.b_size_mm} disabled={!canEdit} onChange={(value) => updateFrame("b_size_mm", value)} />
            <TextField label="DBL (mm)" type="number" value={form.frame.dbl_mm} disabled={!canEdit} onChange={(value) => updateFrame("dbl_mm", value)} />
            <TextField label="Temple Length (mm)" type="number" value={form.frame.temple_length_mm} disabled={!canEdit} onChange={(value) => updateFrame("temple_length_mm", value)} />
            <TextField label="Effective Diameter (mm)" type="number" value={form.frame.effective_diameter_mm} disabled={!canEdit} onChange={(value) => updateFrame("effective_diameter_mm", value)} />
          </FieldGroup>
          <FieldGroup title="Dispensing Measurements">
            <TextField label="Right Monocular PD (mm)" type="number" value={form.measurements.right_monocular_pd_mm} disabled={!canEdit} onChange={(value) => updateMeasurement("right_monocular_pd_mm", value)} />
            <TextField label="Left Monocular PD (mm)" type="number" value={form.measurements.left_monocular_pd_mm} disabled={!canEdit} onChange={(value) => updateMeasurement("left_monocular_pd_mm", value)} />
            <TextField label="Total PD (mm)" type="number" value={form.measurements.total_pd_mm} disabled={!canEdit} onChange={(value) => updateMeasurement("total_pd_mm", value)} />
            <TextField label="Right Fitting Height (mm)" type="number" value={form.measurements.right_fitting_height_mm} disabled={!canEdit} onChange={(value) => updateMeasurement("right_fitting_height_mm", value)} />
            <TextField label="Left Fitting Height (mm)" type="number" value={form.measurements.left_fitting_height_mm} disabled={!canEdit} onChange={(value) => updateMeasurement("left_fitting_height_mm", value)} />
            <TextField label="Right Segment Height (mm)" type="number" value={form.measurements.right_segment_height_mm} disabled={!canEdit} onChange={(value) => updateMeasurement("right_segment_height_mm", value)} />
            <TextField label="Left Segment Height (mm)" type="number" value={form.measurements.left_segment_height_mm} disabled={!canEdit} onChange={(value) => updateMeasurement("left_segment_height_mm", value)} />
            <TextField label="Pantoscopic Tilt (degrees)" type="number" value={form.measurements.pantoscopic_tilt_degrees} disabled={!canEdit} onChange={(value) => updateMeasurement("pantoscopic_tilt_degrees", value)} />
            <TextField label="Vertex Distance (mm)" type="number" value={form.measurements.vertex_distance_mm} disabled={!canEdit} onChange={(value) => updateMeasurement("vertex_distance_mm", value)} />
            <TextField label="Measured By" value={form.measurements.measured_by} disabled={!canEdit} onChange={(value) => updateMeasurement("measured_by", value)} />
            <TextAreaField label="Measurement Notes" value={form.measurements.measurement_notes} disabled={!canEdit} onChange={(value) => updateMeasurement("measurement_notes", value)} />
          </FieldGroup>
        </>
      ) : (
        <FieldGroup title="Lens Specification">
          <label className="text-sm text-slate-200">
            <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-400">Lens Type</span>
            <select aria-label="Lens Type" value={form.lens.lens_type ?? ""} disabled={!canEdit} onChange={(event) => updateLens("lens_type", event.target.value)} className={inputClass()}>
              <option value="">Select lens type</option>
              {LENS_TYPES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </label>
          <TextField label="Lens Brand" value={form.lens.brand} disabled={!canEdit} onChange={(value) => updateLens("brand", value)} />
          <TextField label="Material" value={form.lens.material} disabled={!canEdit} onChange={(value) => updateLens("material", value)} />
          <TextField label="Index" value={form.lens.index} disabled={!canEdit} onChange={(value) => updateLens("index", value)} />
          <TextField label="Design" value={form.lens.design} disabled={!canEdit} onChange={(value) => updateLens("design", value)} />
          <TextField label="Coating" value={form.lens.coating} disabled={!canEdit} onChange={(value) => updateLens("coating", value)} />
          <TextField label="Tint or Photochromic Option" value={form.lens.tint_or_photochromic} disabled={!canEdit} onChange={(value) => updateLens("tint_or_photochromic", value)} />
          <label className="text-sm text-slate-200">
            <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-400">Vendor</span>
            <select
              aria-label="Vendor"
              value={form.vendor_id ?? ""}
              disabled={!canEdit || vendorsQuery.isLoading}
              onChange={(event) => {
                setForm((current) => ({ ...current, vendor_id: event.target.value ? Number(event.target.value) : null }));
                dirty();
              }}
              className={inputClass()}
            >
              <option value="">Select vendor</option>
              {(vendorsQuery.data?.items ?? []).map((vendor) => <option key={vendor.id} value={vendor.id}>{vendor.vendor_name}</option>)}
            </select>
          </label>
          <TextAreaField
            label="Manufacturing Instructions"
            value={form.manufacturing_instructions}
            disabled={!canEdit}
            onChange={(value) => {
              setForm((current) => ({ ...current, manufacturing_instructions: value || null }));
              dirty();
            }}
          />
          <label className="text-sm text-slate-200">
            <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-400">Expected Delivery Date</span>
            <input
              aria-label="Expected Delivery Date"
              type="date"
              value={form.expected_delivery_date ?? ""}
              disabled={!canEdit}
              onChange={(event) => {
                setForm((current) => ({ ...current, expected_delivery_date: event.target.value || null }));
                dirty();
              }}
              className={inputClass()}
            />
          </label>
        </FieldGroup>
      )}

      {error && <p className="rounded-lg border border-rose-300/25 bg-rose-400/10 p-3 text-sm text-rose-100">{error}</p>}
      {message && <p className="text-sm font-medium text-emerald-200">{message}</p>}

      <div className="flex flex-wrap gap-2 border-t border-slate-700/60 pt-4">
        {order && (
          <Link
            to={billingPath}
            className="inline-flex items-center gap-2 rounded-lg border border-emerald-300/35 bg-emerald-400/10 px-3 py-2 text-sm font-semibold text-emerald-100"
          >
            <Receipt size={16} /> {billingQuery.data?.order_bill ? "Open Bill" : "Create Bill"}
          </Link>
        )}
        {canEdit && (
          <button type="button" onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending} className="inline-flex items-center gap-2 rounded-lg bg-pink-500 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50">
            <Save size={16} /> {saveMutation.isPending ? "Saving..." : "Save Spectacle Order"}
          </button>
        )}
        {order?.status === "draft" && (
          <button type="button" onClick={() => statusMutation.mutate("ready_for_vendor")} disabled={context.is_prescription_stale || !lensTypeSelected} className="rounded-lg border border-emerald-300/35 bg-emerald-400/10 px-3 py-2 text-sm font-semibold text-emerald-100 disabled:opacity-45">Mark Ready for Vendor</button>
        )}
        {order?.status === "ready_for_vendor" && (
          <button type="button" onClick={() => statusMutation.mutate("draft")} className="rounded-lg border border-slate-500/50 px-3 py-2 text-sm font-semibold text-slate-200">Return to Draft</button>
        )}
        {order && (
          <button type="button" onClick={() => documentMutation.mutate()} disabled={context.is_prescription_stale || documentMutation.isPending} className="inline-flex items-center gap-2 rounded-lg border border-sky-300/35 bg-sky-400/10 px-3 py-2 text-sm font-semibold text-sky-100 disabled:opacity-45"><FileDown size={16} /> Generate Vendor Document</button>
        )}
        {order?.has_vendor_document && (
          <button type="button" onClick={() => downloadMutation.mutate()} className="rounded-lg px-3 py-2 text-sm font-semibold text-sky-200 underline">Download Vendor Document</button>
        )}
        <button
          type="button"
          onClick={() => sendMutation.mutate()}
          disabled={!order || order.status !== "ready_for_vendor" || context.is_prescription_stale || !vendorSelected || !lensTypeSelected || sendMutation.isPending}
          className="inline-flex items-center gap-2 rounded-lg border border-indigo-300/35 bg-indigo-400/10 px-3 py-2 text-sm font-semibold text-indigo-100 disabled:opacity-45"
        >
          <Send size={16} /> Send to Vendor
        </button>
        {nextStatus && (
          <button type="button" onClick={() => statusMutation.mutate(nextStatus.status)} className="rounded-lg border border-emerald-300/35 px-3 py-2 text-sm font-semibold text-emerald-100">{nextStatus.label}</button>
        )}
        {order && !["delivered", "cancelled"].includes(order.status) && (
          <button type="button" onClick={() => statusMutation.mutate("cancelled")} className="rounded-lg border border-rose-300/35 px-3 py-2 text-sm font-semibold text-rose-100">Cancel Order</button>
        )}
      </div>
      {order && !["delivered", "cancelled"].includes(order.status) && (
        <TextAreaField label="Status Change Notes" value={statusNotes} disabled={false} onChange={setStatusNotes} />
      )}
      {order?.delivered_at && (
        <p className="text-sm text-emerald-100">Delivered {new Date(order.delivered_at).toLocaleString()} by user #{order.delivered_by ?? "unknown"}</p>
      )}
      {order && (order.events?.length ?? 0) > 0 && (
        <section className="border-t border-slate-700/60 pt-4">
          <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-300">Order Event History</h4>
          <ul className="mt-3 space-y-2">
            {(order.events ?? []).map((event) => (
              <li key={event.id} className="rounded-lg border border-slate-700/70 bg-matte-900/60 p-3 text-sm text-slate-200">
                <p className="font-semibold text-pink-100">{statusLabel(event.event)}</p>
                <p className="text-xs text-slate-400">{new Date(event.occurred_at).toLocaleString()} · user #{event.user_id ?? "system"}</p>
                {event.previous_status && <p className="text-xs text-slate-400">From {statusLabel(event.previous_status)} to {statusLabel(event.status)}</p>}
                {event.notes && <p className="mt-1">{event.notes}</p>}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function FieldGroup({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h4 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-300">{title}</h4>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{children}</div>
    </section>
  );
}

function TextField({ label, value, type = "text", disabled, onChange }: { label: string; value?: string | null; type?: string; disabled: boolean; onChange: (value: string) => void }) {
  return (
    <label className="text-sm text-slate-200">
      <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-400">{label}</span>
      <input aria-label={label} type={type} step={type === "number" ? "0.01" : undefined} value={value ?? ""} disabled={disabled} onChange={(event) => onChange(event.target.value)} className={inputClass()} />
    </label>
  );
}

function TextAreaField({ label, value, disabled, onChange }: { label: string; value?: string | null; disabled: boolean; onChange: (value: string) => void }) {
  return (
    <label className="text-sm text-slate-200 md:col-span-2 xl:col-span-3">
      <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-400">{label}</span>
      <textarea aria-label={label} value={value ?? ""} disabled={disabled} rows={3} onChange={(event) => onChange(event.target.value)} className="w-full rounded-lg border border-pink-300/25 bg-matte-900 px-3 py-2 text-sm text-slate-100 outline-none focus:border-pink-200 disabled:opacity-60" />
    </label>
  );
}
