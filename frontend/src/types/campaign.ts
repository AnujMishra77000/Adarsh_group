export type CampaignStatus = "draft" | "scheduled" | "running" | "completed" | "failed" | "cancelled";

export type Campaign = {
  id: number;
  title: string;
  message_body: string;
  scheduled_at: string;
  status: CampaignStatus;
  total_customers_targeted: number;
  total_sent: number;
  total_failed: number;
  created_by: number | null;
  updated_by: number | null;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
};

export type CampaignPayload = {
  title: string;
  message_body: string;
  scheduled_at: string;
};

export type CampaignScheduleResponse = {
  message: string;
  campaign: Campaign;
};

export type CampaignLog = {
  id: number;
  campaign_id: number;
  customer_id: number | null;
  recipient_whatsapp_no: string;
  send_status: string;
  provider_message_id: string | null;
  error_message: string | null;
  attempted_at: string;
};
