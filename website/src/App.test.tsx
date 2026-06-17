import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "@/App";
import { renderWithProviders } from "@/test/render";

describe("Website app", () => {
  it("renders the approved public website mockup and links to the separate CRM app", () => {
    renderWithProviders(<App />, { route: "/" });

    expect(screen.getByRole("heading", { name: /see better\. look better\. live better\./i })).toBeInTheDocument();
    expect(screen.getAllByText(/trusted since 1985/i).length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: /four specialized centers/i })).toBeInTheDocument();
    expect(screen.getAllByText(/adarsh optical centre/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/adarsh optometric clinic/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/adarsh opticals/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/adarsh eye boutique/i).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /contact lenses/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /visit your nearest adarsh center/i })).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /crm login/i })[0]).toHaveAttribute(
      "href",
      "http://127.0.0.1:5173/crm"
    );
  });

  it("renders the same public site from public section routes", () => {
    renderWithProviders(<App />, { route: "/centers" });

    expect(screen.getByRole("heading", { name: /four specialized centers/i })).toBeInTheDocument();
  });
});
