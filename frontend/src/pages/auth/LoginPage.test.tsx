import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { login } from "@/features/auth/api";
import { CRM_PATHS } from "@/lib/routes";
import { LoginPage } from "@/pages/auth/LoginPage";
import { renderWithProviders } from "@/test/render";

vi.mock("@/features/auth/api", () => ({
  getAuthConfig: vi.fn(async () => ({ admin_registration_enabled: false })),
  login: vi.fn(),
  fetchMe: vi.fn()
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn()
  }
}));

describe("LoginPage", () => {
  it("shows validation errors and does not submit invalid credentials", async () => {
    const { user } = renderWithProviders(<LoginPage mode="admin" />, { route: CRM_PATHS.loginAdmin });

    await user.click(screen.getByRole("button", { name: /sign in as admin/i }));

    expect(await screen.findByText("Enter a valid email")).toBeInTheDocument();
    expect(await screen.findByText("Password must be at least 8 characters")).toBeInTheDocument();
    expect(login).not.toHaveBeenCalled();
  });
});
