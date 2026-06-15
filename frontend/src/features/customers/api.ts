import apiClient from "@/lib/api";
import type { PaginatedResponse } from "@/types/common";
import type { Customer, CustomerDetail, CustomerPayload } from "@/types/customer";

export type CustomerListParams = {
  page?: number;
  page_size?: number;
  search?: string;
};

export async function listCustomers(params: CustomerListParams): Promise<PaginatedResponse<Customer>> {
  const response = await apiClient.get<PaginatedResponse<Customer>>("/customers", { params });
  return response.data;
}

export async function searchCustomers(query: string, page = 1, pageSize = 20): Promise<PaginatedResponse<Customer>> {
  const response = await apiClient.get<PaginatedResponse<Customer>>("/customers/search", {
    params: { q: query, page, page_size: pageSize }
  });
  return response.data;
}

export async function getCustomer(customerId: number): Promise<CustomerDetail> {
  const response = await apiClient.get<CustomerDetail>(`/customers/${customerId}`);
  return response.data;
}

export async function createCustomer(payload: CustomerPayload): Promise<Customer> {
  const response = await apiClient.post<Customer>("/customers", payload);
  return response.data;
}

export async function updateCustomer(customerId: number, payload: Partial<CustomerPayload>): Promise<Customer> {
  const response = await apiClient.put<Customer>(`/customers/${customerId}`, payload);
  return response.data;
}

export async function deleteCustomer(customerId: number): Promise<{ message: string }> {
  const response = await apiClient.delete<{ message: string }>(`/customers/${customerId}`);
  return response.data;
}
