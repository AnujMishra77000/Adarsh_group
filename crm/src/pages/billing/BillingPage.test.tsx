import { screen, waitFor } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { createBill } from "@/features/bills/api";
import { searchCustomers } from "@/features/customers/api";
import { getContactLensContext, getDispensingOrderContext } from "@/features/visits/api";
import { CRM_PATHS } from "@/lib/routes";
import { BillingPage } from "@/pages/billing/BillingPage";
import { renderWithProviders } from "@/test/render";

vi.mock("@/features/bills/api", () => ({ createBill: vi.fn() }));
vi.mock("@/features/customers/api", () => ({ searchCustomers: vi.fn() }));
vi.mock("@/features/visits/api", () => ({ getDispensingOrderContext: vi.fn(), getContactLensContext: vi.fn() }));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const mockedCreateBill = vi.mocked(createBill);
const mockedSearchCustomers = vi.mocked(searchCustomers);
const mockedGetDispensingOrderContext = vi.mocked(getDispensingOrderContext);
const mockedGetContactLensContext = vi.mocked(getContactLensContext);

describe("BillingPage workflow context", () => {
  it("prefills order items and creates the official bill with visit and order references", async () => {
    mockedSearchCustomers.mockResolvedValue({
      items: [{
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
      }],
      total: 1,
      page: 1,
      page_size: 15
    });
    mockedGetDispensingOrderContext.mockResolvedValue({
      visit_id: 12,
      current_prescription_id: 31,
      current_prescription_version_number: 1,
      is_prescription_stale: false,
      order: {
        id: 41,
        visit_id: 12,
        customer_id: 4,
        prescription_id: 31,
        prescription_version_number: 1,
        vendor_id: 8,
        vendor_name: "Clear View Lab",
        order_reference: "DO-20260618-ABCD1234",
        status: "draft",
        frame: { brand: "Ray-Ban", model_number: "RX-5228" },
        measurements: {},
        lens: { lens_type: "progressive", brand: "Essilor", design: "Varilux Comfort", coating: "Crizal Sapphire" },
        manufacturing_instructions: "Verify centration before edging.",
        has_vendor_document: false,
        sent_by: null,
        sent_at: null,
        created_by: 2,
        updated_by: 2,
        created_at: "2026-06-18T11:00:00Z",
        updated_at: "2026-06-18T11:00:00Z"
      }
    });
    mockedCreateBill.mockResolvedValue({
      id: 71,
      bill_number: "BILL-20260618-0071",
      visit_id: 12,
      dispensing_order_id: 41,
      pdf_url: null
    } as never);

    const returnTo = `${CRM_PATHS.visitWorkspace}/12`;
    const route = `${CRM_PATHS.billing}?${new URLSearchParams({
      customer_id: "4",
      customer_query: "CUST-20260617-000001",
      visit_id: "12",
      dispensing_order_id: "41",
      return_to: returnTo
    }).toString()}`;
    const { user } = renderWithProviders(
      <Routes>
        <Route path={CRM_PATHS.billing} element={<BillingPage />} />
        <Route path={`${CRM_PATHS.billing}/view/:billId`} element={<h1>Created Bill Detail</h1>} />
      </Routes>,
      { route }
    );

    expect(await screen.findByDisplayValue("Ray-Ban RX-5228")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Progressive · Essilor · Varilux Comfort")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Crizal Sapphire")).toBeInTheDocument();

    const unitPrices = screen.getAllByPlaceholderText("Unit price");
    for (const input of unitPrices) {
      await user.clear(input);
      await user.type(input, "1000");
    }
    await user.click(screen.getByRole("button", { name: /generate bill/i }));

    await waitFor(() => expect(mockedCreateBill).toHaveBeenCalledTimes(1));
    expect(mockedCreateBill.mock.calls[0][0]).toEqual(expect.objectContaining({
      customer_id: 4,
      visit_id: 12,
      dispensing_order_id: 41,
      items: expect.arrayContaining([
        expect.objectContaining({ item_type: "frame", item_name: "Ray-Ban RX-5228" }),
        expect.objectContaining({ item_type: "lens", item_name: "Progressive · Essilor · Varilux Comfort" }),
        expect.objectContaining({ item_type: "coating", item_name: "Crizal Sapphire" })
      ])
    }));
    expect(await screen.findByRole("heading", { name: "Created Bill Detail" })).toBeInTheDocument();
  });

  it("prefills one Contact Lens item and submits the contact-lens order reference", async () => {
    mockedGetContactLensContext.mockResolvedValue({
      visit_id: 12,
      is_activated: true,
      workup: null,
      order: {
        id: 52,
        visit_id: 12,
        customer_id: 4,
        vendor_id: null,
        vendor_name: null,
        order_reference: "CL-20260618-ABCD1234",
        status: "draft",
        workup_snapshot: {},
        lens_details: {
          brand: "Acuvue Oasys",
          material: "Senofilcon A",
          replacement_schedule: "Fortnightly",
          wearing_schedule: "Daily wear"
        },
        order_notes: null,
        created_by: 2,
        updated_by: 2,
        created_at: "2026-06-18T11:00:00Z",
        updated_at: "2026-06-18T11:00:00Z"
      },
      follow_up: null,
      active_bill_id: null
    });
    mockedCreateBill.mockResolvedValue({
      id: 72,
      bill_number: "BILL-20260618-0072",
      visit_id: 12,
      dispensing_order_id: null,
      contact_lens_order_id: 52,
      pdf_url: null
    } as never);

    const route = `${CRM_PATHS.billing}?${new URLSearchParams({
      customer_id: "4",
      customer_query: "CUST-20260617-000001",
      visit_id: "12",
      contact_lens_order_id: "52",
      return_to: `${CRM_PATHS.visitWorkspace}/12`
    }).toString()}`;
    const { user } = renderWithProviders(
      <Routes>
        <Route path={CRM_PATHS.billing} element={<BillingPage />} />
        <Route path={`${CRM_PATHS.billing}/view/:billId`} element={<h1>Created Bill Detail</h1>} />
      </Routes>,
      { route }
    );

    expect(await screen.findByDisplayValue("Acuvue Oasys · Senofilcon A · Fortnightly")).toBeInTheDocument();
    const price = screen.getByPlaceholderText("Unit price");
    await user.clear(price);
    await user.type(price, "2500");
    await user.click(screen.getByRole("button", { name: /generate bill/i }));

    await waitFor(() => expect(mockedCreateBill).toHaveBeenCalledTimes(1));
    expect(mockedCreateBill.mock.calls[0][0]).toEqual(expect.objectContaining({
      customer_id: 4,
      visit_id: 12,
      dispensing_order_id: null,
      contact_lens_order_id: 52,
      items: [expect.objectContaining({ item_type: "contact_lens", quantity: 1, unit_price: 2500 })]
    }));
  });
});
