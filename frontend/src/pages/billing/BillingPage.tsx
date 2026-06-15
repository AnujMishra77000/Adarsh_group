import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { z } from "zod";

import { createBill } from "@/features/bills/api";
import { calculateBillSummary, sanitizeBillPayloadMoney } from "@/features/bills/calculations";
import { searchCustomers } from "@/features/customers/api";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { getErrorMessage } from "@/lib/errors";
import type { BillPayload } from "@/types/bill";

const billFormSchema = z
  .object({
    customer_id: z.coerce.number().int().positive("Select a customer"),
    product_name: z.string().min(1, "Product name is required").max(255),
    frame_name: z.string().max(255).optional(),
    whole_price: z.coerce.number().min(0, "Whole price must be 0 or greater"),
    discount: z.coerce.number().min(0, "Discount must be 0 or greater"),
    paid_amount: z.coerce.number().min(0, "Paid amount must be 0 or greater"),
    payment_mode: z.enum(["cash", "upi"]),
    delivery_date: z.string().optional(),
    notes: z.string().optional()
  })
  .superRefine((values, ctx) => {
    const finalPrice = values.whole_price - values.discount;
    if (finalPrice < 0) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["discount"],
        message: "Discount cannot exceed whole price"
      });
    }

    if (values.paid_amount > finalPrice) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["paid_amount"],
        message: "Paid amount cannot exceed final price"
      });
    }
  });

type BillFormValues = z.infer<typeof billFormSchema>;

const defaultValues: BillFormValues = {
  customer_id: 0,
  product_name: "",
  frame_name: "",
  whole_price: 0,
  discount: 0,
  paid_amount: 0,
  payment_mode: "cash",
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
    formState: { errors }
  } = useForm<BillFormValues>({
    resolver: zodResolver(billFormSchema),
    defaultValues
  });

  const watchedWholePrice = Number(watch("whole_price") || 0);
  const watchedDiscount = Number(watch("discount") || 0);
  const watchedPaidAmount = Number(watch("paid_amount") || 0);

  const billSummary = useMemo(
    () => calculateBillSummary(watchedWholePrice, watchedDiscount, watchedPaidAmount),
    [watchedWholePrice, watchedDiscount, watchedPaidAmount]
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
    const sanitizedMoney = sanitizeBillPayloadMoney({
      whole_price: values.whole_price,
      discount: values.discount,
      paid_amount: values.paid_amount
    });

    const payload: BillPayload = {
      customer_id: values.customer_id,
      product_name: values.product_name,
      frame_name: values.frame_name || null,
      whole_price: sanitizedMoney.whole_price,
      discount: sanitizedMoney.discount,
      paid_amount: sanitizedMoney.paid_amount,
      payment_mode: values.payment_mode,
      delivery_date: values.delivery_date || null,
      notes: values.notes || null
    };

    createMutation.mutate(payload);
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
          onClick={() => navigate("/billing/records")}
          className="rounded-lg border border-pink-300/45 bg-pink-500/15 px-3 py-2 text-sm font-medium text-pink-100"
        >
          View Saved Bills
        </button>
      </div>

      <form className="space-y-3" onSubmit={handleSubmit(onSubmit)}>
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

        <div>
          <input
            {...register("product_name")}
            placeholder="Product Name"
            className="w-full rounded-lg border border-pink-400/25 bg-matte-800 px-3 py-2 text-sm text-slate-100"
          />
          {errors.product_name && <p className="mt-1 text-xs text-rose-400">{errors.product_name.message}</p>}
        </div>

        <div>
          <input
            {...register("frame_name")}
            placeholder="Frame Name (optional)"
            className="w-full rounded-lg border border-pink-400/25 bg-matte-800 px-3 py-2 text-sm text-slate-100"
          />
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div>
            <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-300">Total Cost</label>
            <input
              type="number"
              step="0.01"
              {...register("whole_price")}
              placeholder="Total Cost"
              className="w-full"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-300">Discount</label>
            <input
              type="number"
              step="0.01"
              {...register("discount")}
              placeholder="Discount"
              className="w-full"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-300">Paid Amount</label>
            <input
              type="number"
              step="0.01"
              {...register("paid_amount")}
              placeholder="Paid Amount"
              className="w-full"
            />
          </div>
        </div>

        {(errors.whole_price || errors.discount || errors.paid_amount) && (
          <div className="space-y-1 text-xs text-rose-400">
            {errors.whole_price?.message && <p>{errors.whole_price.message}</p>}
            {errors.discount?.message && <p>{errors.discount.message}</p>}
            {errors.paid_amount?.message && <p>{errors.paid_amount.message}</p>}
          </div>
        )}

        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <select
            {...register("payment_mode")}
            className="rounded-lg border border-pink-400/25 bg-matte-800 px-3 py-2 text-sm text-slate-100"
          >
            <option value="cash">Cash</option>
            <option value="upi">UPI</option>
          </select>

          <input
            type="date"
            {...register("delivery_date")}
            className="rounded-lg border border-pink-400/25 bg-matte-800 px-3 py-2 text-sm text-slate-100"
          />
        </div>

        <textarea
          {...register("notes")}
          rows={3}
          placeholder="Notes"
          className="w-full rounded-lg border border-pink-400/25 bg-matte-800 px-3 py-2 text-sm text-slate-100"
        />

        <div className="rounded-lg border border-pink-400/15 bg-matte-800/70 p-3 text-xs text-slate-300">
          <p className="mb-2 text-[11px] text-slate-300/90">
            Automated formula: (Total Cost - Discount) - Paid Amount
          </p>
          <div className="flex items-center justify-between">
            <span>Total Price After Discount</span>
            <span className="font-semibold text-pink-200">{formatCurrency(billSummary.totalAfterDiscount)}</span>
          </div>
          <div className="mt-1 flex items-center justify-between">
            <span>Paid Amount</span>
            <span className="font-semibold text-pink-200">{formatCurrency(billSummary.paidAmount)}</span>
          </div>
          <div className="mt-1 flex items-center justify-between">
            <span>Balance Amount</span>
            <span className="font-semibold text-pink-200">{formatCurrency(billSummary.balanceAmount)}</span>
          </div>
          <div className="mt-1 flex items-center justify-between">
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
