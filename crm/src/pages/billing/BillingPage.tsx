import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useFieldArray, useForm } from "react-hook-form";
import { useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { z } from "zod";

import { createBill } from "@/features/bills/api";
import { calculateMultiBillSummary } from "@/features/bills/calculations";
import { searchCustomers } from "@/features/customers/api";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { getErrorMessage } from "@/lib/errors";
import { CRM_PATHS } from "@/lib/routes";
import type { BillItemPayload, BillPayload, BillPaymentPayload } from "@/types/bill";

const itemTypeOptions = [
  { value: "frame", label: "Frame" },
  { value: "lens", label: "Lens" },
  { value: "coating", label: "Coating" },
  { value: "contact_lens", label: "Contact Lens" },
  { value: "eye_test", label: "Eye Test" },
  { value: "repair", label: "Repair" },
  { value: "accessory", label: "Accessory" },
  { value: "other", label: "Other" }
] as const;

const paymentModeOptions = [
  { value: "cash", label: "Cash" },
  { value: "upi", label: "UPI" },
  { value: "card", label: "Card" },
  { value: "bank_transfer", label: "Bank Transfer" },
  { value: "other", label: "Other" }
] as const;

const billItemSchema = z
  .object({
    item_type: z.enum(["frame", "lens", "coating", "contact_lens", "eye_test", "repair", "accessory", "other"]),
    item_name: z.string().min(1, "Item name is required").max(255),
    quantity: z.coerce.number().positive("Quantity must be greater than 0"),
    unit_price: z.coerce.number().min(0, "Unit price must be 0 or greater"),
    discount: z.coerce.number().min(0, "Discount must be 0 or greater")
  })
  .superRefine((values, ctx) => {
    const gross = values.quantity * values.unit_price;
    if (values.discount > gross) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["discount"],
        message: "Discount cannot exceed line price"
      });
    }
  });

const billPaymentSchema = z.object({
  mode: z.enum(["cash", "upi", "card", "bank_transfer", "other"]),
  amount: z.coerce.number().min(0, "Payment amount must be 0 or greater"),
  paid_at: z.string().optional(),
  reference_no: z.string().max(255).optional()
});

const billFormSchema = z
  .object({
    customer_id: z.coerce.number().int().positive("Select a customer"),
    items: z.array(billItemSchema).min(1, "Add at least one item"),
    payments: z.array(billPaymentSchema),
    tax_total: z.coerce.number().min(0, "Tax must be 0 or greater"),
    delivery_date: z.string().optional(),
    notes: z.string().optional()
  })
  .superRefine((values, ctx) => {
    const summary = calculateMultiBillSummary(values.items, values.payments, values.tax_total);
    const rawPaidTotal = values.payments.reduce((sum, payment) => sum + Math.max(Number(payment.amount || 0), 0), 0);
    if (rawPaidTotal > summary.grandTotal) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["payments"],
        message: "Paid total cannot exceed grand total"
      });
    }
  });

type BillFormValues = z.infer<typeof billFormSchema>;

const defaultValues: BillFormValues = {
  customer_id: 0,
  items: [
    {
      item_type: "frame",
      item_name: "",
      quantity: 1,
      unit_price: 0,
      discount: 0
    }
  ],
  payments: [{ mode: "cash", amount: 0, paid_at: "", reference_no: "" }],
  tax_total: 0,
  delivery_date: "",
  notes: ""
};

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
    minimumFractionDigits: 2
  }).format(value);
}

function buildBillPayload(values: BillFormValues): BillPayload {
  const items: BillItemPayload[] = values.items.map((item) => ({
    item_type: item.item_type,
    item_name: item.item_name.trim(),
    quantity: Number(item.quantity || 0),
    unit_price: Number(item.unit_price || 0),
    discount: Number(item.discount || 0)
  }));
  const payments: BillPaymentPayload[] = values.payments
    .filter((payment) => Number(payment.amount || 0) > 0)
    .map((payment) => ({
      mode: payment.mode,
      amount: Number(payment.amount || 0),
      paid_at: payment.paid_at || null,
      reference_no: payment.reference_no?.trim() || null
    }));
  const summary = calculateMultiBillSummary(items, payments, values.tax_total);
  const firstItem = items[0];
  const frameItem = items.find((item) => item.item_type === "frame");

  return {
    customer_id: values.customer_id,
    product_name: firstItem.item_name,
    frame_name: frameItem?.item_name ?? null,
    whole_price: summary.subtotal,
    discount: summary.discountTotal,
    paid_amount: summary.paidTotal,
    payment_mode: payments[0]?.mode ?? "cash",
    tax_total: summary.taxTotal,
    items,
    payments,
    delivery_date: values.delivery_date || null,
    notes: values.notes || null
  };
}

export function BillingPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const [customerLookup, setCustomerLookup] = useState("");
  const debouncedCustomerLookup = useDebouncedValue(customerLookup, 300);

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    watch,
    control,
    formState: { errors }
  } = useForm<BillFormValues>({
    resolver: zodResolver(billFormSchema),
    defaultValues
  });

  const itemFields = useFieldArray({ control, name: "items" });
  const paymentFields = useFieldArray({ control, name: "payments" });
  const watchedItems = watch("items");
  const watchedPayments = watch("payments");
  const watchedTaxTotal = Number(watch("tax_total") || 0);

  const billSummary = useMemo(
    () => calculateMultiBillSummary(watchedItems || [], watchedPayments || [], watchedTaxTotal),
    [watchedItems, watchedPayments, watchedTaxTotal]
  );

  const customerLookupQuery = useQuery({
    queryKey: ["bill-create-customer-lookup", debouncedCustomerLookup],
    queryFn: () => searchCustomers(debouncedCustomerLookup, 1, 15),
    enabled: debouncedCustomerLookup.length >= 2
  });

  useEffect(() => {
    const customerIdRaw = searchParams.get("customer_id");
    const customerQuery = (searchParams.get("customer_query") ?? "").trim();

    let didApply = false;

    if (customerQuery.length > 0) {
      setCustomerLookup(customerQuery);
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
      setSearchParams(next, { replace: true });
    }
  }, [searchParams, setSearchParams, setValue]);

  const createMutation = useMutation({
    mutationFn: createBill,
    onSuccess: (bill) => {
      toast.success(
        bill.pdf_url
          ? "Bill " + bill.bill_number + " created and PDF generated"
          : "Bill " + bill.bill_number + " created"
      );
      reset(defaultValues);
      setCustomerLookup("");
      queryClient.invalidateQueries({ queryKey: ["bills"] });
      queryClient.invalidateQueries({ queryKey: ["bill", bill.id] });
    },
    onError: (error) => toast.error(getErrorMessage(error))
  });

  const onSubmit = (values: BillFormValues) => {
    createMutation.mutate(buildBillPayload(values));
  };

  return (
    <section className="rounded-2xl border border-pink-400/20 bg-matte-850/85 p-5 shadow-neon-ring">
      <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-100">Generate Bill</h2>
          <p className="text-sm text-slate-400">
            Full-screen bill generation. Use Saved Bills to view and manage all created billing records.
          </p>
        </div>

        <button
          type="button"
          onClick={() => navigate(CRM_PATHS.billingRecords)}
          className="rounded-lg border border-pink-300/45 bg-pink-500/15 px-3 py-2 text-sm font-medium text-pink-100"
        >
          View Saved Bills
        </button>
      </div>

      <form className="space-y-5" onSubmit={handleSubmit(onSubmit)}>
        <div className="space-y-2">
          <input
            value={customerLookup}
            onChange={(event) => setCustomerLookup(event.target.value)}
            placeholder="Search customer by ID or contact"
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

        <div className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-pink-200">Items</h3>
            <button
              type="button"
              onClick={() => itemFields.append({ item_type: "lens", item_name: "", quantity: 1, unit_price: 0, discount: 0 })}
              className="rounded-lg border border-pink-300/45 bg-pink-500/15 px-3 py-2 text-xs text-pink-100"
            >
              Add Item
            </button>
          </div>

          <div className="space-y-2">
            {itemFields.fields.map((field, index) => (
              <div key={field.id} className="grid grid-cols-1 gap-2 rounded-lg border border-pink-400/15 bg-matte-800/70 p-3 lg:grid-cols-12">
                <select {...register(`items.${index}.item_type`)} className="lg:col-span-2">
                  {itemTypeOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
                <input {...register(`items.${index}.item_name`)} placeholder="Item name" className="lg:col-span-4" />
                <input type="number" step="0.01" {...register(`items.${index}.quantity`)} placeholder="Qty" className="lg:col-span-1" />
                <input type="number" step="0.01" {...register(`items.${index}.unit_price`)} placeholder="Unit price" className="lg:col-span-2" />
                <input type="number" step="0.01" {...register(`items.${index}.discount`)} placeholder="Discount" className="lg:col-span-2" />
                <button
                  type="button"
                  disabled={itemFields.fields.length === 1}
                  onClick={() => itemFields.remove(index)}
                  className="rounded-lg border border-rose-300/35 px-3 py-2 text-xs text-rose-200 disabled:cursor-not-allowed disabled:opacity-40 lg:col-span-1"
                >
                  Remove
                </button>
                {errors.items?.[index] && (
                  <p className="text-xs text-rose-400 lg:col-span-12">
                    {errors.items[index]?.item_name?.message ||
                      errors.items[index]?.quantity?.message ||
                      errors.items[index]?.unit_price?.message ||
                      errors.items[index]?.discount?.message}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-pink-200">Payments</h3>
            <button
              type="button"
              onClick={() => paymentFields.append({ mode: "upi", amount: 0, paid_at: "", reference_no: "" })}
              className="rounded-lg border border-pink-300/45 bg-pink-500/15 px-3 py-2 text-xs text-pink-100"
            >
              Add Payment
            </button>
          </div>

          <div className="space-y-2">
            {paymentFields.fields.map((field, index) => (
              <div key={field.id} className="grid grid-cols-1 gap-2 rounded-lg border border-pink-400/15 bg-matte-800/70 p-3 lg:grid-cols-12">
                <select {...register(`payments.${index}.mode`)} className="lg:col-span-2">
                  {paymentModeOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
                <input type="number" step="0.01" {...register(`payments.${index}.amount`)} placeholder="Amount" className="lg:col-span-2" />
                <input type="datetime-local" {...register(`payments.${index}.paid_at`)} className="lg:col-span-3" />
                <input {...register(`payments.${index}.reference_no`)} placeholder="Reference no" className="lg:col-span-4" />
                <button
                  type="button"
                  disabled={paymentFields.fields.length === 1}
                  onClick={() => paymentFields.remove(index)}
                  className="rounded-lg border border-rose-300/35 px-3 py-2 text-xs text-rose-200 disabled:cursor-not-allowed disabled:opacity-40 lg:col-span-1"
                >
                  Remove
                </button>
                {errors.payments?.[index] && (
                  <p className="text-xs text-rose-400 lg:col-span-12">
                    {errors.payments[index]?.amount?.message || errors.payments[index]?.reference_no?.message}
                  </p>
                )}
              </div>
            ))}
            {errors.payments && !Array.isArray(errors.payments) && (
              <p className="text-xs text-rose-400">{errors.payments.message}</p>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <input type="number" step="0.01" {...register("tax_total")} placeholder="Tax total" />
          <input type="date" {...register("delivery_date")} />
        </div>
        {errors.tax_total && <p className="text-xs text-rose-400">{errors.tax_total.message}</p>}

        <textarea {...register("notes")} rows={3} placeholder="Notes" className="w-full rounded-lg border border-pink-400/25 bg-matte-800 px-3 py-2 text-sm text-slate-100" />

        <div className="rounded-lg border border-pink-400/15 bg-matte-800/70 p-3 text-xs text-slate-300">
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            <div className="flex items-center justify-between gap-3">
              <span>Subtotal</span>
              <span className="font-semibold text-pink-200">{formatCurrency(billSummary.subtotal)}</span>
            </div>
            <div className="flex items-center justify-between gap-3">
              <span>Discount</span>
              <span className="font-semibold text-pink-200">{formatCurrency(billSummary.discountTotal)}</span>
            </div>
            <div className="flex items-center justify-between gap-3">
              <span>Tax</span>
              <span className="font-semibold text-pink-200">{formatCurrency(billSummary.taxTotal)}</span>
            </div>
            <div className="flex items-center justify-between gap-3">
              <span>Grand Total</span>
              <span className="font-semibold text-pink-200">{formatCurrency(billSummary.grandTotal)}</span>
            </div>
            <div className="flex items-center justify-between gap-3">
              <span>Paid</span>
              <span className="font-semibold text-pink-200">{formatCurrency(billSummary.paidTotal)}</span>
            </div>
            <div className="flex items-center justify-between gap-3">
              <span>Balance</span>
              <span className="font-semibold text-pink-200">{formatCurrency(billSummary.balanceAmount)}</span>
            </div>
          </div>
          <div className="mt-2 flex items-center justify-between border-t border-pink-400/10 pt-2">
            <span>Payment Status</span>
            <span className="font-semibold text-pink-200">{billSummary.paymentStatus.toUpperCase()}</span>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            type="submit"
            disabled={createMutation.isPending}
            className="rounded-lg border border-pink-300/45 bg-pink-500/15 px-4 py-2 text-sm text-pink-100"
          >
            {createMutation.isPending ? "Creating..." : "Generate Bill"}
          </button>
        </div>
      </form>
    </section>
  );
}
