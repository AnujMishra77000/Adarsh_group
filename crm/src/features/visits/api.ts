import apiClient from "@/lib/api";
import type {
  DispensingOrder,
  DispensingOrderContext,
  DispensingOrderDocumentResponse,
  DispensingOrderPayload,
  DispensingOrderSendResponse,
  DispensingOrderStatus,
  ContactLensContext,
  ContactLensFollowUp,
  ContactLensOrder,
  ContactLensOrderPayload,
  ContactLensWorkup,
  ContactLensWorkupPayload,
  FollowUpInterval,
  FollowUpStatus,
  Visit,
  VisitBillingContext,
  VisitExamSection,
  VisitExamSectionHistoryResponse,
  VisitExamSectionListResponse,
  VisitExamSectionPayload,
  VisitListResponse,
  VisitPayload,
  VisitPrescription,
  VisitPrescriptionDraftPayload,
  VisitPrescriptionPdfResponse,
  VisitPrescriptionReview,
  VisitPrescriptionSummary
} from "@/types/visit";
import type { Bill } from "@/types/bill";

export async function createVisit(payload: VisitPayload): Promise<Visit> {
  const response = await apiClient.post<Visit>("/visits", payload);
  return response.data;
}

export async function getVisit(visitId: number): Promise<Visit> {
  const response = await apiClient.get<Visit>(`/visits/${visitId}`);
  return response.data;
}

export async function listCustomerVisits(customerId: number): Promise<VisitListResponse> {
  const response = await apiClient.get<VisitListResponse>(`/visits/customer/${customerId}`);
  return response.data;
}

export async function listVisitExamSections(visitId: number): Promise<VisitExamSectionListResponse> {
  const response = await apiClient.get<VisitExamSectionListResponse>(`/visits/${visitId}/exam-sections`);
  return response.data;
}

export async function listVisitExamSectionHistory(visitId: number): Promise<VisitExamSectionHistoryResponse> {
  const response = await apiClient.get<VisitExamSectionHistoryResponse>(`/visits/${visitId}/exam-section-history`);
  return response.data;
}

export async function saveVisitExamSection(
  visitId: number,
  sectionKey: string,
  payload: VisitExamSectionPayload
): Promise<VisitExamSection> {
  const response = await apiClient.put<VisitExamSection>(`/visits/${visitId}/exam-sections/${sectionKey}`, payload);
  return response.data;
}

export async function getVisitPrescriptionSummary(visitId: number): Promise<VisitPrescriptionSummary> {
  const response = await apiClient.get<VisitPrescriptionSummary>(`/visits/${visitId}/prescriptions`);
  return response.data;
}

export async function saveVisitPrescriptionDraft(
  visitId: number,
  payload: VisitPrescriptionDraftPayload
): Promise<VisitPrescription> {
  const response = await apiClient.put<VisitPrescription>(`/visits/${visitId}/prescriptions/draft`, payload);
  return response.data;
}

export async function getVisitPrescriptionReview(
  visitId: number,
  prescriptionId: number
): Promise<VisitPrescriptionReview> {
  const response = await apiClient.get<VisitPrescriptionReview>(
    `/visits/${visitId}/prescriptions/${prescriptionId}/review`
  );
  return response.data;
}

export async function finalizeVisitPrescription(
  visitId: number,
  prescriptionId: number,
  payload: { confirmed: boolean }
): Promise<VisitPrescription> {
  const response = await apiClient.post<VisitPrescription>(
    `/visits/${visitId}/prescriptions/${prescriptionId}/finalize`,
    payload
  );
  return response.data;
}

export async function createVisitPrescriptionAmendment(
  visitId: number,
  prescriptionId: number
): Promise<VisitPrescription> {
  const response = await apiClient.post<VisitPrescription>(
    `/visits/${visitId}/prescriptions/${prescriptionId}/amend`
  );
  return response.data;
}

export async function generateVisitPrescriptionPdf(visitId: number): Promise<VisitPrescriptionPdfResponse> {
  const response = await apiClient.post<VisitPrescriptionPdfResponse>(`/visits/${visitId}/prescription/pdf`);
  return response.data;
}

export async function completeVisit(visitId: number, payload: { confirmed: boolean }): Promise<Visit> {
  const response = await apiClient.post<Visit>(`/visits/${visitId}/complete`, payload);
  return response.data;
}

export async function getDispensingOrderContext(visitId: number): Promise<DispensingOrderContext> {
  const response = await apiClient.get<DispensingOrderContext>(`/visits/${visitId}/dispensing-order`);
  return response.data;
}

export async function saveDispensingOrder(
  visitId: number,
  payload: DispensingOrderPayload
): Promise<DispensingOrder> {
  const response = await apiClient.put<DispensingOrder>(`/visits/${visitId}/dispensing-order`, payload);
  return response.data;
}

export async function relinkDispensingOrderPrescription(visitId: number): Promise<DispensingOrder> {
  const response = await apiClient.post<DispensingOrder>(`/visits/${visitId}/dispensing-order/relink-current`);
  return response.data;
}

export async function changeDispensingOrderStatus(
  visitId: number,
  status: DispensingOrderStatus
): Promise<DispensingOrder> {
  const response = await apiClient.post<DispensingOrder>(`/visits/${visitId}/dispensing-order/status`, { status });
  return response.data;
}

export async function generateDispensingOrderVendorDocument(
  visitId: number
): Promise<DispensingOrderDocumentResponse> {
  const response = await apiClient.post<DispensingOrderDocumentResponse>(
    `/visits/${visitId}/dispensing-order/vendor-document`
  );
  return response.data;
}

export async function downloadDispensingOrderVendorDocument(visitId: number): Promise<Blob> {
  const response = await apiClient.get<Blob>(`/visits/${visitId}/dispensing-order/vendor-document/download`, {
    responseType: "blob"
  });
  return response.data;
}

export async function sendDispensingOrderToVendor(
  visitId: number,
  payload: { caption?: string | null } = {}
): Promise<DispensingOrderSendResponse> {
  const response = await apiClient.post<DispensingOrderSendResponse>(
    `/visits/${visitId}/dispensing-order/send-vendor`,
    payload
  );
  return response.data;
}

export async function getVisitBillingContext(visitId: number): Promise<VisitBillingContext> {
  const response = await apiClient.get<VisitBillingContext>(`/visits/${visitId}/billing`);
  return response.data;
}

export async function linkExistingBillToVisit(
  visitId: number,
  payload: { bill_id: number; dispensing_order_id?: number | null; contact_lens_order_id?: number | null }
): Promise<Bill> {
  const response = await apiClient.post<Bill>(`/visits/${visitId}/billing/link`, payload);
  return response.data;
}

export async function getContactLensContext(visitId: number): Promise<ContactLensContext> {
  const response = await apiClient.get<ContactLensContext>(`/visits/${visitId}/contact-lens`);
  return response.data;
}

export async function activateContactLensWorkup(visitId: number): Promise<ContactLensContext> {
  const response = await apiClient.post<ContactLensContext>(`/visits/${visitId}/contact-lens/activate`);
  return response.data;
}

export async function saveContactLensWorkup(
  visitId: number,
  payload: ContactLensWorkupPayload
): Promise<ContactLensWorkup> {
  const response = await apiClient.put<ContactLensWorkup>(`/visits/${visitId}/contact-lens/workup`, payload);
  return response.data;
}

export async function saveContactLensOrder(
  visitId: number,
  payload: ContactLensOrderPayload
): Promise<ContactLensOrder> {
  const response = await apiClient.put<ContactLensOrder>(`/visits/${visitId}/contact-lens/order`, payload);
  return response.data;
}

export async function changeContactLensOrderStatus(
  visitId: number,
  status: DispensingOrderStatus
): Promise<ContactLensOrder> {
  const response = await apiClient.post<ContactLensOrder>(`/visits/${visitId}/contact-lens/order/status`, { status });
  return response.data;
}

export async function scheduleContactLensFollowUp(
  visitId: number,
  payload: { interval: FollowUpInterval; due_date?: string | null; notes?: string | null }
): Promise<ContactLensFollowUp> {
  const response = await apiClient.put<ContactLensFollowUp>(`/visits/${visitId}/contact-lens/follow-up`, payload);
  return response.data;
}

export async function changeContactLensFollowUpStatus(
  visitId: number,
  status: FollowUpStatus
): Promise<ContactLensFollowUp> {
  const response = await apiClient.post<ContactLensFollowUp>(`/visits/${visitId}/contact-lens/follow-up/status`, { status });
  return response.data;
}
