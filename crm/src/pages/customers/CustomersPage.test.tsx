import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CustomersPage } from "@/pages/customers/CustomersPage";
import { renderWithProviders } from "@/test/render";

describe("CustomersPage patient visit workflow", () => {
  it("presents patient search and visit actions instead of quick prescription and bill creation", () => {
    renderWithProviders(<CustomersPage />, { route: "/crm/customers" });

    expect(screen.getByRole("heading", { name: /search patient/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /new patient/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /start new visit/i })).toBeInTheDocument();
    expect(screen.queryByText(/quick add prescription/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/quick add bill/i)).not.toBeInTheDocument();
  });
});
