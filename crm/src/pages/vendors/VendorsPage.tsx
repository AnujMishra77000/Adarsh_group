import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { useCurrentUser } from "@/features/auth/useCurrentUser";
import { createVendor, deleteVendor, listVendors, updateVendor } from "@/features/vendors/api";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { getErrorMessage } from "@/lib/errors";
import type { Vendor, VendorPayload } from "@/types/vendor";

const vendorFormSchema = z.object({
  vendor_name: z.string().min(2, "Vendor name is required"),
  contact_person: z.string().optional(),
  whatsapp_no: z.string().min(8, "WhatsApp number is required"),
  address: z.string().optional(),
  is_active: z.boolean()
});

type VendorFormValues = z.infer<typeof vendorFormSchema>;

const defaultValues: VendorFormValues = {
  vendor_name: "",
  contact_person: "",
  whatsapp_no: "",
  address: "",
  is_active: true
};

export function VendorsPage() {
  const queryClient = useQueryClient();
  const currentUserQuery = useCurrentUser();
  const canManageVendors = currentUserQuery.data?.role === "admin";

  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 300);
  const [editingVendor, setEditingVendor] = useState<Vendor | null>(null);

  const vendorsQuery = useQuery({
    queryKey: ["vendors", page, debouncedSearch],
    queryFn: () => listVendors({ page, page_size: 10, search: debouncedSearch || undefined })
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors }
  } = useForm<VendorFormValues>({
    resolver: zodResolver(vendorFormSchema),
    defaultValues
  });

  useEffect(() => {
    if (!editingVendor) {
      reset(defaultValues);
      return;
    }

    reset({
      vendor_name: editingVendor.vendor_name,
      contact_person: editingVendor.contact_person ?? "",
      whatsapp_no: editingVendor.whatsapp_no,
      address: editingVendor.address ?? "",
      is_active: editingVendor.is_active
    });
  }, [editingVendor, reset]);

  useEffect(() => {
    if (!canManageVendors && editingVendor) {
      setEditingVendor(null);
      reset(defaultValues);
    }
  }, [canManageVendors, editingVendor, reset]);

  const createMutation = useMutation({
    mutationFn: createVendor,
    onSuccess: () => {
      toast.success("Vendor created");
      queryClient.invalidateQueries({ queryKey: ["vendors"] });
      reset(defaultValues);
    },
    onError: (error) => toast.error(getErrorMessage(error))
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: Partial<VendorPayload> }) => updateVendor(id, payload),
    onSuccess: () => {
      toast.success("Vendor updated");
      queryClient.invalidateQueries({ queryKey: ["vendors"] });
      setEditingVendor(null);
      reset(defaultValues);
    },
    onError: (error) => toast.error(getErrorMessage(error))
  });

  const deleteMutation = useMutation({
    mutationFn: deleteVendor,
    onSuccess: () => {
      toast.success("Vendor deactivated");
      queryClient.invalidateQueries({ queryKey: ["vendors"] });
    },
    onError: (error) => toast.error(getErrorMessage(error))
  });

  const onSubmit = (values: VendorFormValues) => {
    if (!canManageVendors) {
      toast.error("Only admin can modify vendors");
      return;
    }

    const payload = {
      ...values,
      contact_person: values.contact_person || null,
      address: values.address || null
    };

    if (editingVendor) {
      updateMutation.mutate({ id: editingVendor.id, payload });
      return;
    }

    createMutation.mutate(payload);
  };

  return (
    <div className="grid gap-6 xl:grid-cols-[1.5fr_1fr]">
      <section className="order-2 rounded-2xl border border-pink-300/20 bg-matte-850/90 p-5 shadow-neon-ring">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold text-slate-100">Vendors</h2>
            <p className="text-sm text-slate-300">
              {canManageVendors
                ? "Manage active vendors for prescription dispatching."
                : "Vendor list is visible in read-only mode for staff users."}
            </p>
          </div>
          <input
            value={search}
            onChange={(event) => {
              setSearch(event.target.value);
              setPage(1);
            }}
            placeholder="Search vendors"
            className="w-full max-w-xs rounded-lg border border-pink-300/30 bg-matte-800 px-3 py-2 text-sm text-slate-100 outline-none focus:border-pink-200"
          />
        </div>

        {vendorsQuery.isLoading && <p className="text-sm text-slate-200">Loading vendors...</p>}
        {vendorsQuery.isError && <p className="text-sm text-rose-200">{getErrorMessage(vendorsQuery.error)}</p>}

        {vendorsQuery.data && vendorsQuery.data.items.length === 0 && (
          <p className="rounded-lg border border-dashed border-slate-600 p-6 text-center text-sm text-slate-300">No vendors found.</p>
        )}

        {vendorsQuery.data && vendorsQuery.data.items.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[680px] text-left text-sm">
              <thead className="border-b border-pink-300/20 text-xs uppercase tracking-wide text-slate-300">
                <tr>
                  <th className="py-3 pr-3">Vendor</th>
                  <th className="py-3 pr-3">Contact Person</th>
                  <th className="py-3 pr-3">WhatsApp</th>
                  <th className="py-3 pr-3">Status</th>
                  <th className="py-3 pr-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {vendorsQuery.data.items.map((vendor) => (
                  <tr key={vendor.id} className="border-b border-slate-700/60 text-slate-100">
                    <td className="py-3 pr-3 font-medium text-pink-100">{vendor.vendor_name}</td>
                    <td className="py-3 pr-3">{vendor.contact_person || "-"}</td>
                    <td className="py-3 pr-3">{vendor.whatsapp_no}</td>
                    <td className="py-3 pr-3">
                      <span
                        className={`rounded px-2 py-1 text-xs ${
                          vendor.is_active ? "bg-emerald-500/15 text-emerald-200" : "bg-slate-500/20 text-slate-200"
                        }`}
                      >
                        {vendor.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="py-3 pr-3">
                      {canManageVendors ? (
                        <div className="flex flex-wrap gap-2">
                          <button
                            type="button"
                            onClick={() => setEditingVendor(vendor)}
                            className="rounded-md border border-amber-400/30 px-2 py-1 text-xs text-amber-200"
                          >
                            Edit
                          </button>
                          <button
                            type="button"
                            disabled={!vendor.is_active}
                            onClick={() => {
                              if (window.confirm(`Deactivate vendor ${vendor.vendor_name}?`)) {
                                deleteMutation.mutate(vendor.id);
                              }
                            }}
                            className="rounded-md border border-rose-400/35 px-2 py-1 text-xs text-rose-200 disabled:opacity-40"
                          >
                            Deactivate
                          </button>
                        </div>
                      ) : (
                        <span className="text-xs text-slate-300">View only</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="order-1 rounded-2xl border border-pink-300/20 bg-matte-850/90 p-5 shadow-neon-ring">
        {canManageVendors ? (
          <>
            <h3 className="text-lg font-semibold text-slate-100">{editingVendor ? "Edit Vendor" : "Create Vendor"}</h3>
            <form className="mt-4 space-y-3" onSubmit={handleSubmit(onSubmit)}>
              <div>
                <input
                  {...register("vendor_name")}
                  placeholder="Vendor Name"
                  className="w-full rounded-lg border border-pink-300/30 bg-matte-800 px-3 py-2 text-sm text-slate-100"
                />
                {errors.vendor_name && <p className="mt-1 text-xs text-rose-300">{errors.vendor_name.message}</p>}
              </div>
              <div>
                <input
                  {...register("contact_person")}
                  placeholder="Contact Person"
                  className="w-full rounded-lg border border-pink-300/30 bg-matte-800 px-3 py-2 text-sm text-slate-100"
                />
              </div>
              <div>
                <input
                  {...register("whatsapp_no")}
                  placeholder="WhatsApp Number"
                  className="w-full rounded-lg border border-pink-300/30 bg-matte-800 px-3 py-2 text-sm text-slate-100"
                />
                {errors.whatsapp_no && <p className="mt-1 text-xs text-rose-300">{errors.whatsapp_no.message}</p>}
              </div>
              <div>
                <textarea
                  {...register("address")}
                  rows={3}
                  placeholder="Address"
                  className="w-full rounded-lg border border-pink-300/30 bg-matte-800 px-3 py-2 text-sm text-slate-100"
                />
              </div>
              <label className="flex items-center gap-2 text-sm text-slate-100">
                <input type="checkbox" {...register("is_active")} />
                Active Vendor
              </label>

              <div className="flex flex-wrap gap-2">
                <button type="submit" className="rounded-lg border border-pink-300/45 bg-pink-400/15 px-4 py-2 text-sm text-pink-50">
                  {editingVendor ? "Update" : "Create"}
                </button>
                {editingVendor && (
                  <button
                    type="button"
                    onClick={() => setEditingVendor(null)}
                    className="rounded-lg border border-slate-500/50 px-4 py-2 text-sm text-slate-100"
                  >
                    Cancel
                  </button>
                )}
              </div>
            </form>
          </>
        ) : (
          <div className="text-sm text-slate-200">Vendor create/update/deactivate controls are available only for admin users.</div>
        )}
      </section>
    </div>
  );
}
