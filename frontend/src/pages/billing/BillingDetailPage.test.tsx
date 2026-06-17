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
});
