import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { z } from "zod";

import { createBill } from "@/features/bills/api";
import { calculateBillSummary, sanitizeBillPayloadMoney } from "@/features/bills/calculations";
import { createCustomer } from "@/features/customers/api";
import { createPrescription } from "@/features/prescriptions/api";
import { getErrorMessage } from "@/lib/errors";
import type { BillPayload } from "@/types/bill";
import type { CustomerPayload } from "@/types/customer";
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
const optionalEmail = z
  .string()
  .trim()
  .optional()
  .refine((value) => (value ? /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value) : true), {
    message: "Enter a valid email"
  });


const customerFormSchema = z
  .object({
    name: z.string().min(2, "Name is required"),
    age: z
      .string()
      .optional()
      .transform((value) => {
        if (!value) return null;
        const numeric = Number(value);
        return Number.isNaN(numeric) ? null : numeric;
      }),
    contact_no: z.string().min(8, "Contact number is required"),
    email: optionalEmail,
    whatsapp_no: z.string().optional(),
    gender: z.preprocess(
      (value) => (value === "" || value === undefined ? null : value),
      z.enum(["male", "female", "other"]).nullable()
    ),
    address: z.string().optional(),
    purpose_of_visit: z.string().optional(),
    whatsapp_opt_in: z.boolean(),

    quick_add_prescription: z.boolean(),
    rx_prescription_date: z.string().optional(),
    rx_right_sph: optionalDecimal,
    rx_right_cyl: optionalDecimal,
    rx_right_axis: optionalAxis,
    rx_left_sph: optionalDecimal,
    rx_left_cyl: optionalDecimal,
    rx_left_axis: optionalAxis,
    rx_pd: optionalDecimal,
    rx_add_power: optionalDecimal,
    rx_notes: z.string().optional(),

    quick_add_bill: z.boolean(),
    bill_product_name: z.string().optional(),
    bill_frame_name: z.string().optional(),
    bill_whole_price: optionalDecimal,
    bill_discount: optionalDecimal,
    bill_paid_amount: optionalDecimal,
    bill_payment_mode: z.enum(["cash", "upi"]).optional(),
    bill_delivery_date: z.string().optional(),
    bill_notes: z.string().optional()
  })
  .superRefine((values, ctx) => {
    if (values.quick_add_prescription && !values.rx_prescription_date) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["rx_prescription_date"],
        message: "Prescription date is required"
      });
    }

    if (values.quick_add_bill) {
      const productName = values.bill_product_name?.trim() || "";
      const wholePrice = values.bill_whole_price;
      const discount = values.bill_discount ?? 0;
      const paidAmount = values.bill_paid_amount ?? 0;

      if (!productName) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ["bill_product_name"],
          message: "Product name is required"
        });
      }

      if (wholePrice === null) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ["bill_whole_price"],
          message: "Whole price is required"
        });
      }

      if (!values.bill_payment_mode) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ["bill_payment_mode"],
          message: "Payment mode is required"
        });
      }

      if (wholePrice !== null) {
        if (discount > wholePrice) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            path: ["bill_discount"],
            message: "Discount cannot exceed whole price"
          });
        }

        const finalPrice = wholePrice - discount;
        if (paidAmount > finalPrice) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            path: ["bill_paid_amount"],
            message: "Paid amount cannot exceed final price"
          });
        }
      }
    }
  });

type CustomerFormValues = z.infer<typeof customerFormSchema>;

const defaultValues: CustomerFormValues = {
  name: "",
  age: null,
  contact_no: "",
  email: "",
  whatsapp_no: "",
  gender: null,
  address: "",
  purpose_of_visit: "",
  whatsapp_opt_in: false,

  quick_add_prescription: false,
  rx_prescription_date: "",
  rx_right_sph: null,
  rx_right_cyl: null,
  rx_right_axis: null,
  rx_left_sph: null,
  rx_left_cyl: null,
  rx_left_axis: null,
  rx_pd: null,
  rx_add_power: null,
  rx_notes: "",

  quick_add_bill: false,
  bill_product_name: "",
  bill_frame_name: "",
  bill_whole_price: null,
  bill_discount: 0,
  bill_paid_amount: 0,
  bill_payment_mode: undefined,
  bill_delivery_date: "",
  bill_notes: ""
};

function formatMoney(value: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
    minimumFractionDigits: 2
  }).format(value);
}

export function CustomersPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [searchInput, setSearchInput] = useState("");

  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors }
  } = useForm<CustomerFormValues>({
    resolver: zodResolver(customerFormSchema),
    defaultValues
  });

  const quickAddPrescription = watch("quick_add_prescription");
  const quickAddBill = watch("quick_add_bill");

  const quickBillSummary = calculateBillSummary(
    Number(watch("bill_whole_price") ?? 0),
    Number(watch("bill_discount") ?? 0),
    Number(watch("bill_paid_amount") ?? 0)
  );

  const createMutation = useMutation({
    mutationFn: createCustomer
  });

  const quickPrescriptionMutation = useMutation({
    mutationFn: createPrescription
  });

  const quickBillMutation = useMutation({
    mutationFn: createBill
  });

  const isSubmitting = createMutation.isPending || quickPrescriptionMutation.isPending || quickBillMutation.isPending;

  const onSearchSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const query = searchInput.trim();
    const params = new URLSearchParams();

    if (query.length > 0) {
      params.set("q", query);
    }

    navigate(`/customers/records${params.toString() ? `?${params.toString()}` : ""}`);
  };

  const onSubmit = async (values: CustomerFormValues) => {
    const customerPayload: CustomerPayload = {
      name: values.name,
      age: values.age ?? null,
      contact_no: values.contact_no,
      email: values.email || null,
      whatsapp_no: values.whatsapp_no || null,
      gender: values.gender,
      address: values.address || null,
      purpose_of_visit: values.purpose_of_visit || null,
      whatsapp_opt_in: values.whatsapp_opt_in
    };

    try {
      const createdCustomer = await createMutation.mutateAsync(customerPayload);

      const completedSteps: string[] = [];

      if (values.quick_add_prescription) {
        const prescriptionPayload: PrescriptionPayload = {
          customer_id: createdCustomer.id,
          prescription_date: values.rx_prescription_date || new Date().toISOString().slice(0, 10),
          right_sph: values.rx_right_sph,
          right_cyl: values.rx_right_cyl,
          right_axis: values.rx_right_axis,
          left_sph: values.rx_left_sph,
          left_cyl: values.rx_left_cyl,
          left_axis: values.rx_left_axis,
          pd: values.rx_pd,
          add_power: values.rx_add_power,
          notes: values.rx_notes || null
        };
        await quickPrescriptionMutation.mutateAsync(prescriptionPayload);
        completedSteps.push("prescription added");
      }

      if (values.quick_add_bill) {
        const quickBillMoney = sanitizeBillPayloadMoney({
          whole_price: values.bill_whole_price ?? 0,
          discount: values.bill_discount ?? 0,
          paid_amount: values.bill_paid_amount ?? 0
        });

        const billPayload: BillPayload = {
          customer_id: createdCustomer.id,
          product_name: (values.bill_product_name || "").trim(),
          frame_name: values.bill_frame_name || null,
          whole_price: quickBillMoney.whole_price,
          discount: quickBillMoney.discount,
          paid_amount: quickBillMoney.paid_amount,
          payment_mode: values.bill_payment_mode || "cash",
          delivery_date: values.bill_delivery_date || null,
          notes: values.bill_notes || null
        };
        const bill = await quickBillMutation.mutateAsync(billPayload);
        completedSteps.push(`bill ${bill.bill_number} added`);
      }

      const suffix = completedSteps.length > 0 ? `, ${completedSteps.join(", ")}` : "";
      toast.success(`Customer created${suffix}`);

      queryClient.invalidateQueries({ queryKey: ["customers"] });
      queryClient.invalidateQueries({ queryKey: ["prescriptions"] });
      queryClient.invalidateQueries({ queryKey: ["bills"] });
      reset(defaultValues);

      setSearchInput(createdCustomer.contact_no);
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  };

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-pink-400/20 bg-matte-850/85 p-5 shadow-neon-ring">
        <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <h2 className="text-xl font-semibold text-slate-100">Create Customer</h2>
            <p className="text-sm text-slate-400">
              Main workflow first. Saved customer records are on a dedicated page.
            </p>
          </div>

          <button
            type="button"
            onClick={() => navigate("/customers/records")}
            className="rounded-lg border border-pink-300/45 bg-pink-500/15 px-3 py-2 text-sm font-medium text-pink-100"
          >
            Open Saved Records
          </button>
        </div>

        <form onSubmit={onSearchSubmit} className="mb-4 flex flex-col gap-2 sm:flex-row">
          <input
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            placeholder="Search saved customer by name / customer ID / contact / email / WhatsApp"
            className="h-11 w-full rounded-lg border border-pink-300/35 bg-matte-800 px-3 text-sm text-slate-100 outline-none transition-all duration-300 focus:border-neon-pink/70 focus:ring-2 focus:ring-neon-pink/20"
          />
          <button
            type="submit"
            className="h-11 rounded-lg border border-pink-300/45 bg-pink-500/15 px-4 text-sm font-medium text-pink-100 hover:bg-neon-pink/25 hover:text-slate-50"
          >
            Search
          </button>
        </form>

        <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-12">
            <div className="lg:col-span-5">
              <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-300">Customer Name</label>
              <input
                {...register("name")}
                placeholder="Enter full name"
                className="h-11 w-full rounded-lg border border-pink-300/35 bg-matte-800 px-3 text-sm text-slate-100 outline-none transition-all duration-300 focus:border-neon-pink/70 focus:ring-2 focus:ring-neon-pink/20"
              />
              {errors.name && <p className="mt-1 text-xs text-rose-400">{errors.name.message}</p>}
            </div>

            <div className="lg:col-span-2">
              <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-300">Age</label>
              <input
                {...register("age")}
                type="number"
                min="0"
                placeholder="Age"
                className="h-11 w-full rounded-lg border border-pink-300/35 bg-matte-800 px-3 text-sm text-slate-100 outline-none transition-all duration-300 focus:border-neon-pink/70 focus:ring-2 focus:ring-neon-pink/20"
              />
            </div>

            <div className="lg:col-span-2">
              <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-300">Gender</label>
              <select
                {...register("gender")}
                className="h-11 w-full rounded-lg border border-pink-300/35 bg-matte-800 px-3 text-sm text-slate-100 outline-none transition-all duration-300 focus:border-neon-pink/70 focus:ring-2 focus:ring-neon-pink/20"
              >
                <option value="">Select</option>
                <option value="male">Male</option>
                <option value="female">Female</option>
                <option value="other">Other</option>
              </select>
            </div>

            <div className="lg:col-span-3">
              <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-300">Contact Number</label>
              <input
                {...register("contact_no")}
                placeholder="Enter contact number"
                className="h-11 w-full rounded-lg border border-pink-300/35 bg-matte-800 px-3 text-sm text-slate-100 outline-none transition-all duration-300 focus:border-neon-pink/70 focus:ring-2 focus:ring-neon-pink/20"
              />
              {errors.contact_no && <p className="mt-1 text-xs text-rose-400">{errors.contact_no.message}</p>}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <div>
              <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-300">Email</label>
              <input
                {...register("email")}
                type="email"
                placeholder="Email ID (for welcome mail)"
                className="h-11 w-full rounded-lg border border-pink-300/35 bg-matte-800 px-3 text-sm text-slate-100 outline-none transition-all duration-300 focus:border-neon-pink/70 focus:ring-2 focus:ring-neon-pink/20"
              />
              {errors.email && <p className="mt-1 text-xs text-rose-400">{errors.email.message}</p>}
            </div>

            <div>
              <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-300">WhatsApp Number</label>
              <input
                {...register("whatsapp_no")}
                placeholder="WhatsApp Number (optional)"
                className="h-11 w-full rounded-lg border border-pink-300/35 bg-matte-800 px-3 text-sm text-slate-100 outline-none transition-all duration-300 focus:border-neon-pink/70 focus:ring-2 focus:ring-neon-pink/20"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <div>
              <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-300">Purpose Of Visit</label>
              <input
                {...register("purpose_of_visit")}
                placeholder="Purpose of Visit"
                className="h-11 w-full rounded-lg border border-pink-300/35 bg-matte-800 px-3 text-sm text-slate-100 outline-none transition-all duration-300 focus:border-neon-pink/70 focus:ring-2 focus:ring-neon-pink/20"
              />
            </div>

            <div>
              <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-300">Address</label>
              <textarea
                {...register("address")}
                placeholder="Address"
                rows={3}
                className="w-full rounded-lg border border-pink-300/35 bg-matte-800 px-3 py-2 text-sm text-slate-100 outline-none transition-all duration-300 focus:border-neon-pink/70 focus:ring-2 focus:ring-neon-pink/20"
              />
            </div>
          </div>

          <label className="flex items-center gap-2 text-sm text-slate-300">
            <input type="checkbox" {...register("whatsapp_opt_in")} />
            WhatsApp Opt-in
          </label>

          <div className="rounded-lg border border-pink-400/15 bg-matte-800/65 p-3 text-xs text-slate-300">
            New customer entries can be linked immediately with prescription and product/payment details.
          </div>

          <label className="flex items-center gap-2 text-sm text-slate-300">
            <input type="checkbox" {...register("quick_add_prescription")} />
            Add prescription now for this customer
          </label>

          {quickAddPrescription && (
            <div className="space-y-2 rounded-lg border border-pink-400/20 bg-matte-800/65 p-3">
              <p className="text-xs uppercase tracking-wide text-pink-200">Quick Prescription</p>
              <div>
                <input
                  type="date"
                  {...register("rx_prescription_date")}
                  className="w-full rounded-lg border border-pink-400/25 bg-matte-850 px-3 py-2 text-sm text-slate-100"
                />
                {errors.rx_prescription_date && (
                  <p className="mt-1 text-xs text-rose-400">{errors.rx_prescription_date.message}</p>
                )}
              </div>

              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
                <input
                  {...register("rx_right_sph")}
                  placeholder="Right SPH"
                  className="rounded-lg border border-pink-400/25 bg-matte-850 px-3 py-2 text-sm text-slate-100"
                />
                <input
                  {...register("rx_right_cyl")}
                  placeholder="Right CYL"
                  className="rounded-lg border border-pink-400/25 bg-matte-850 px-3 py-2 text-sm text-slate-100"
                />
                <input
                  {...register("rx_right_axis")}
                  placeholder="Right Axis"
                  className="rounded-lg border border-pink-400/25 bg-matte-850 px-3 py-2 text-sm text-slate-100"
                />

                <input
                  {...register("rx_left_sph")}
                  placeholder="Left SPH"
                  className="rounded-lg border border-pink-400/25 bg-matte-850 px-3 py-2 text-sm text-slate-100"
                />
                <input
                  {...register("rx_left_cyl")}
                  placeholder="Left CYL"
                  className="rounded-lg border border-pink-400/25 bg-matte-850 px-3 py-2 text-sm text-slate-100"
                />
                <input
                  {...register("rx_left_axis")}
                  placeholder="Left Axis"
                  className="rounded-lg border border-pink-400/25 bg-matte-850 px-3 py-2 text-sm text-slate-100"
                />

                <input
                  {...register("rx_pd")}
                  placeholder="PD"
                  className="rounded-lg border border-pink-400/25 bg-matte-850 px-3 py-2 text-sm text-slate-100"
                />
                <input
                  {...register("rx_add_power")}
                  placeholder="ADD Power"
                  className="rounded-lg border border-pink-400/25 bg-matte-850 px-3 py-2 text-sm text-slate-100"
                />
              </div>

              {(errors.rx_right_axis ||
                errors.rx_right_sph ||
                errors.rx_right_cyl ||
                errors.rx_left_axis ||
                errors.rx_left_sph ||
                errors.rx_left_cyl ||
                errors.rx_pd ||
                errors.rx_add_power) && (
                <div className="space-y-1 text-xs text-rose-400">
                  {errors.rx_right_axis?.message && <p>{errors.rx_right_axis.message}</p>}
                  {errors.rx_right_sph?.message && <p>{errors.rx_right_sph.message}</p>}
                  {errors.rx_right_cyl?.message && <p>{errors.rx_right_cyl.message}</p>}
                  {errors.rx_left_axis?.message && <p>{errors.rx_left_axis.message}</p>}
                  {errors.rx_left_sph?.message && <p>{errors.rx_left_sph.message}</p>}
                  {errors.rx_left_cyl?.message && <p>{errors.rx_left_cyl.message}</p>}
                  {errors.rx_pd?.message && <p>{errors.rx_pd.message}</p>}
                  {errors.rx_add_power?.message && <p>{errors.rx_add_power.message}</p>}
                </div>
              )}

              <textarea
                {...register("rx_notes")}
                rows={2}
                placeholder="Prescription notes"
                className="w-full rounded-lg border border-pink-400/25 bg-matte-850 px-3 py-2 text-sm text-slate-100"
              />
            </div>
          )}

          <label className="flex items-center gap-2 text-sm text-slate-300">
            <input type="checkbox" {...register("quick_add_bill")} />
            Add product and payment details now (create bill)
          </label>

          {quickAddBill && (
            <div className="space-y-2 rounded-lg border border-pink-400/20 bg-matte-800/65 p-3">
              <p className="text-xs uppercase tracking-wide text-pink-200">Quick Billing</p>

              <div>
                <input
                  {...register("bill_product_name")}
                  placeholder="Product Name"
                  className="w-full rounded-lg border border-pink-400/25 bg-matte-850 px-3 py-2 text-sm text-slate-100"
                />
                {errors.bill_product_name && <p className="mt-1 text-xs text-rose-400">{errors.bill_product_name.message}</p>}
              </div>

              <input
                {...register("bill_frame_name")}
                placeholder="Frame Name (optional)"
                className="w-full rounded-lg border border-pink-400/25 bg-matte-850 px-3 py-2 text-sm text-slate-100"
              />

              <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                <input
                  type="number"
                  step="0.01"
                  {...register("bill_whole_price")}
                  placeholder="Whole"
                  className="rounded-lg border border-pink-400/25 bg-matte-850 px-3 py-2 text-sm text-slate-100"
                />
                <input
                  type="number"
                  step="0.01"
                  {...register("bill_discount")}
                  placeholder="Discount"
                  className="rounded-lg border border-pink-400/25 bg-matte-850 px-3 py-2 text-sm text-slate-100"
                />
                <input
                  type="number"
                  step="0.01"
                  {...register("bill_paid_amount")}
                  placeholder="Paid"
                  className="rounded-lg border border-pink-400/25 bg-matte-850 px-3 py-2 text-sm text-slate-100"
                />
              </div>

              {(errors.bill_whole_price || errors.bill_discount || errors.bill_paid_amount) && (
                <div className="space-y-1 text-xs text-rose-400">
                  {errors.bill_whole_price?.message && <p>{errors.bill_whole_price.message}</p>}
                  {errors.bill_discount?.message && <p>{errors.bill_discount.message}</p>}
                  {errors.bill_paid_amount?.message && <p>{errors.bill_paid_amount.message}</p>}
                </div>
              )}

              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                <select
                  {...register("bill_payment_mode")}
                  className="rounded-lg border border-pink-400/25 bg-matte-850 px-3 py-2 text-sm text-slate-100"
                >
                  <option value="">Payment Mode</option>
                  <option value="cash">Cash</option>
                  <option value="upi">UPI</option>
                </select>

                <input
                  type="date"
                  {...register("bill_delivery_date")}
                  className="rounded-lg border border-pink-400/25 bg-matte-850 px-3 py-2 text-sm text-slate-100"
                />
              </div>
              {errors.bill_payment_mode && <p className="text-xs text-rose-400">{errors.bill_payment_mode.message}</p>}

              <textarea
                {...register("bill_notes")}
                rows={2}
                placeholder="Bill notes"
                className="w-full rounded-lg border border-pink-400/25 bg-matte-850 px-3 py-2 text-sm text-slate-100"
              />

              <div className="rounded-lg border border-pink-400/15 bg-matte-900/70 p-2 text-xs text-slate-300">
                <p className="mb-2 text-[11px] text-slate-300/90">
                  Automated formula: (Total Cost - Discount) - Paid Amount
                </p>
                <div className="flex items-center justify-between">
                  <span>Total Price After Discount</span>
                  <span className="font-semibold text-pink-200">{formatMoney(quickBillSummary.totalAfterDiscount)}</span>
                </div>
                <div className="mt-1 flex items-center justify-between">
                  <span>Paid Amount</span>
                  <span className="font-semibold text-pink-200">{formatMoney(quickBillSummary.paidAmount)}</span>
                </div>
                <div className="mt-1 flex items-center justify-between">
                  <span>Balance Amount</span>
                  <span className="font-semibold text-pink-200">{formatMoney(quickBillSummary.balanceAmount)}</span>
                </div>
              </div>
            </div>
          )}

          <div className="flex flex-wrap gap-2">
            <button
              type="submit"
              disabled={isSubmitting}
              className="rounded-lg border border-pink-300/45 bg-pink-500/15 px-4 py-2 text-sm font-medium text-pink-100"
            >
              Create
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
