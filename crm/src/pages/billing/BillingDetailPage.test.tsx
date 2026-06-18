import { screen } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { getBill } from "@/features/bills/api";
import { CRM_PATHS } from "@/lib/routes";
import { BillingDetailPage } from "@/pages/billing/BillingDetailPage";
import { renderWithProviders } from "@/test/render";

vi.mock("@/features/bills/api", () => ({
  downloadBillPdf: vi.fn(),
  generateBillPdf: vi.fn(),
  getBill: vi.fn(),
  getBillPdfPreviewUrl: vi.fn(),
  sendBillEmail: vi.fn(),
  sendBillWhatsapp: vi.fn()
}));

vi.mock("@/features/auth/useCurrentUser", () => ({
  useCurrentUser: () => ({
    data: { role: "admin" },
    isLoading: false,
    isError: false
  })
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn()
  }
}));

const mockedGetBill = vi.mocked(getBill);

describe("BillingDetailPage", () => {
  it("renders API errors for failed bill lookups", async () => {
    mockedGetBill.mockRejectedValue(new Error("Bill not found"));

    renderWithProviders(
      <Routes>
        <Route path={`${CRM_PATHS.billing}/view/:billId`} element={<BillingDetailPage />} />
      </Routes>,
      { route: `${CRM_PATHS.billing}/view/999` }
    );

    expect(await screen.findByText("Bill not found")).toBeInTheDocument();
  });

  it("returns to a validated CRM visit supplied by the billing handoff", async () => {
    mockedGetBill.mockResolvedValue({
      id: 71,
      bill_number: "BILL-20260618-0071",
      customer_name_snapshot: "Riya Shah",
      customer_business_id: "CUST-20260617-000001",
      customer_contact_no: "9876500100",
      grand_total: 4800,
      paid_total: 2000,
      balance_amount: 2800,
      payment_status: "partial",
      delivery_date: null,
      created_at: "2026-06-18T11:00:00Z",
      updated_at: "2026-06-18T11:00:00Z",
      notes: null,
      items: [],
      payments: [],
      subtotal: 5000,
      discount_total: 200,
      tax_total: 0,
      pdf_url: null
    } as never);

    const { user } = renderWithProviders(
      <Routes>
        <Route path={`${CRM_PATHS.billing}/view/:billId`} element={<BillingDetailPage />} />
        <Route path={`${CRM_PATHS.visitWorkspace}/:visitId`} element={<h1>Returned Visit</h1>} />
      </Routes>,
      { route: `${CRM_PATHS.billing}/view/71?return_to=${encodeURIComponent(`${CRM_PATHS.visitWorkspace}/12`)}` }
    );

    await screen.findByRole("heading", { name: /BILL-20260618-0071/ });
    await user.click(screen.getByRole("button", { name: "Back" }));
    expect(await screen.findByRole("heading", { name: "Returned Visit" })).toBeInTheDocument();
  });
});
