import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { getCustomer, listCustomers } from "@/features/customers/api";
import { CustomerRecordsPage } from "@/pages/customers/CustomerRecordsPage";
import { renderWithProviders } from "@/test/render";

vi.mock("@/features/auth/useCurrentUser", () => ({
  useCurrentUser: () => ({ data: { role: "admin" } })
}));
vi.mock("@/features/customers/api", () => ({
  listCustomers: vi.fn(),
  getCustomer: vi.fn(),
  deleteCustomer: vi.fn()
}));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const customer = {
  id: 4,
  customer_id: "CUST-20260617-000001",
  name: "Riya Shah",
  age: 31,
  contact_no: "9876500100",
  email: null,
  whatsapp_no: null,
  gender: "female",
  occupation: null,
  guardian_name: null,
  guardian_contact_no: null,
  address: null,
  purpose_of_visit: null,
  whatsapp_opt_in: false,
  created_at: "2026-06-17T11:00:00Z",
  updated_at: "2026-06-17T11:00:00Z",
  created_by: 2,
  updated_by: 2,
  is_deleted: false
} as const;

describe("CustomerRecordsPage contact-lens history", () => {
  it("shows contact-lens orders and scheduled follow-ups with visit navigation", async () => {
    vi.mocked(listCustomers).mockResolvedValue({ items: [customer], total: 1, page: 1, page_size: 10 });
    vi.mocked(getCustomer).mockResolvedValue({
      ...customer,
      visits: [{
        id: 12,
        visit_date: "2026-06-18T10:00:00Z",
        reason_for_visit: "Contact lens fitting",
        referred_by: null,
        status: "in_progress",
        assigned_examiner_id: 2,
        visit_notes: null,
        created_at: "2026-06-18T10:00:00Z"
      }],
      referrals: [],
      prescriptions: [],
      bills: [],
      contact_lens_orders: [{
        id: 52,
        visit_id: 12,
        order_reference: "CL-20260618-ABCD1234",
        status: "ready_for_vendor",
        vendor_id: null,
        created_at: "2026-06-18T11:00:00Z"
      }],
      follow_up_tasks: [{
        id: 61,
        visit_id: 12,
        contact_lens_order_id: 52,
        task_type: "contact_lens_review",
        due_date: "2026-06-25",
        status: "pending",
        notes: "Check comfort",
        completed_at: null
      }],
      dispensing_orders: [],
      timeline: [
        {
          event: "visit",
          occurred_at: "2026-06-18T10:00:00Z",
          label: "Visit: Contact lens fitting",
          visit_id: 12,
          entity_type: "visit",
          entity_id: 12,
          status: "in_progress",
          user_id: 2,
          notes: null,
          previous_status: null
        },
        {
          event: "follow_up_scheduled",
          occurred_at: "2026-06-18T11:15:00Z",
          label: "Contact lens follow-up scheduled",
          visit_id: 12,
          entity_type: "follow_up",
          entity_id: 61,
          status: "pending",
          user_id: 2,
          notes: "Check comfort",
          previous_status: null
        }
      ]
    } as never);

    renderWithProviders(<CustomerRecordsPage />, { route: "/crm/customers/records" });

    expect(await screen.findByRole("heading", { name: /contact lens orders/i })).toBeInTheDocument();
    expect(screen.getByText("CL-20260618-ABCD1234")).toBeInTheDocument();
    expect(screen.getByText(/ready for vendor/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /follow-up tasks/i })).toBeInTheDocument();
    expect(screen.getAllByText(/check comfort/i)).toHaveLength(2);
    expect(screen.getByRole("heading", { name: /patient timeline/i })).toBeInTheDocument();
    expect(screen.getByText(/contact lens follow-up scheduled/i)).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /continue visit/i }).length).toBeGreaterThan(0);
  });
});
