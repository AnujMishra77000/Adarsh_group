import type { PaymentStatus } from "@/types/bill";

type BillSummary = {
  totalCost: number;
  discount: number;
  totalAfterDiscount: number;
  paidAmount: number;
  balanceAmount: number;
  paymentStatus: PaymentStatus;
};

type BillItemMoneyInput = {
  quantity: number;
  unit_price: number;
  discount: number;
};

type BillPaymentMoneyInput = {
  amount: number;
};

type MultiBillSummary = {
  subtotal: number;
  discountTotal: number;
  taxTotal: number;
  grandTotal: number;
  paidTotal: number;
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

export function calculateMultiBillSummary(
  items: BillItemMoneyInput[],
  payments: BillPaymentMoneyInput[],
  taxTotalInput = 0
): MultiBillSummary {
  const lineSummaries = items.map((item) => {
    const quantity = toNonNegative(item.quantity);
    const unitPrice = toNonNegative(item.unit_price);
    const gross = roundMoney(quantity * unitPrice);
    const discount = Math.min(toNonNegative(item.discount), gross);
    return {
      gross,
      discount,
      lineTotal: roundMoney(gross - discount)
    };
  });

  const subtotal = roundMoney(lineSummaries.reduce((sum, item) => sum + item.gross, 0));
  const discountTotal = roundMoney(lineSummaries.reduce((sum, item) => sum + item.discount, 0));
  const itemTotal = roundMoney(lineSummaries.reduce((sum, item) => sum + item.lineTotal, 0));
  const taxTotal = toNonNegative(taxTotalInput);
  const grandTotal = roundMoney(itemTotal + taxTotal);
  const paidTotal = Math.min(roundMoney(payments.reduce((sum, payment) => sum + toNonNegative(payment.amount), 0)), grandTotal);
  const balanceAmount = roundMoney(grandTotal - paidTotal);

  let paymentStatus: PaymentStatus = "pending";
  if (balanceAmount <= 0) {
    paymentStatus = "paid";
  } else if (paidTotal > 0) {
    paymentStatus = "partial";
  }

  return {
    subtotal,
    discountTotal,
    taxTotal,
    grandTotal,
    paidTotal,
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
