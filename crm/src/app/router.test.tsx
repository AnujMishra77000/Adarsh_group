import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AppRouter } from "@/app/router";
import { renderWithProviders } from "@/test/render";

describe("AppRouter CRM route ownership", () => {
  it("redirects root into the CRM launch route", async () => {
    renderWithProviders(<AppRouter />, { route: "/" });

    expect(await screen.findByRole("heading", { name: /shop entry/i })).toBeInTheDocument();
  });

  it("loads CRM shop entry from the /crm launch route", async () => {
    renderWithProviders(<AppRouter />, { route: "/crm" });

    expect(await screen.findByRole("heading", { name: /shop entry/i })).toBeInTheDocument();
  });

  it("redirects unauthenticated deep CRM routes to CRM shop entry", async () => {
    renderWithProviders(<AppRouter />, { route: "/crm/dashboard" });

    expect(await screen.findByRole("heading", { name: /shop entry/i })).toBeInTheDocument();
  });
});
