import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { useCurrentUser } from "@/features/auth/useCurrentUser";
import {
  createCampaign,
  deleteCampaign,
  getCampaignLogs,
  listCampaigns,
  scheduleCampaign,
  updateCampaign
} from "@/features/campaigns/api";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { getErrorMessage } from "@/lib/errors";
import type { Campaign, CampaignStatus } from "@/types/campaign";

const campaignFormSchema = z.object({
  title: z.string().min(3, "Title must be at least 3 characters").max(255),
  message_body: z.string().min(1, "Message is required").max(5000),
  scheduled_date: z.string().min(1, "Date is required"),
  scheduled_time: z.string().min(1, "Time is required")
});

type CampaignFormValues = z.infer<typeof campaignFormSchema>;

type CampaignViewMode = "create" | "logs";

const defaultValues: CampaignFormValues = {
  title: "",
  message_body: "",
  scheduled_date: "",
  scheduled_time: ""
};

function toLocalDateParts(isoString: string): { date: string; time: string } {
  const value = new Date(isoString);
  const pad = (input: number) => String(input).padStart(2, "0");

  return {
    date: `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())}`,
    time: `${pad(value.getHours())}:${pad(value.getMinutes())}`
  };
}

function statusClassName(status: CampaignStatus): string {
  if (status === "completed") return "bg-emerald-500/15 text-emerald-200";
  if (status === "running") return "bg-sky-500/15 text-sky-200";
  if (status === "scheduled") return "bg-pink-500/15 text-pink-100";
  if (status === "failed") return "bg-rose-500/15 text-rose-200";
  if (status === "cancelled") return "bg-slate-500/25 text-slate-200";
  return "bg-amber-500/15 text-amber-200";
}

export function CampaignsPage() {
  const queryClient = useQueryClient();
  const currentUserQuery = useCurrentUser();
  const canManageCampaigns = currentUserQuery.data?.role === "admin";

  const [viewMode, setViewMode] = useState<CampaignViewMode>("create");

  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 300);
  const [statusFilter, setStatusFilter] = useState<"all" | CampaignStatus>("all");

  const [editingCampaign, setEditingCampaign] = useState<Campaign | null>(null);
  const [selectedCampaign, setSelectedCampaign] = useState<Campaign | null>(null);

  const campaignListQuery = useQuery({
    queryKey: ["campaigns", page, debouncedSearch, statusFilter],
    queryFn: () =>
      listCampaigns({
        page,
        page_size: 10,
        search: debouncedSearch || undefined,
        status: statusFilter === "all" ? undefined : statusFilter
      })
  });

  const logsQuery = useQuery({
    queryKey: ["campaign-logs", selectedCampaign?.id],
    queryFn: () => getCampaignLogs((selectedCampaign as Campaign).id, 1, 25),
    enabled: selectedCampaign !== null
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors }
  } = useForm<CampaignFormValues>({
    resolver: zodResolver(campaignFormSchema),
    defaultValues
  });

  useEffect(() => {
    if (!canManageCampaigns) {
      setViewMode("logs");
      setEditingCampaign(null);
      reset(defaultValues);
    }
  }, [canManageCampaigns, reset]);

  useEffect(() => {
    if (!editingCampaign) {
      reset(defaultValues);
      return;
    }

    const local = toLocalDateParts(editingCampaign.scheduled_at);
    reset({
      title: editingCampaign.title,
      message_body: editingCampaign.message_body,
      scheduled_date: local.date,
      scheduled_time: local.time
    });
  }, [editingCampaign, reset]);

  const createMutation = useMutation({
    mutationFn: createCampaign,
    onSuccess: () => {
      toast.success("Campaign created");
      reset(defaultValues);
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
    },
    onError: (error) => toast.error(getErrorMessage(error))
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: { title: string; message_body: string; scheduled_at: string } }) =>
      updateCampaign(id, payload),
    onSuccess: () => {
      toast.success("Campaign updated");
      setEditingCampaign(null);
      reset(defaultValues);
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
    },
    onError: (error) => toast.error(getErrorMessage(error))
  });

  const scheduleMutation = useMutation({
    mutationFn: scheduleCampaign,
    onSuccess: () => {
      toast.success("Campaign scheduled");
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      if (selectedCampaign) {
        queryClient.invalidateQueries({ queryKey: ["campaign-logs", selectedCampaign.id] });
      }
    },
    onError: (error) => toast.error(getErrorMessage(error))
  });

  const deleteMutation = useMutation({
    mutationFn: deleteCampaign,
    onSuccess: () => {
      toast.success("Campaign deleted");
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      setSelectedCampaign(null);
    },
    onError: (error) => toast.error(getErrorMessage(error))
  });

  const totalPages = useMemo(() => {
    if (!campaignListQuery.data) return 1;
    return Math.max(1, Math.ceil(campaignListQuery.data.total / campaignListQuery.data.page_size));
  }, [campaignListQuery.data]);

  const onSubmit = (values: CampaignFormValues) => {
    if (!canManageCampaigns) {
      toast.error("Campaign creation and scheduling is admin-only");
      return;
    }

    const scheduledDate = new Date(`${values.scheduled_date}T${values.scheduled_time}:00`);
    if (Number.isNaN(scheduledDate.getTime())) {
      toast.error("Please provide a valid schedule date and time");
      return;
    }

    const payload = {
      title: values.title,
      message_body: values.message_body,
      scheduled_at: scheduledDate.toISOString()
    };

    if (editingCampaign) {
      updateMutation.mutate({ id: editingCampaign.id, payload });
      return;
    }

    createMutation.mutate(payload);
  };

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-pink-300/20 bg-matte-850/90 p-5 shadow-neon-ring">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold text-slate-100">Campaign Management</h2>
            <p className="text-sm text-slate-300">
              {canManageCampaigns
                ? "Create campaign in full-page mode and switch to logs/details when needed."
                : "Campaign run controls are admin-only. You can view campaign details and logs."}
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            {canManageCampaigns && viewMode === "create" && (
              <button
                type="button"
                onClick={() => {
                  setViewMode("logs");
                  setEditingCampaign(null);
                  reset(defaultValues);
                }}
                className="rounded-lg border border-pink-300/45 bg-pink-500/15 px-4 py-2 text-sm font-medium text-pink-100 hover:bg-neon-pink/25 hover:text-slate-50"
              >
                View Logs & Details
              </button>
            )}

            {canManageCampaigns && viewMode === "logs" && (
              <button
                type="button"
                onClick={() => {
                  setViewMode("create");
                  setEditingCampaign(null);
                  reset(defaultValues);
                }}
                className="rounded-lg border border-pink-300/45 bg-pink-500/15 px-4 py-2 text-sm font-medium text-pink-100 hover:bg-neon-pink/25 hover:text-slate-50"
              >
                Open Create Campaign
              </button>
            )}
          </div>
        </div>
      </section>

      {canManageCampaigns && viewMode === "create" ? (
        <section className="rounded-2xl border border-pink-300/20 bg-matte-850/90 p-5 shadow-neon-ring">
          <h3 className="text-lg font-semibold text-slate-100">{editingCampaign ? "Edit Campaign" : "Create Campaign"}</h3>

          <form className="mt-4 space-y-4" onSubmit={handleSubmit(onSubmit)}>
            <div>
              <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-300">Campaign Title</label>
              <input {...register("title")} placeholder="Campaign Title" className="w-full" />
              {errors.title && <p className="mt-1 text-xs text-rose-300">{errors.title.message}</p>}
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-300">Date</label>
                <input type="date" {...register("scheduled_date")} className="w-full" />
                {errors.scheduled_date && <p className="mt-1 text-xs text-rose-300">{errors.scheduled_date.message}</p>}
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-300">Time</label>
                <input type="time" {...register("scheduled_time")} className="w-full" />
                {errors.scheduled_time && <p className="mt-1 text-xs text-rose-300">{errors.scheduled_time.message}</p>}
              </div>
            </div>

            <div>
              <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-300">Message Body</label>
              <textarea {...register("message_body")} rows={8} placeholder="Campaign Message" className="w-full" />
              {errors.message_body && <p className="mt-1 text-xs text-rose-300">{errors.message_body.message}</p>}
            </div>

            <div className="flex flex-wrap gap-2">
              <button
                type="submit"
                disabled={createMutation.isPending || updateMutation.isPending}
                className="rounded-lg border border-pink-300/45 bg-pink-400/15 px-4 py-2 text-sm text-pink-50 hover:bg-neon-pink/25 hover:text-slate-50"
              >
                {editingCampaign ? "Update" : "Create"}
              </button>
              {editingCampaign && (
                <button
                  type="button"
                  onClick={() => {
                    setEditingCampaign(null);
                    reset(defaultValues);
                  }}
                  className="rounded-lg border border-slate-400/50 px-4 py-2 text-sm text-slate-100"
                >
                  Cancel
                </button>
              )}
            </div>
          </form>
        </section>
      ) : (
        <section className="space-y-6">
          <div className="rounded-2xl border border-pink-300/20 bg-matte-850/90 p-5 shadow-neon-ring">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="text-lg font-semibold text-slate-100">Campaign Logs & Details</h3>
                <p className="text-sm text-slate-300">Search campaigns, open details, and inspect send logs.</p>
              </div>

              <input
                value={search}
                onChange={(event) => {
                  setSearch(event.target.value);
                  setPage(1);
                }}
                placeholder="Search campaigns"
                className="w-full max-w-xs"
              />
            </div>

            <div className="mb-4 flex flex-wrap gap-2 text-xs">
              <button
                onClick={() => {
                  setStatusFilter("all");
                  setPage(1);
                }}
                className={`rounded-md border px-3 py-1 ${
                  statusFilter === "all"
                    ? "border-pink-300/45 bg-pink-400/15 text-pink-50"
                    : "border-pink-300/20 text-slate-200"
                }`}
              >
                All
              </button>
              {(["draft", "scheduled", "running", "completed", "failed", "cancelled"] as CampaignStatus[]).map((status) => (
                <button
                  key={status}
                  onClick={() => {
                    setStatusFilter(status);
                    setPage(1);
                  }}
                  className={`rounded-md border px-3 py-1 ${
                    statusFilter === status
                      ? "border-pink-300/45 bg-pink-400/15 text-pink-50"
                      : "border-pink-300/20 text-slate-200"
                  }`}
                >
                  {status.toUpperCase()}
                </button>
              ))}
            </div>

            {campaignListQuery.isLoading && <p className="text-sm text-slate-200">Loading campaigns...</p>}
            {campaignListQuery.isError && <p className="text-sm text-rose-200">{getErrorMessage(campaignListQuery.error)}</p>}

            {campaignListQuery.data && campaignListQuery.data.items.length === 0 && (
              <p className="rounded-lg border border-dashed border-slate-600 p-6 text-center text-sm text-slate-200">
                No campaigns found.
              </p>
            )}

            {campaignListQuery.data && campaignListQuery.data.items.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[980px] text-left text-sm">
                  <thead className="border-b border-pink-300/20 text-xs uppercase tracking-wide text-slate-300">
                    <tr>
                      <th className="py-3 pr-3">Title</th>
                      <th className="py-3 pr-3">Scheduled</th>
                      <th className="py-3 pr-3">Status</th>
                      <th className="py-3 pr-3">Targeted</th>
                      <th className="py-3 pr-3">Sent</th>
                      <th className="py-3 pr-3">Failed</th>
                      <th className="py-3 pr-3">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {campaignListQuery.data.items.map((campaign) => (
                      <tr key={campaign.id} className="border-b border-slate-700/60 text-slate-100">
                        <td className="py-3 pr-3 font-medium text-pink-100">{campaign.title}</td>
                        <td className="py-3 pr-3">{new Date(campaign.scheduled_at).toLocaleString()}</td>
                        <td className="py-3 pr-3">
                          <span className={`rounded px-2 py-1 text-xs ${statusClassName(campaign.status)}`}>
                            {campaign.status.toUpperCase()}
                          </span>
                        </td>
                        <td className="py-3 pr-3">{campaign.total_customers_targeted}</td>
                        <td className="py-3 pr-3">{campaign.total_sent}</td>
                        <td className="py-3 pr-3">{campaign.total_failed}</td>
                        <td className="py-3 pr-3">
                          <div className="flex flex-wrap gap-2">
                            {canManageCampaigns && (
                              <button
                                type="button"
                                onClick={() => {
                                  setViewMode("create");
                                  setEditingCampaign(campaign);
                                }}
                                className="rounded-md border border-amber-400/30 px-2 py-1 text-xs text-amber-200"
                              >
                                Edit
                              </button>
                            )}
                            {canManageCampaigns && (
                              <button
                                type="button"
                                onClick={() => scheduleMutation.mutate(campaign.id)}
                                className="rounded-md border border-pink-300/45 px-2 py-1 text-xs text-pink-100"
                              >
                                Schedule
                              </button>
                            )}
                            <button
                              type="button"
                              onClick={() => setSelectedCampaign(campaign)}
                              className="rounded-md border border-emerald-400/35 px-2 py-1 text-xs text-emerald-200"
                            >
                              View Logs
                            </button>
                            {canManageCampaigns && (
                              <button
                                type="button"
                                onClick={() => {
                                  if (window.confirm(`Delete campaign ${campaign.title}?`)) {
                                    deleteMutation.mutate(campaign.id);
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

            <div className="mt-4 flex items-center justify-between text-xs text-slate-300">
              <span>
                Page {page} of {totalPages}
              </span>
              <div className="flex flex-wrap gap-2">
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
          </div>

          <div className="rounded-2xl border border-pink-300/20 bg-matte-850/90 p-5 shadow-neon-ring">
            <h3 className="text-lg font-semibold text-slate-100">Selected Campaign Details</h3>
            {selectedCampaign === null && <p className="mt-2 text-sm text-slate-300">Choose a campaign and click View Logs.</p>}

            {selectedCampaign !== null && (
              <div className="mt-3 grid gap-2 text-sm text-slate-200 sm:grid-cols-2 lg:grid-cols-4">
                <div className="rounded-lg border border-pink-300/20 bg-matte-900/60 p-3">
                  <p className="text-xs uppercase tracking-wide text-slate-300">Title</p>
                  <p className="mt-1 font-medium text-pink-100">{selectedCampaign.title}</p>
                </div>
                <div className="rounded-lg border border-pink-300/20 bg-matte-900/60 p-3">
                  <p className="text-xs uppercase tracking-wide text-slate-300">Scheduled</p>
                  <p className="mt-1">{new Date(selectedCampaign.scheduled_at).toLocaleString()}</p>
                </div>
                <div className="rounded-lg border border-pink-300/20 bg-matte-900/60 p-3">
                  <p className="text-xs uppercase tracking-wide text-slate-300">Status</p>
                  <p className="mt-1">{selectedCampaign.status.toUpperCase()}</p>
                </div>
                <div className="rounded-lg border border-pink-300/20 bg-matte-900/60 p-3">
                  <p className="text-xs uppercase tracking-wide text-slate-300">Sent / Failed</p>
                  <p className="mt-1">{selectedCampaign.total_sent} / {selectedCampaign.total_failed}</p>
                </div>
              </div>
            )}

            {logsQuery.isLoading && selectedCampaign !== null && <p className="mt-3 text-sm text-slate-200">Loading logs...</p>}
            {logsQuery.isError && <p className="mt-3 text-sm text-rose-200">{getErrorMessage(logsQuery.error)}</p>}

            {logsQuery.data && logsQuery.data.items.length === 0 && (
              <p className="mt-3 text-sm text-slate-300">No logs available yet for this campaign.</p>
            )}

            {logsQuery.data && logsQuery.data.items.length > 0 && (
              <div className="mt-3 max-h-[360px] overflow-auto">
                <table className="w-full min-w-[620px] text-left text-xs">
                  <thead className="border-b border-pink-300/20 uppercase tracking-wide text-slate-300">
                    <tr>
                      <th className="py-2 pr-2">Recipient</th>
                      <th className="py-2 pr-2">Status</th>
                      <th className="py-2 pr-2">Provider ID</th>
                      <th className="py-2 pr-2">Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {logsQuery.data.items.map((log) => (
                      <tr key={log.id} className="border-b border-slate-700/60 text-slate-100">
                        <td className="py-2 pr-2">{log.recipient_whatsapp_no}</td>
                        <td className="py-2 pr-2">
                          <span
                            className={`rounded px-2 py-1 ${
                              log.send_status === "sent" ? "bg-emerald-500/15 text-emerald-200" : "bg-rose-500/15 text-rose-200"
                            }`}
                          >
                            {log.send_status.toUpperCase()}
                          </span>
                        </td>
                        <td className="py-2 pr-2">{log.provider_message_id || "-"}</td>
                        <td className="py-2 pr-2">{new Date(log.attempted_at).toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>
      )}
    </div>
  );
}
