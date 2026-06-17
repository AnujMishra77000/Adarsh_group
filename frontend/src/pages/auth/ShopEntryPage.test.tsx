import { screen, waitFor } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { resolveShop } from "@/features/shops/api";
import { CRM_PATHS } from "@/lib/routes";
import { ShopEntryPage } from "@/pages/auth/ShopEntryPage";
import { renderWithProviders } from "@/test/render";

vi.mock("@/features/shops/api", () => ({
  resolveShop: vi.fn()
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn()
  }
}));

const mockedResolveShop = vi.mocked(resolveShop);

describe("ShopEntryPage", () => {
  beforeEach(() => {
    mockedResolveShop.mockReset();
  });

  it("stores the selected shop only after the backend resolver accepts the identifier", async () => {
    mockedResolveShop.mockResolvedValue({
      code: "adarsh-eye-boutique",
      display_name: "Adarsh Eye Boutique",
      location_label: "",
      center_type: "Eye boutique"
    });

    const { user } = renderWithProviders(
      <Routes>
        <Route path={CRM_PATHS.shopEntry} element={<ShopEntryPage />} />
        <Route path={`${CRM_PATHS.shopResolver}/adarsh-eye-boutique`} element={<div>Resolved shop route</div>} />
      </Routes>,
      { route: CRM_PATHS.shopEntry }
    );

    await user.type(screen.getByLabelText(/shop identifier/i), " 9876543210 ");
    await user.click(screen.getByRole("button", { name: /continue to shop crm/i }));

    await waitFor(() => {
      expect(mockedResolveShop).toHaveBeenCalled();
    });
    expect(mockedResolveShop.mock.calls[0][0]).toEqual({ identifier: "9876543210" });
    expect(sessionStorage.getItem("eye_boutique_active_shop_key")).toBe("adarsh-eye-boutique");
    expect(await screen.findByText("Resolved shop route")).toBeInTheDocument();
  });

  it("rejects an empty shop identifier before calling the API", async () => {
    const { user } = renderWithProviders(<ShopEntryPage />, { route: CRM_PATHS.shopEntry });

    await user.click(screen.getByRole("button", { name: /continue to shop crm/i }));

    expect(mockedResolveShop).not.toHaveBeenCalled();
  });
});
