import { screen } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { setActiveShop } from "@/features/shops/store";
import { setAuthTokens, setCurrentUser } from "@/features/auth/store";
import { CRM_PATHS } from "@/lib/routes";
import { ProtectedRoute } from "@/routes/ProtectedRoute";
import { renderWithProviders } from "@/test/render";
import type { UserProfile } from "@/types/auth";

const currentUser: UserProfile = {
  id: 1,
  email: "staff@example.com",
  full_name: "Staff User",
  shop_key: "adarsh-eye-boutique",
  role: "staff",
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z"
};

vi.mock("@/features/auth/api", () => ({
  fetchMe: vi.fn(async () => currentUser)
}));

describe("ProtectedRoute", () => {
  it("redirects unauthenticated users to the launch page", () => {
    renderWithProviders(
      <Routes>
        <Route
          path="/crm/private"
          element={
            <ProtectedRoute>
              <div>Private CRM</div>
            </ProtectedRoute>
          }
        />
        <Route path={CRM_PATHS.root} element={<div>Launch page</div>} />
      </Routes>,
      { route: "/crm/private" }
    );

    expect(screen.getByText("Launch page")).toBeInTheDocument();
  });

  it("redirects authenticated users away from disallowed role routes", () => {
    setActiveShop("adarsh-eye-boutique");
    setAuthTokens({ access_token: "access-token", refresh_token: "refresh-token", token_type: "bearer" }, "staff");
    setCurrentUser(currentUser, "staff");

    renderWithProviders(
      <Routes>
        <Route
          path="/crm/admin-only"
          element={
            <ProtectedRoute allowedRoles={["admin"]}>
              <div>Admin Only</div>
            </ProtectedRoute>
          }
        />
        <Route path={CRM_PATHS.dashboard} element={<div>Dashboard</div>} />
      </Routes>,
      { route: "/crm/admin-only" }
    );

    expect(screen.getByText("Dashboard")).toBeInTheDocument();
  });
});
