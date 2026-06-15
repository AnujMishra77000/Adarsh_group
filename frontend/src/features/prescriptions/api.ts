import apiClient from "@/lib/api";
import type { PaginatedResponse } from "@/types/common";
import type {
  Prescription,
  PrescriptionPayload,
  PrescriptionPdfResponse,
  PrescriptionSendVendorPayload,
  PrescriptionSendVendorResponse
} from "@/types/prescription";

export type PrescriptionListParams = {
  page?: number;
  page_size?: number;
  customer_id?: number;
  customer_business_id?: string;
  contact_no?: string;
};

export async function listPrescriptions(params: PrescriptionListParams): Promise<PaginatedResponse<Prescription>> {
  const response = await apiClient.get<PaginatedResponse<Prescription>>("/prescriptions", { params });
  return response.data;
}

export async function listPrescriptionsByCustomer(customerId: number): Promise<Prescription[]> {
  const response = await apiClient.get<Prescription[]>(`/prescriptions/customer/${customerId}`);
  return response.data;
}

export async function createPrescription(payload: PrescriptionPayload): Promise<Prescription> {
  const response = await apiClient.post<Prescription>("/prescriptions", payload);
  return response.data;
}

export async function updatePrescription(
  prescriptionId: number,
  payload: Partial<PrescriptionPayload>
): Promise<Prescription> {
  const response = await apiClient.put<Prescription>(`/prescriptions/${prescriptionId}`, payload);
  return response.data;
}

export async function deletePrescription(prescriptionId: number): Promise<{ message: string }> {
  const response = await apiClient.delete<{ message: string }>(`/prescriptions/${prescriptionId}`);
  return response.data;
}

export async function generatePrescriptionPdf(prescriptionId: number): Promise<PrescriptionPdfResponse> {
  const response = await apiClient.post<PrescriptionPdfResponse>(`/prescriptions/${prescriptionId}/pdf`);
  return response.data;
}

export async function sendPrescriptionToVendor(
  prescriptionId: number,
  payload: PrescriptionSendVendorPayload
): Promise<PrescriptionSendVendorResponse> {
  const response = await apiClient.post<PrescriptionSendVendorResponse>(
    `/prescriptions/${prescriptionId}/send-vendor`,
    payload
  );
  return response.data;
}
