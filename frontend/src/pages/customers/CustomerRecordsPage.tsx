import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";

import { useCurrentUser } from "@/features/auth/useCurrentUser";
import { deleteCustomer, getCustomer, listCustomers } from "@/features/customers/api";
import { getErrorMessage } from "@/lib/errors";

export function CustomerRecordsPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const currentUserQuery = useCurrentUser();
  const canDeleteCustomers = currentUserQuery.data?.role === "admin";

  const initialSearch = (searchParams.get("q") ?? "").trim();
  const initialPage = Number.parseInt(searchParams.get("page") ?? "1", 10);

  const [searchInput, setSearchInput] = useState(initialSearch);
  const [searchTerm, setSearchTerm] = useState(initialSearch);
  const [page, setPage] = useState(Number.isFinite(initialPage) && initialPage > 0 ? initialPage : 1);
  const [selectedCustomerId, setSelectedCustomerId] = useState<number | null>(null);

  const customersQuery = useQuery({
    queryKey: ["customer-records", page, searchTerm],
    queryFn: () => listCustomers({ page, page_size: 10, search: searchTerm || undefined })
  });

  const customerDetailQuery = useQuery({
    queryKey: ["customer-record-detail", selectedCustomerId],
    queryFn: () => getCustomer(selectedCustomerId as number),
    enabled: selectedCustomerId !== null
  });

  const deleteMutation = useMutation({
    mutationFn: deleteCustomer,
    onSuccess: () => {
      toast.success("Customer deleted");
      queryClient.invalidateQueries({ queryKey: ["customer-records"] });
      queryClient.invalidateQueries({ queryKey: ["customers"] });
      setSelectedCustomerId(null);
    },
    onError: (error) => toast.error(getErrorMessage(error))
  });

  useEffect(() => {
    const next = new URLSearchParams();
    if (searchTerm.length > 0) {
      next.set("q", searchTerm);
    }
    if (page > 1) {
      next.set("page", String(page));
    }
    setSearchParams(next, { replace: true });
  }, [page, searchTerm, setSearchParams]);

  useEffect(() => {
    if (!customersQuery.data || customersQuery.data.items.length === 0) {
      setSelectedCustomerId(null);
      return;
    }

    const selectedStillVisible =
      selectedCustomerId !== null && customersQuery.data.items.some((customer) => customer.id === selectedCustomerId);

    if (!selectedStillVisible) {
      setSelectedCustomerId(customersQuery.data.items[0].id);
    }
  }, [customersQuery.data, selectedCustomerId]);

  const totalPages = useMemo(() => {
    if (!customersQuery.data) return 1;
    return Math.max(1, Math.ceil(customersQuery.data.total / customersQuery.data.page_size));
  }, [customersQuery.data]);

  const onSearchSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSearchTerm(searchInput.trim());
    setPage(1);
  };

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-pink-300/20 bg-matte-850/90 p-5 shadow-neon-ring">
        <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <h2 className="text-xl font-semibold text-slate-100">Customer Records</h2>
            <p className="text-sm text-slate-300">
              Search and open full customer history. Use customer ID, name, contact number, or WhatsApp number.
            </p>
          </div>
          <button
            type="button"
            onClick={() => navigate("/customers")}
            className="rounded-lg border border-pink-300/45 bg-pink-400/15 px-3 py-2 text-sm font-medium text-pink-50"
          >
            Create Customer
          </button>
        </div>

        <form onSubmit={onSearchSubmit} className="flex flex-col gap-2 sm:flex-row">
          <input
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            placeholder="Search customer..."
            className="w-full rounded-lg border border-pink-300/30 bg-matte-800 px-3 py-2 text-sm text-slate-100 outline-none focus:border-pink-200"
          />
          <button
            type="submit"
            className="rounded-lg border border-pink-300/45 bg-pink-400/15 px-4 py-2 text-sm font-medium text-pink-50"
          >
            Search
          </button>
        </form>
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.6fr_1fr]">
        <section className="rounded-2xl border border-pink-300/20 bg-matte-850/90 p-5 shadow-neon-ring">
          {customersQuery.isLoading && <p className="text-sm text-slate-200">Loading customers...</p>}
          {customersQuery.isError && <p className="text-sm text-rose-200">{getErrorMessage(customersQuery.error)}</p>}

          {customersQuery.data && customersQuery.data.items.length === 0 && (
            <p className="rounded-lg border border-dashed border-slate-600 p-6 text-center text-sm text-slate-300">No customers found.</p>
          )}

          {customersQuery.data && customersQuery.data.items.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[860px] text-left text-sm">
                <thead className="border-b border-pink-300/20 text-xs uppercase tracking-wide text-slate-300">
                  <tr>
                    <th className="py-3 pr-3">Customer ID</th>
                    <th className="py-3 pr-3">Name</th>
                    <th className="py-3 pr-3">Contact</th>
                    <th className="py-3 pr-3">Email</th>
                    <th className="py-3 pr-3">WhatsApp</th>
                    <th className="py-3 pr-3">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {customersQuery.data.items.map((customer) => {
                    const isSelected = selectedCustomerId === customer.id;
                    return (
                      <tr
                        key={customer.id}
                        className={`border-b border-slate-700/60 text-slate-100 ${isSelected ? "bg-pink-400/10" : ""}`}
                      >
                        <td className="py-3 pr-3 font-medium text-pink-100">{customer.customer_id}</td>
                        <td className="py-3 pr-3">{customer.name}</td>
                        <td className="py-3 pr-3">{customer.contact_no}</td>
                        <td className="py-3 pr-3">{customer.email || "-"}</td>
                        <td className="py-3 pr-3">{customer.whatsapp_no || "-"}</td>
                        <td className="py-3 pr-3">
                          <div className="flex flex-wrap gap-2">
                            <button
                              type="button"
                              onClick={() => setSelectedCustomerId(customer.id)}
                              className="rounded-md border border-pink-300/30 px-2 py-1 text-xs text-pink-100 hover:border-pink-200"
                            >
                              View
                            </button>
                            <button
                              type="button"
                              onClick={() => {
                                const params = new URLSearchParams({
                                  customer_id: String(customer.id),
                                  customer_query: customer.customer_id,
                                  contact_no: customer.contact_no
                                });
                                navigate(`/prescriptions?${params.toString()}`);
                              }}
                              className="rounded-md border border-indigo-400/30 px-2 py-1 text-xs text-indigo-200 hover:border-indigo-300"
                            >
                              Prescriptions
                            </button>
                            <button
                              type="button"
                              onClick={() => {
                                const params = new URLSearchParams({
                                  customer_id: String(customer.id),
                                  customer_query: customer.customer_id
                                });
                                navigate(`/billing?${params.toString()}`);
                              }}
                              className="rounded-md border border-emerald-400/30 px-2 py-1 text-xs text-emerald-200 hover:border-emerald-300"
                            >
                              Billing
                            </button>
                            {canDeleteCustomers && (
                              <button
                                type="button"
                                onClick={() => {
                                  if (window.confirm(`Delete customer ${customer.name}?`)) {
                                    deleteMutation.mutate(customer.id);
                                  }
                                }}
                                className="rounded-md border border-rose-400/35 px-2 py-1 text-xs text-rose-200 hover:border-rose-300"
                              >
                                Delete
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          <div className="mt-4 flex items-center justify-between text-xs text-slate-300">
            <span>
              Page {page} of {totalPages}
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => setPage((currentPage) => Math.max(1, currentPage - 1))}
                className="rounded-md border border-pink-300/20 px-2 py-1 disabled:opacity-40"
              >
                Previous
              </button>
              <button
                type="button"
                disabled={page >= totalPages}
                onClick={() => setPage((currentPage) => Math.min(totalPages, currentPage + 1))}
                className="rounded-md border border-pink-300/20 px-2 py-1 disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        </section>

        <section className="rounded-2xl border border-pink-300/20 bg-matte-850/90 p-5 shadow-neon-ring">
          <h3 className="text-lg font-semibold text-slate-100">Customer Full Detail</h3>
          {!selectedCustomerId && <p className="mt-2 text-sm text-slate-300">Select a customer to view full details.</p>}

          {customerDetailQuery.isLoading && selectedCustomerId !== null && (
            <p className="mt-2 text-sm text-slate-200">Loading customer detail...</p>
          )}
          {customerDetailQuery.isError && <p className="mt-2 text-sm text-rose-200">{getErrorMessage(customerDetailQuery.error)}</p>}

          {customerDetailQuery.data && (
            <div className="mt-3 space-y-4 text-sm text-slate-100">
              <div className="space-y-1">
                <p className="font-medium text-pink-100">
                  {customerDetailQuery.data.name} ({customerDetailQuery.data.customer_id})
                </p>
                <p>Contact: {customerDetailQuery.data.contact_no}</p>
                <p>Email: {customerDetailQuery.data.email || "-"}</p>
                <p>WhatsApp: {customerDetailQuery.data.whatsapp_no || "-"}</p>
                <p>Purpose: {customerDetailQuery.data.purpose_of_visit || "-"}</p>
                <p>Address: {customerDetailQuery.data.address || "-"}</p>
              </div>

              <div>
                <p className="mb-2 font-medium text-slate-100">Prescriptions</p>
                {customerDetailQuery.data.prescriptions.length === 0 && <p className="text-slate-300">No prescriptions yet.</p>}
                {customerDetailQuery.data.prescriptions.length > 0 && (
                  <ul className="space-y-1 text-slate-100">
                    {customerDetailQuery.data.prescriptions.map((item) => (
                      <li key={item.id}>
                        {new Date(item.prescription_date).toLocaleDateString()} {item.notes ? `- ${item.notes}` : ""}
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div>
                <p className="mb-2 font-medium text-slate-100">Bills</p>
                {customerDetailQuery.data.bills.length === 0 && <p className="text-slate-300">No bills yet.</p>}
                {customerDetailQuery.data.bills.length > 0 && (
                  <ul className="space-y-1 text-slate-100">
                    {customerDetailQuery.data.bills.map((bill) => (
                      <li key={bill.id}>
                        {bill.bill_number} - Final: {bill.final_price} - Balance: {bill.balance_amount}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
