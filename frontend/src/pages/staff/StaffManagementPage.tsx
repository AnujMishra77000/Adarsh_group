import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { createStaff, deleteStaff, listStaff, listStaffLoginActivities } from "@/features/staff/api";
import { getErrorMessage } from "@/lib/errors";

const staffCreateSchema = z.object({
  full_name: z.string().trim().max(255, "Maximum 255 characters").optional(),
  email: z.string().email("Enter a valid email"),
  password: z.string().min(8, "Password must be at least 8 characters")
});

type StaffCreateFormValues = z.infer<typeof staffCreateSchema>;

const defaultValues: StaffCreateFormValues = {
  full_name: "",
  email: "",
  password: ""
};

export function StaffManagementPage() {
  const queryClient = useQueryClient();

  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [activeOnly, setActiveOnly] = useState(true);

  const [activityPage, setActivityPage] = useState(1);

  const staffListQuery = useQuery({
    queryKey: ["staff", page, search, activeOnly],
    queryFn: () =>
      listStaff({
        page,
        page_size: 10,
        search: search.trim() || undefined,
        is_active: activeOnly ? true : undefined
      })
  });

  const loginActivityQuery = useQuery({
    queryKey: ["staff-login-activities", activityPage],
    queryFn: () => listStaffLoginActivities({ page: activityPage, page_size: 15 })
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors }
  } = useForm<StaffCreateFormValues>({
    resolver: zodResolver(staffCreateSchema),
    defaultValues
  });

  const createMutation = useMutation({
    mutationFn: createStaff,
    onSuccess: () => {
      toast.success("Staff account created");
      reset(defaultValues);
      queryClient.invalidateQueries({ queryKey: ["staff"] });
    },
    onError: (error) => toast.error(getErrorMessage(error))
  });

  const deleteMutation = useMutation({
    mutationFn: deleteStaff,
    onSuccess: (response) => {
      toast.success(response.message || "Staff account deleted");
      queryClient.invalidateQueries({ queryKey: ["staff"] });
    },
    onError: (error) => toast.error(getErrorMessage(error))
  });

  const staffTotalPages = useMemo(() => {
    if (!staffListQuery.data) return 1;
    return Math.max(1, Math.ceil(staffListQuery.data.total / staffListQuery.data.page_size));
  }, [staffListQuery.data]);

  const activityTotalPages = useMemo(() => {
    if (!loginActivityQuery.data) return 1;
    return Math.max(1, Math.ceil(loginActivityQuery.data.total / loginActivityQuery.data.page_size));
  }, [loginActivityQuery.data]);

  return (
    <div className="grid gap-6 xl:grid-cols-[1.6fr_1fr]">
      <section className="rounded-2xl border border-pink-300/20 bg-matte-850/90 p-5 shadow-neon-ring">
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold text-slate-100">Staff Management</h2>
            <p className="text-sm text-slate-300">Create new staff accounts, delete accounts, and review login activity.</p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <input
              value={search}
              onChange={(event) => {
                setSearch(event.target.value);
                setPage(1);
              }}
              placeholder="Search by email or name"
              className="w-60 rounded-lg border border-pink-300/30 bg-matte-800 px-3 py-2 text-sm text-slate-100 outline-none focus:border-pink-200"
            />
            <button
              type="button"
              onClick={() => {
                setActiveOnly((current) => !current);
                setPage(1);
              }}
              className="rounded-lg border border-pink-300/30 bg-pink-400/10 px-3 py-2 text-xs font-medium text-pink-100"
            >
              {activeOnly ? "Showing Active" : "Showing All"}
            </button>
          </div>
        </div>

        {staffListQuery.isLoading && <p className="text-sm text-slate-200">Loading staff...</p>}
        {staffListQuery.isError && <p className="text-sm text-rose-300">{getErrorMessage(staffListQuery.error)}</p>}

        {staffListQuery.data && staffListQuery.data.items.length === 0 && (
          <p className="rounded-lg border border-dashed border-slate-600 p-6 text-center text-sm text-slate-200">
            No staff accounts found.
          </p>
        )}

        {staffListQuery.data && staffListQuery.data.items.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="border-b border-pink-300/20 text-xs uppercase tracking-wide text-slate-300">
                <tr>
                  <th className="py-3 pr-3">Name</th>
                  <th className="py-3 pr-3">Email</th>
                  <th className="py-3 pr-3">Last Login</th>
                  <th className="py-3 pr-3">Status</th>
                  <th className="py-3 pr-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {staffListQuery.data.items.map((staff) => (
                  <tr key={staff.id} className="border-b border-slate-700/60 text-slate-100">
                    <td className="py-3 pr-3">{staff.full_name || "-"}</td>
                    <td className="py-3 pr-3 text-pink-100">{staff.email}</td>
                    <td className="py-3 pr-3">{staff.last_login_at ? new Date(staff.last_login_at).toLocaleString() : "-"}</td>
                    <td className="py-3 pr-3">
                      <span
                        className={`rounded px-2 py-1 text-xs ${
                          staff.is_active ? "bg-emerald-400/20 text-emerald-100" : "bg-slate-400/20 text-slate-200"
                        }`}
                      >
                        {staff.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="py-3 pr-3">
                      <button
                        type="button"
                        disabled={!staff.is_active || deleteMutation.isPending}
                        onClick={() => {
                          if (window.confirm(`Delete staff user ${staff.email}?`)) {
                            deleteMutation.mutate(staff.id);
                          }
                        }}
                        className="rounded-md border border-rose-300/40 px-3 py-1.5 text-xs text-rose-100 disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="mt-4 flex items-center justify-between text-xs text-slate-300">
          <span>
            Page {page} of {staffTotalPages}
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
              disabled={page >= staffTotalPages}
              onClick={() => setPage((currentPage) => Math.min(staffTotalPages, currentPage + 1))}
              className="rounded-md border border-pink-300/20 px-2 py-1 disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      </section>

      <section className="space-y-6">
        <div className="rounded-2xl border border-pink-300/20 bg-matte-850/90 p-5 shadow-neon-ring">
          <h3 className="text-lg font-semibold text-slate-100">Register New Staff</h3>

          <form className="mt-4 space-y-3" onSubmit={handleSubmit((values) => createMutation.mutate(values))}>
            <div>
              <input
                {...register("full_name")}
                placeholder="Full Name"
                className="w-full rounded-lg border border-pink-300/30 bg-matte-800 px-3 py-2 text-sm text-slate-100"
              />
              {errors.full_name && <p className="mt-1 text-xs text-rose-300">{errors.full_name.message}</p>}
            </div>

            <div>
              <input
                {...register("email")}
                placeholder="Email"
                className="w-full rounded-lg border border-pink-300/30 bg-matte-800 px-3 py-2 text-sm text-slate-100"
              />
              {errors.email && <p className="mt-1 text-xs text-rose-300">{errors.email.message}</p>}
            </div>

            <div>
              <input
                type="password"
                {...register("password")}
                placeholder="Password"
                className="w-full rounded-lg border border-pink-300/30 bg-matte-800 px-3 py-2 text-sm text-slate-100"
              />
              {errors.password && <p className="mt-1 text-xs text-rose-300">{errors.password.message}</p>}
            </div>

            <button
              type="submit"
              disabled={createMutation.isPending}
              className="w-full rounded-lg border border-pink-300/45 bg-pink-400/15 px-4 py-2 text-sm font-medium text-pink-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {createMutation.isPending ? "Creating..." : "Create Staff User"}
            </button>
          </form>
        </div>

        <div className="rounded-2xl border border-pink-300/20 bg-matte-850/90 p-5 shadow-neon-ring">
          <h3 className="text-lg font-semibold text-slate-100">Staff Login Activities</h3>

          {loginActivityQuery.isLoading && <p className="mt-3 text-sm text-slate-200">Loading activities...</p>}
          {loginActivityQuery.isError && <p className="mt-3 text-sm text-rose-300">{getErrorMessage(loginActivityQuery.error)}</p>}

          {loginActivityQuery.data && loginActivityQuery.data.items.length === 0 && (
            <p className="mt-3 text-sm text-slate-300">No login activities available.</p>
          )}

          {loginActivityQuery.data && loginActivityQuery.data.items.length > 0 && (
            <div className="mt-3 max-h-[320px] overflow-auto">
              <table className="w-full min-w-[560px] text-left text-xs">
                <thead className="border-b border-pink-300/20 uppercase tracking-wide text-slate-300">
                  <tr>
                    <th className="py-2 pr-2">Staff</th>
                    <th className="py-2 pr-2">Time</th>
                    <th className="py-2 pr-2">IP</th>
                  </tr>
                </thead>
                <tbody>
                  {loginActivityQuery.data.items.map((item) => (
                    <tr key={item.id} className="border-b border-slate-700/60 text-slate-100">
                      <td className="py-2 pr-2">{item.staff_full_name || item.staff_email}</td>
                      <td className="py-2 pr-2">{new Date(item.attempted_at).toLocaleString()}</td>
                      <td className="py-2 pr-2">{item.ip_address || "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="mt-3 flex items-center justify-between text-xs text-slate-300">
            <span>
              Page {activityPage} of {activityTotalPages}
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                disabled={activityPage <= 1}
                onClick={() => setActivityPage((currentPage) => Math.max(1, currentPage - 1))}
                className="rounded-md border border-pink-300/20 px-2 py-1 disabled:opacity-40"
              >
                Previous
              </button>
              <button
                type="button"
                disabled={activityPage >= activityTotalPages}
                onClick={() => setActivityPage((currentPage) => Math.min(activityTotalPages, currentPage + 1))}
                className="rounded-md border border-pink-300/20 px-2 py-1 disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
