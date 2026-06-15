import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { z } from "zod";

import { searchCustomers } from "@/features/customers/api";
import { createPrescription } from "@/features/prescriptions/api";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { getErrorMessage } from "@/lib/errors";
import type { PrescriptionPayload } from "@/types/prescription";

const optionalDecimal = z.preprocess(
  (value) => {
    if (value === "" || value === null || value === undefined) {
      return null;
    }
    const numeric = Number(value);
    return Number.isNaN(numeric) ? value : numeric;
  },
  z.number({ invalid_type_error: "Enter a valid number" }).nullable()
);

const optionalAxis = z.preprocess(
  (value) => {
    if (value === "" || value === null || value === undefined) {
      return null;
    }
    const numeric = Number(value);
    return Number.isNaN(numeric) ? value : numeric;
  },
  z
    .number({ invalid_type_error: "Axis must be a number" })
    .int("Axis must be an integer")
    .min(0, "Axis must be between 0 and 180")
    .max(180, "Axis must be between 0 and 180")
    .nullable()
);

const prescriptionFormSchema = z.object({
  customer_id: z.coerce.number().int().positive("Select a customer"),
  prescription_date: z.string().min(1, "Prescription date is required"),
  right_sph: optionalDecimal,
  right_cyl: optionalDecimal,
  right_axis: optionalAxis,
  right_vn: z.string().max(20, "Max length is 20 characters").optional(),
  left_sph: optionalDecimal,
  left_cyl: optionalDecimal,
  left_axis: optionalAxis,
  left_vn: z.string().max(20, "Max length is 20 characters").optional(),
  fh: z.string().max(32, "Max length is 32 characters").optional(),
  add_power: optionalDecimal,
  pd: optionalDecimal,
  notes: z.string().optional()
});

type PrescriptionFormValues = z.infer<typeof prescriptionFormSchema>;

const defaultValues: PrescriptionFormValues = {
  customer_id: 0,
  prescription_date: "",
  right_sph: null,
  right_cyl: null,
  right_axis: null,
  right_vn: "",
  left_sph: null,
  left_cyl: null,
  left_axis: null,
  left_vn: "",
  fh: "",
  add_power: null,
  pd: null,
  notes: ""
};

export function PrescriptionsPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const [customerLookup, setCustomerLookup] = useState("");
  const debouncedLookup = useDebouncedValue(customerLookup, 300);

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    formState: { errors }
  } = useForm<PrescriptionFormValues>({
    resolver: zodResolver(prescriptionFormSchema),
    defaultValues
  });

  const customerLookupQuery = useQuery({
    queryKey: ["prescription-create-customer-lookup", debouncedLookup],
    queryFn: () => searchCustomers(debouncedLookup, 1, 15),
    enabled: debouncedLookup.length >= 2
  });

  useEffect(() => {
    const customerIdRaw = searchParams.get("customer_id");
    const customerQuery = (searchParams.get("customer_query") ?? "").trim();
    const contactNo = (searchParams.get("contact_no") ?? "").trim();

    let didApply = false;

    if (customerQuery.length > 0) {
      setCustomerLookup(customerQuery);
      didApply = true;
    } else if (contactNo.length > 0) {
      setCustomerLookup(contactNo);
      didApply = true;
    }

    if (customerIdRaw) {
      const customerId = Number(customerIdRaw);
      if (Number.isFinite(customerId) && customerId > 0) {
        setValue("customer_id", customerId, { shouldValidate: true, shouldDirty: true });
        didApply = true;
      }
    }

    if (didApply) {
      const next = new URLSearchParams(searchParams);
      next.delete("customer_id");
      next.delete("customer_query");
      next.delete("contact_no");
      setSearchParams(next, { replace: true });
    }
  }, [searchParams, setSearchParams, setValue]);

  const createMutation = useMutation({
    mutationFn: createPrescription,
    onSuccess: () => {
      toast.success("Prescription created");
      queryClient.invalidateQueries({ queryKey: ["prescriptions"] });
      reset(defaultValues);
      setCustomerLookup("");
    },
    onError: (error) => toast.error(getErrorMessage(error))
  });

  const onSubmit = (values: PrescriptionFormValues) => {
    const payload: PrescriptionPayload = {
      ...values,
      right_vn: values.right_vn || null,
      left_vn: values.left_vn || null,
      fh: values.fh || null,
      notes: values.notes || null
    };

    createMutation.mutate(payload);
  };

  return (
    <section className="rounded-2xl border border-pink-400/20 bg-matte-850/85 p-5 shadow-neon-ring">
      <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-100">Create Prescription</h2>
          <p className="text-sm text-slate-400">
            Full-screen creation flow. Use Saved Prescriptions to view and manage all existing records.
          </p>
        </div>

        <button
          type="button"
          onClick={() => navigate("/prescriptions/records")}
          className="rounded-lg border border-pink-300/45 bg-pink-500/15 px-3 py-2 text-sm font-medium text-pink-100"
        >
          View Saved Prescriptions
        </button>
      </div>

      <form className="space-y-3" onSubmit={handleSubmit(onSubmit)}>
        <div className="space-y-2">
          <input
            value={customerLookup}
            onChange={(event) => setCustomerLookup(event.target.value)}
            placeholder="Search customer by ID or mobile"
            className="w-full rounded-lg border border-pink-400/25 bg-matte-800 px-3 py-2 text-sm text-slate-100"
          />

          <select
            {...register("customer_id")}
            className="w-full rounded-lg border border-pink-400/25 bg-matte-800 px-3 py-2 text-sm text-slate-100"
          >
            <option value={0}>Select customer</option>
            {(customerLookupQuery.data?.items || []).map((customer) => (
              <option key={customer.id} value={customer.id}>
                {customer.customer_id} - {customer.name} ({customer.contact_no})
              </option>
            ))}
          </select>
          {errors.customer_id && <p className="text-xs text-rose-400">{errors.customer_id.message}</p>}
        </div>

        <div>
          <input
            type="date"
            {...register("prescription_date")}
            className="w-full rounded-lg border border-pink-400/25 bg-matte-800 px-3 py-2 text-sm text-slate-100"
          />
          {errors.prescription_date && <p className="text-xs text-rose-400">{errors.prescription_date.message}</p>}
        </div>

        <p className="pt-1 text-xs uppercase tracking-wide text-slate-400">Right Eye</p>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <input
            {...register("right_sph")}
            placeholder="Right SPH"
            className="rounded-lg border border-pink-400/25 bg-matte-800 px-3 py-2 text-sm text-slate-100"
          />
          <input
            {...register("right_cyl")}
            placeholder="Right CYL"
            className="rounded-lg border border-pink-400/25 bg-matte-800 px-3 py-2 text-sm text-slate-100"
          />
          <input
            {...register("right_axis")}
            placeholder="Right Axis"
            className="rounded-lg border border-pink-400/25 bg-matte-800 px-3 py-2 text-sm text-slate-100"
          />
          <input
            {...register("right_vn")}
            placeholder="Right VN"
            className="rounded-lg border border-pink-400/25 bg-matte-800 px-3 py-2 text-sm text-slate-100"
          />
        </div>

        <p className="pt-1 text-xs uppercase tracking-wide text-slate-400">Left Eye</p>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <input
            {...register("left_sph")}
            placeholder="Left SPH"
            className="rounded-lg border border-pink-400/25 bg-matte-800 px-3 py-2 text-sm text-slate-100"
          />
          <input
            {...register("left_cyl")}
            placeholder="Left CYL"
            className="rounded-lg border border-pink-400/25 bg-matte-800 px-3 py-2 text-sm text-slate-100"
          />
          <input
            {...register("left_axis")}
            placeholder="Left Axis"
            className="rounded-lg border border-pink-400/25 bg-matte-800 px-3 py-2 text-sm text-slate-100"
          />
          <input
            {...register("left_vn")}
            placeholder="Left VN"
            className="rounded-lg border border-pink-400/25 bg-matte-800 px-3 py-2 text-sm text-slate-100"
          />
        </div>

        <p className="pt-1 text-xs uppercase tracking-wide text-slate-400">Fitting</p>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <input
            {...register("pd")}
            placeholder="PD"
            className="rounded-lg border border-pink-400/25 bg-matte-800 px-3 py-2 text-sm text-slate-100"
          />
          <input
            {...register("add_power")}
            placeholder="ADD Power"
            className="rounded-lg border border-pink-400/25 bg-matte-800 px-3 py-2 text-sm text-slate-100"
          />
        </div>

        <input
          {...register("fh")}
          placeholder="FH"
          className="w-full rounded-lg border border-pink-400/25 bg-matte-800 px-3 py-2 text-sm text-slate-100"
        />

        <textarea
          {...register("notes")}
          rows={3}
          placeholder="Notes"
          className="w-full rounded-lg border border-pink-400/25 bg-matte-800 px-3 py-2 text-sm text-slate-100"
        />

        <div className="flex flex-wrap gap-2">
          <button
            type="submit"
            disabled={createMutation.isPending}
            className="rounded-lg border border-pink-300/45 bg-pink-500/15 px-4 py-2 text-sm text-pink-100"
          >
            {createMutation.isPending ? "Creating..." : "Create Prescription"}
          </button>
        </div>
      </form>
    </section>
  );
}
