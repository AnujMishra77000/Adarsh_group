export type RevenueRange = "today" | "last_7_days" | "last_30_days";

export type DashboardSummary = {
  total_customers: number;
  today_customers: number;
  total_prescriptions: number;
  bills_generated_today: number;
  revenue_today: number;
  scheduled_campaigns: number;
  failed_whatsapp_jobs: number;
};

export type RevenueSummary = {
  range_key: RevenueRange;
  total_revenue: number;
  total_bills: number;
  average_bill_value: number;
};

export type RevenueTimeseriesPoint = {
  label: string;
  value: number;
};

export type RevenueTimeseries = {
  range_key: RevenueRange;
  points: RevenueTimeseriesPoint[];
};
