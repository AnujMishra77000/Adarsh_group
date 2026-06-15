import apiClient from "@/lib/api";
import type { PaginatedResponse } from "@/types/common";
import type { Vendor, VendorPayload } from "@/types/vendor";

export type VendorListParams = {
  page?: number;
  page_size?: number;
  search?: string;
  is_active?: boolean;
};

export async function listVendors(params: VendorListParams): Promise<PaginatedResponse<Vendor>> {
  const response = await apiClient.get<PaginatedResponse<Vendor>>("/vendors", { params });
  return response.data;
}

export async function createVendor(payload: VendorPayload): Promise<Vendor> {
  const response = await apiClient.post<Vendor>("/vendors", payload);
  return response.data;
}

export async function updateVendor(vendorId: number, payload: Partial<VendorPayload>): Promise<Vendor> {
  const response = await apiClient.put<Vendor>(`/vendors/${vendorId}`, payload);
  return response.data;
}

export async function deleteVendor(vendorId: number): Promise<{ message: string }> {
  const response = await apiClient.delete<{ message: string }>(`/vendors/${vendorId}`);
  return response.data;
}
