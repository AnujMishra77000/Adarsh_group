import apiClient from "@/lib/api";
import type { DashboardSummary, RevenueRange, RevenueSummary, RevenueTimeseries } from "@/types/analytics";

export async function getDashboardSummary(): Promise<DashboardSummary> {
  const response = await apiClient.get<DashboardSummary>("/analytics/dashboard");
  return response.data;
}

export async function getRevenueSummary(range: RevenueRange): Promise<RevenueSummary> {
  const response = await apiClient.get<RevenueSummary>("/analytics/revenue", {
    params: { range }
  });
  return response.data;
}

export async function getRevenueTimeseries(range: RevenueRange): Promise<RevenueTimeseries> {
  const response = await apiClient.get<RevenueTimeseries>("/analytics/revenue/timeseries", {
    params: { range }
  });
  return response.data;
}
