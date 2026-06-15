import apiClient from "@/lib/api";
import type { Bill, BillPayload } from "@/types/bill";
import type { PaginatedResponse } from "@/types/common";

export type BillListParams = {
  page?: number;
  page_size?: number;
  search?: string;
  customer_id?: number;
};

export async function listBills(params: BillListParams): Promise<PaginatedResponse<Bill>> {
  const response = await apiClient.get<PaginatedResponse<Bill>>("/bills", { params });
  return response.data;
}

export async function getBill(billId: number): Promise<Bill> {
  const response = await apiClient.get<Bill>(`/bills/${billId}`);
  return response.data;
}

export async function createBill(payload: BillPayload): Promise<Bill> {
  const response = await apiClient.post<Bill>("/bills", payload);
  return response.data;
}

export async function updateBill(billId: number, payload: Partial<BillPayload>): Promise<Bill> {
  const response = await apiClient.put<Bill>(`/bills/${billId}`, payload);
  return response.data;
}

export async function deleteBill(billId: number): Promise<{ message: string }> {
  const response = await apiClient.delete<{ message: string }>(`/bills/${billId}`);
  return response.data;
}

export async function generateBillPdf(billId: number): Promise<Bill> {
  const response = await apiClient.post<Bill>(`/bills/${billId}/generate-pdf`);
  return response.data;
}

export async function sendBillEmail(billId: number): Promise<{ message: string }> {
  const response = await apiClient.post<{ message: string }>(`/bills/${billId}/send-email`);
  return response.data;
}

export async function sendBillWhatsapp(billId: number): Promise<{ message: string }> {
  const response = await apiClient.post<{ message: string }>(`/bills/${billId}/send-whatsapp`);
  return response.data;
}
