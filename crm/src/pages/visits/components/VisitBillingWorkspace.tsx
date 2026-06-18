import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowUpRight, Link2, Receipt } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";

import { listBills } from "@/features/bills/api";
import { getVisitBillingContext, linkExistingBillToVisit } from "@/features/visits/api";
import { getErrorMessage } from "@/lib/errors";
import { CRM_PATHS } from "@/lib/routes";
import type { Visit, VisitBillSummary } from "@/types/visit";

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2
  }).format(value);
}

function billDetailPath(billId: number, returnTo: string): string {
  return `${CRM_PATHS.billing}/view/${billId}?${new URLSearchParams({ return_to: returnTo }).toString()}`;
}

function BillSummaryCard({ bill, returnTo }: { bill: VisitBillSummary; returnTo: string }) {
  return (
    <article className="rounded-lg border border-slate-600/45 bg-matte-900/70 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-100">{bill.bill_number}</p>
          <p className="mt-1 text-xs capitalize text-slate-400">{bill.payment_status} payment</p>
        </div>
        <Link
          to={billDetailPath(bill.id, returnTo)}
          className="inline-flex items-center gap-2 rounded-lg border border-emerald-300/35 px-3 py-2 text-sm font-medium text-emerald-100"
        >
          Open Bill <ArrowUpRight size={15} />
        </Link>
      </div>
      <dl className="mt-4 grid gap-3 sm:grid-cols-3">
        <div><dt className="text-xs uppercase text-slate-400">Grand Total</dt><dd className="mt-1 text-sm text-slate-100">{formatCurrency(bill.grand_total)}</dd></div>
        <div><dt className="text-xs uppercase text-slate-400">Paid</dt><dd className="mt-1 text-sm text-emerald-100">{formatCurrency(bill.paid_total)}</dd></div>
        <div><dt className="text-xs uppercase text-slate-400">Balance</dt><dd className="mt-1 text-sm text-amber-100">{formatCurrency(bill.balance_amount)}</dd></div>
      </dl>
    </article>
  );
}

export function VisitBillingWorkspace({ visit }: { visit: Visit }) {
  const queryClient = useQueryClient();
  const [selectedBillId, setSelectedBillId] = useState("");
  const returnTo = `${CRM_PATHS.visitWorkspace}/${visit.id}`;

  const contextQuery = useQuery({
    queryKey: ["visits", visit.id, "billing"],
    queryFn: () => getVisitBillingContext(visit.id)
  });
  const billsQuery = useQuery({
    queryKey: ["bills", "customer", visit.customer_id],
    queryFn: () => listBills({ customer_id: visit.customer_id, page: 1, page_size: 100 })
  });

  const availableBills = useMemo(
    () => (billsQuery.data?.items ?? []).filter((bill) => bill.visit_id === null && bill.dispensing_order_id === null),
    [billsQuery.data?.items]
  );

  const linkMutation = useMutation({
    mutationFn: () =>
      linkExistingBillToVisit(visit.id, {
        bill_id: Number(selectedBillId),
        dispensing_order_id: contextQuery.data?.dispensing_order_id ?? null
      }),
    onSuccess: () => {
      toast.success("Bill linked to this visit");
      setSelectedBillId("");
      queryClient.invalidateQueries({ queryKey: ["visits", visit.id, "billing"] });
      queryClient.invalidateQueries({ queryKey: ["bills"] });
    },
    onError: (error) => toast.error(getErrorMessage(error))
  });

  const createParams = new URLSearchParams({
    customer_id: String(visit.customer_id),
    customer_query: visit.customer_business_id ?? "",
    visit_id: String(visit.id),
    return_to: returnTo
  });
  if (contextQuery.data?.dispensing_order_id && !contextQuery.data.order_bill) {
    createParams.set("dispensing_order_id", String(contextQuery.data.dispensing_order_id));
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h4 className="text-lg font-semibold text-slate-100">Billing and Payment</h4>
          <p className="mt-1 text-sm text-slate-400">Uses the shared billing, payment, and invoice workflow.</p>
        </div>
        {!contextQuery.data?.order_bill && (
          <Link
            to={`${CRM_PATHS.billing}?${createParams.toString()}`}
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-emerald-300/35 bg-emerald-400/10 px-3 py-2 text-sm font-medium text-emerald-100"
          >
            <Receipt size={16} /> Create Bill
          </Link>
        )}
      </div>

      {contextQuery.isLoading && <p className="text-sm text-slate-300">Loading billing context...</p>}
      {contextQuery.isError && <p className="text-sm text-rose-200">{getErrorMessage(contextQuery.error)}</p>}

      {contextQuery.data?.order_bill && (
        <section className="space-y-3">
          <h5 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Dispensing Order Bill</h5>
          <BillSummaryCard bill={contextQuery.data.order_bill} returnTo={returnTo} />
        </section>
      )}

      {(contextQuery.data?.visit_bills ?? []).filter((bill) => bill.id !== contextQuery.data?.order_bill?.id).length > 0 && (
        <section className="space-y-3">
          <h5 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Other Visit Bills</h5>
          {(contextQuery.data?.visit_bills ?? [])
            .filter((bill) => bill.id !== contextQuery.data?.order_bill?.id)
            .map((bill) => <BillSummaryCard key={bill.id} bill={bill} returnTo={returnTo} />)}
        </section>
      )}

      {!contextQuery.data?.order_bill && availableBills.length > 0 && (
        <section className="space-y-3 border-t border-slate-700/60 pt-4">
          <h5 className="text-sm font-semibold text-slate-100">Link an existing bill</h5>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <label className="flex-1 text-sm text-slate-200">
              <span className="mb-1 block text-xs font-medium uppercase text-slate-400">Existing Bill</span>
              <select
                value={selectedBillId}
                onChange={(event) => setSelectedBillId(event.target.value)}
                className="h-10 w-full rounded-lg border border-pink-300/25 bg-matte-900 px-3 text-sm text-slate-100"
              >
                <option value="">Select an unlinked bill</option>
                {availableBills.map((bill) => (
                  <option key={bill.id} value={bill.id}>{bill.bill_number} · {formatCurrency(bill.grand_total)}</option>
                ))}
              </select>
            </label>
            <button
              type="button"
              disabled={!selectedBillId || linkMutation.isPending}
              onClick={() => linkMutation.mutate()}
              className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-indigo-300/35 bg-indigo-400/10 px-3 text-sm font-medium text-indigo-100 disabled:opacity-50"
            >
              <Link2 size={16} /> {linkMutation.isPending ? "Linking..." : "Link Selected Bill"}
            </button>
          </div>
        </section>
      )}
    </div>
  );
}
