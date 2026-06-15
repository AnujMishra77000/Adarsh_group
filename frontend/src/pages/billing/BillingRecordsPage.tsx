import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";

import { deleteBill, listBills } from "@/features/bills/api";
import { useCurrentUser } from "@/features/auth/useCurrentUser";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { getErrorMessage } from "@/lib/errors";

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
    minimumFractionDigits: 2
  }).format(value);
}

export function BillingRecordsPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const currentUserQuery = useCurrentUser();
  const currentRole = currentUserQuery.data?.role;
  const canUpdateBills = currentRole === "admin" || currentRole === "staff";
  const canDeleteBills = currentRole === "admin";

  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [customerIdFilter, setCustomerIdFilter] = useState<number | undefined>(undefined);
  const [prefillApplied, setPrefillApplied] = useState(false);
  const debouncedSearch = useDebouncedValue(search, 300);

  const billsQuery = useQuery({
    queryKey: ["bills", page, debouncedSearch, customerIdFilter],
    queryFn: () =>
      listBills({
        page,
        page_size: 10,
        search: debouncedSearch || undefined,
        customer_id: customerIdFilter
      })
  });

  useEffect(() => {
    if (prefillApplied) {
      return;
    }

    const customerIdRaw = searchParams.get("customer_id");
    const customerQuery = (searchParams.get("customer_query") ?? "").trim();
    const contactNo = (searchParams.get("contact_no") ?? "").trim();
    let didApply = false;

    if (customerIdRaw) {
      const customerId = Number(customerIdRaw);
      if (Number.isFinite(customerId) && customerId > 0) {
        setCustomerIdFilter(customerId);
        didApply = true;
      }
    }

    if (customerQuery.length > 0) {
      setSearch(customerQuery);
      didApply = true;
    } else if (contactNo.length > 0) {
      setSearch(contactNo);
      didApply = true;
    }

    if (didApply) {
      setPage(1);
      const next = new URLSearchParams(searchParams);
      next.delete("customer_id");
      next.delete("customer_query");
      next.delete("contact_no");
      setSearchParams(next, { replace: true });
    }

    setPrefillApplied(true);
  }, [prefillApplied, searchParams, setSearchParams]);

  const deleteMutation = useMutation({
    mutationFn: deleteBill,
    onSuccess: () => {
      toast.success("Bill deleted");
      queryClient.invalidateQueries({ queryKey: ["bills"] });
    },
    onError: (error) => toast.error(getErrorMessage(error))
  });

  const totalPages = useMemo(() => {
    if (billsQuery.data === undefined) return 1;
    return Math.max(1, Math.ceil(billsQuery.data.total / billsQuery.data.page_size));
  }, [billsQuery.data]);

  return (
    <section className="rounded-2xl border border-pink-400/20 bg-matte-850/85 p-5 shadow-neon-ring">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-slate-100">Saved Bills</h2>
          <p className="text-sm text-slate-400">
            This page shows only saved bills. Use View, Update, or PDF to open full bill pages.
          </p>
        </div>
        <input
          value={search}
          onChange={(event) => {
            setSearch(event.target.value);
            setPage(1);
          }}
          placeholder="Search bill, customer, product, frame, mobile"
          className="w-full max-w-xs rounded-lg border border-pink-400/25 bg-matte-800 px-3 py-2 text-sm text-slate-100 outline-none focus:border-pink-300"
        />
      </div>

      {customerIdFilter !== undefined && (
        <div className="mb-4 flex items-center justify-between rounded-lg border border-pink-300/30 bg-pink-500/10 px-3 py-2 text-xs text-pink-100">
          <span>Customer filter active (ID: {customerIdFilter})</span>
          <button
            type="button"
            onClick={() => {
              setCustomerIdFilter(undefined);
              setPage(1);
            }}
            className="rounded-md border border-pink-300/45 px-2 py-1"
          >
            Clear Filter
          </button>
        </div>
      )}

      {billsQuery.isLoading && <p className="text-sm text-slate-300">Loading bills...</p>}
      {billsQuery.isError && <p className="text-sm text-rose-400">{getErrorMessage(billsQuery.error)}</p>}

      {billsQuery.data && billsQuery.data.items.length === 0 && (
        <p className="rounded-lg border border-dashed border-slate-700 p-6 text-center text-sm text-slate-400">
          No bills found.
        </p>
      )}

      {billsQuery.data && billsQuery.data.items.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[980px] text-left text-sm">
            <thead className="border-b border-pink-400/20 text-xs uppercase tracking-wide text-slate-400">
              <tr>
                <th className="py-3 pr-3">Bill No</th>
                <th className="py-3 pr-3">Customer</th>
                <th className="py-3 pr-3">Mobile</th>
                <th className="py-3 pr-3">Product</th>
                <th className="py-3 pr-3">Final</th>
                <th className="py-3 pr-3">Balance</th>
                <th className="py-3 pr-3">Status</th>
                <th className="py-3 pr-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {billsQuery.data.items.map((bill) => (
                <tr key={bill.id} className="border-b border-slate-800/80 text-slate-200">
                  <td className="py-3 pr-3 font-medium text-pink-200">{bill.bill_number}</td>
                  <td className="py-3 pr-3">{bill.customer_name_snapshot}</td>
                  <td className="py-3 pr-3">{bill.customer_contact_no || "-"}</td>
                  <td className="py-3 pr-3">{bill.product_name}</td>
                  <td className="py-3 pr-3">{formatCurrency(Number(bill.final_price))}</td>
                  <td className="py-3 pr-3">{formatCurrency(Number(bill.balance_amount))}</td>
                  <td className="py-3 pr-3">
                    <span
                      className={`rounded px-2 py-1 text-xs ${
                        bill.payment_status === "paid"
                          ? "bg-emerald-500/15 text-emerald-200"
                          : bill.payment_status === "partial"
                          ? "bg-amber-500/15 text-amber-200"
                          : "bg-slate-500/20 text-slate-300"
                      }`}
                    >
                      {bill.payment_status.toUpperCase()}
                    </span>
                  </td>
                  <td className="py-3 pr-3">
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => navigate("/billing/view/" + bill.id)}
                        className="rounded-md border border-sky-400/35 px-2 py-1 text-xs text-sky-200"
                      >
                        View
                      </button>
                      {canUpdateBills && (
                        <button
                          type="button"
                          onClick={() => navigate("/billing/edit/" + bill.id)}
                          className="rounded-md border border-amber-400/30 px-2 py-1 text-xs text-amber-200"
                        >
                          Update
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => navigate("/billing/view/" + bill.id + "?focus=pdf")}
                        className="rounded-md border border-pink-400/30 px-2 py-1 text-xs text-pink-200"
                      >
                        PDF
                      </button>
                      {canDeleteBills && (
                        <button
                          type="button"
                          onClick={() => {
                            if (window.confirm(`Delete bill ${bill.bill_number}?`)) {
                              deleteMutation.mutate(bill.id);
                            }
                          }}
                          className="rounded-md border border-rose-400/35 px-2 py-1 text-xs text-rose-200"
                        >
                          Delete
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="mt-4 flex items-center justify-between text-xs text-slate-400">
        <span>
          Page {page} of {totalPages}
        </span>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={page <= 1}
            onClick={() => setPage((currentPage) => Math.max(1, currentPage - 1))}
            className="rounded-md border border-pink-400/20 px-2 py-1 disabled:opacity-40"
          >
            Previous
          </button>
          <button
            type="button"
            disabled={page >= totalPages}
            onClick={() => setPage((currentPage) => Math.min(totalPages, currentPage + 1))}
            className="rounded-md border border-pink-400/20 px-2 py-1 disabled:opacity-40"
          >
            Next
          </button>
        </div>
      </div>
    </section>
  );
}
