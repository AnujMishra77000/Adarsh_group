import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { StatCard } from "@/components/ui/StatCard";
import { useCurrentUser } from "@/features/auth/useCurrentUser";
import { getDashboardSummary, getRevenueTimeseries } from "@/features/analytics/api";
import { getErrorMessage } from "@/lib/errors";
import type { RevenueRange } from "@/types/analytics";

const GRAPH_PURPLE = "#6b2fa3";

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
    minimumFractionDigits: 2
  }).format(value);
}

export function DashboardPage() {
  const [range, setRange] = useState<RevenueRange>("last_7_days");

  const currentUserQuery = useCurrentUser();
  const canViewRevenue = currentUserQuery.data?.role === "admin";

  const summaryQuery = useQuery({
    queryKey: ["analytics-dashboard-summary"],
    queryFn: getDashboardSummary
  });

  const revenueQuery = useQuery({
    queryKey: ["analytics-dashboard-revenue", range],
    queryFn: () => getRevenueTimeseries(range),
    enabled: canViewRevenue
  });

  const summaryStats = useMemo(() => {
    const data = summaryQuery.data;
    const baseStats = [
      { label: "Total Customers", value: data ? String(data.total_customers) : "-", hint: "All-time" },
      { label: "Today Customers", value: data ? String(data.today_customers) : "-", hint: "Current day" },
      { label: "Total Prescriptions", value: data ? String(data.total_prescriptions) : "-", hint: "All records" },
      { label: "Bills Today", value: data ? String(data.bills_generated_today) : "-", hint: "Generated today" },
      {
        label: "Scheduled Campaigns",
        value: data ? String(data.scheduled_campaigns) : "-",
        hint: "Upcoming"
      },
      {
        label: "Failed WhatsApp Jobs",
        value: data ? String(data.failed_whatsapp_jobs) : "-",
        hint: "Needs retry"
      }
    ];

    if (!canViewRevenue) {
      return baseStats;
    }

    return [
      ...baseStats.slice(0, 4),
      {
        label: "Revenue Today",
        value: data ? formatCurrency(data.revenue_today) : "-",
        hint: "Confirmed billing"
      },
      ...baseStats.slice(4)
    ];
  }, [summaryQuery.data, canViewRevenue]);

  const revenuePoints = revenueQuery.data?.points ?? [];

  return (
    <div className="space-y-7">
      <section>
        <h2 className="text-xl font-semibold text-slate-100">Operations Dashboard</h2>
        <p className="mt-1 text-sm text-slate-300">Daily KPIs and workflow visibility for the boutique team.</p>
      </section>

      {summaryQuery.isError && (
        <p className="rounded-lg border border-rose-300/30 bg-rose-400/10 p-3 text-sm text-rose-100">
          {getErrorMessage(summaryQuery.error)}
        </p>
      )}

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {summaryStats.map((item) => (
          <StatCard key={item.label} label={item.label} value={item.value} hint={item.hint} />
        ))}
      </section>

      {canViewRevenue ? (
        <section className="rounded-2xl border border-pink-300/20 bg-matte-850/90 p-5 shadow-neon-ring">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="text-base font-semibold text-slate-100">Revenue Trend</h3>
              <p className="text-sm text-slate-300">Time series sourced from confirmed bills.</p>
            </div>
            <div className="flex flex-wrap gap-2 text-xs">
              <button
                onClick={() => setRange("today")}
                className={`rounded-md border px-3 py-1 ${
                  range === "today"
                    ? "border-pink-300/45 bg-pink-400/15 text-pink-50"
                    : "border-pink-300/20 text-slate-200"
                }`}
              >
                Today
              </button>
              <button
                onClick={() => setRange("last_7_days")}
                className={`rounded-md border px-3 py-1 ${
                  range === "last_7_days"
                    ? "border-pink-300/45 bg-pink-400/15 text-pink-50"
                    : "border-pink-300/20 text-slate-200"
                }`}
              >
                Last 7 days
              </button>
              <button
                onClick={() => setRange("last_30_days")}
                className={`rounded-md border px-3 py-1 ${
                  range === "last_30_days"
                    ? "border-pink-300/45 bg-pink-400/15 text-pink-50"
                    : "border-pink-300/20 text-slate-200"
                }`}
              >
                Last 30 days
              </button>
            </div>
          </div>

          {revenueQuery.isError && <p className="text-sm text-rose-200">{getErrorMessage(revenueQuery.error)}</p>}

          <div className="h-64 w-full">
            <ResponsiveContainer>
              <AreaChart data={revenuePoints}>
                <defs>
                  <linearGradient id="dashboardRevenueGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={GRAPH_PURPLE} stopOpacity={0.62} />
                    <stop offset="100%" stopColor={GRAPH_PURPLE} stopOpacity={0.07} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="4 4" stroke="rgba(107, 47, 163, 0.24)" />
                <XAxis dataKey="label" stroke={GRAPH_PURPLE} />
                <YAxis stroke={GRAPH_PURPLE} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#ffeaf6",
                    border: "1px solid rgba(107, 47, 163, 0.45)",
                    borderRadius: 12,
                    color: GRAPH_PURPLE
                  }}
                  itemStyle={{ color: GRAPH_PURPLE }}
                  labelStyle={{ color: GRAPH_PURPLE }}
                  formatter={(value) => formatCurrency(Number(value))}
                />
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke={GRAPH_PURPLE}
                  strokeWidth={2}
                  fill="url(#dashboardRevenueGradient)"
                  dot={{ r: 2, fill: GRAPH_PURPLE, stroke: GRAPH_PURPLE }}
                  activeDot={{ r: 4, fill: GRAPH_PURPLE, stroke: GRAPH_PURPLE }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {revenueQuery.isLoading && <p className="mt-3 text-xs text-slate-300">Refreshing revenue chart...</p>}
        </section>
      ) : (
        <section className="rounded-2xl border border-pink-300/20 bg-matte-850/90 p-5 text-sm text-slate-200 shadow-neon-ring">
          Revenue analytics and revenue graph are visible only for admin login.
        </section>
      )}
    </div>
  );
}
