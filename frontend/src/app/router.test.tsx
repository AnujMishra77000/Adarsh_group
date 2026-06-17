import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AppRouter } from "@/app/router";
import { renderWithProviders } from "@/test/render";

describe("AppRouter public and CRM route ownership", () => {
  it("loads the public website homepage at root", async () => {
    renderWithProviders(<AppRouter />, { route: "/" });

    const crmLoginLinks = await screen.findAllByRole("link", { name: /crm login/i });
    expect(crmLoginLinks.some((link) => link.getAttribute("href") === "/crm")).toBe(true);
    expect(screen.getByRole("heading", { name: /adarsh optical group/i })).toBeInTheDocument();
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
