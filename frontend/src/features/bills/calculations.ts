import type { PaymentStatus } from "@/types/bill";

type BillSummary = {
  totalCost: number;
  discount: number;
  totalAfterDiscount: number;
  paidAmount: number;
  balanceAmount: number;
  paymentStatus: PaymentStatus;
};

const MONEY_FACTOR = 100;

function roundMoney(value: number): number {
  if (!Number.isFinite(value)) {
    return 0;
  }
  return Math.round(value * MONEY_FACTOR) / MONEY_FACTOR;
}

function toNonNegative(value: number): number {
  const rounded = roundMoney(value);
  if (rounded < 0) {
    return 0;
  }
  return rounded;
}

export function calculateBillSummary(wholePriceInput: number, discountInput: number, paidAmountInput: number): BillSummary {
  const totalCost = toNonNegative(wholePriceInput);
  const discount = Math.min(toNonNegative(discountInput), totalCost);
  const totalAfterDiscount = roundMoney(totalCost - discount);
  const paidAmount = Math.min(toNonNegative(paidAmountInput), totalAfterDiscount);
  const balanceAmount = roundMoney(totalAfterDiscount - paidAmount);

  let paymentStatus: PaymentStatus = "pending";
  if (balanceAmount <= 0) {
    paymentStatus = "paid";
  } else if (paidAmount > 0) {
    paymentStatus = "partial";
  }

  return {
    totalCost,
    discount,
    totalAfterDiscount,
    paidAmount,
    balanceAmount,
    paymentStatus
  };
}

export function sanitizeBillPayloadMoney(input: {
  whole_price: number;
  discount: number;
  paid_amount: number;
}): {
  whole_price: number;
  discount: number;
  paid_amount: number;
} {
  const summary = calculateBillSummary(input.whole_price, input.discount, input.paid_amount);
  return {
    whole_price: summary.totalCost,
    discount: summary.discount,
    paid_amount: summary.paidAmount
  };
}
