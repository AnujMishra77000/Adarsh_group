import { describe, expect, it } from "vitest";

import { calculateBillSummary, calculateMultiBillSummary, sanitizeBillPayloadMoney } from "@/features/bills/calculations";

describe("bill calculations", () => {
  it("calculates multi-item totals and partial payment status", () => {
    const summary = calculateMultiBillSummary(
      [
        { quantity: 1, unit_price: 3000, discount: 250 },
        { quantity: 2, unit_price: 1800, discount: 100 }
      ],
      [{ amount: 1500 }, { amount: 1000 }],
      0
    );

    expect(summary.subtotal).toBe(6600);
    expect(summary.discountTotal).toBe(350);
    expect(summary.taxTotal).toBe(0);
    expect(summary.grandTotal).toBe(6250);
    expect(summary.paidTotal).toBe(2500);
    expect(summary.balanceAmount).toBe(3750);
    expect(summary.paymentStatus).toBe("partial");
  });

  it("keeps the legacy single-item helpers compatible", () => {
    const legacySummary = calculateBillSummary(2500, 500, 1000);
    const sanitized = sanitizeBillPayloadMoney({ whole_price: 2500, discount: 500, paid_amount: 1000 });

    expect(legacySummary.totalAfterDiscount).toBe(2000);
    expect(legacySummary.balanceAmount).toBe(1000);
    expect(sanitized).toEqual({ whole_price: 2500, discount: 500, paid_amount: 1000 });
  });
});
