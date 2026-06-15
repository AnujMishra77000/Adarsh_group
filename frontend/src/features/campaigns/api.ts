import apiClient from "@/lib/api";
import type { Campaign, CampaignLog, CampaignPayload, CampaignScheduleResponse, CampaignStatus } from "@/types/campaign";
import type { PaginatedResponse } from "@/types/common";

export type CampaignListParams = {
  page?: number;
  page_size?: number;
  search?: string;
  status?: CampaignStatus;
};

export async function listCampaigns(params: CampaignListParams): Promise<PaginatedResponse<Campaign>> {
  const response = await apiClient.get<PaginatedResponse<Campaign>>("/campaigns", { params });
  return response.data;
}

export async function createCampaign(payload: CampaignPayload): Promise<Campaign> {
  const response = await apiClient.post<Campaign>("/campaigns", payload);
  return response.data;
}

export async function getCampaign(campaignId: number): Promise<Campaign> {
  const response = await apiClient.get<Campaign>(`/campaigns/${campaignId}`);
  return response.data;
}

export async function updateCampaign(campaignId: number, payload: Partial<CampaignPayload>): Promise<Campaign> {
  const response = await apiClient.put<Campaign>(`/campaigns/${campaignId}`, payload);
  return response.data;
}

export async function deleteCampaign(campaignId: number): Promise<{ message: string }> {
  const response = await apiClient.delete<{ message: string }>(`/campaigns/${campaignId}`);
  return response.data;
}

export async function scheduleCampaign(campaignId: number): Promise<CampaignScheduleResponse> {
  const response = await apiClient.post<CampaignScheduleResponse>(`/campaigns/${campaignId}/schedule`);
  return response.data;
}

export async function getCampaignLogs(
  campaignId: number,
  page = 1,
  pageSize = 20
): Promise<PaginatedResponse<CampaignLog>> {
  const response = await apiClient.get<PaginatedResponse<CampaignLog>>(`/campaigns/${campaignId}/logs`, {
    params: { page, page_size: pageSize }
  });
  return response.data;
}
