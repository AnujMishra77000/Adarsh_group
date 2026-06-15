import apiClient from "@/lib/api";
import type { PaginatedResponse } from "@/types/common";
import type { StaffCreatePayload, StaffLoginActivity, StaffUser } from "@/types/staff";

type ListStaffParams = {
  page?: number;
  page_size?: number;
  search?: string;
  is_active?: boolean;
};

type ListActivityParams = {
  page?: number;
  page_size?: number;
  staff_user_id?: number;
};

export async function listStaff(params: ListStaffParams): Promise<PaginatedResponse<StaffUser>> {
  const response = await apiClient.get<PaginatedResponse<StaffUser>>("/staff", { params });
  return response.data;
}

export async function createStaff(payload: StaffCreatePayload): Promise<StaffUser> {
  const response = await apiClient.post<StaffUser>("/staff", payload);
  return response.data;
}

export async function deleteStaff(staffUserId: number): Promise<{ message: string }> {
  const response = await apiClient.delete<{ message: string }>(`/staff/${staffUserId}`);
  return response.data;
}

export async function listStaffLoginActivities(params: ListActivityParams): Promise<PaginatedResponse<StaffLoginActivity>> {
  const response = await apiClient.get<PaginatedResponse<StaffLoginActivity>>("/staff/login-activities", { params });
  return response.data;
}
