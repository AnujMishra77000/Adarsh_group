export type PaymentMode = "cash" | "upi" | "card" | "bank_transfer" | "other";
export type PaymentStatus = "pending" | "partial" | "paid";
export type BillItemType = "frame" | "lens" | "coating" | "contact_lens" | "eye_test" | "repair" | "accessory" | "other";

export type BillItem = {
  id: number;
  bill_id: number;
  item_type: BillItemType;
  item_name: string;
  quantity: number;
  unit_price: number;
  discount: number;
  line_total: number;
};

export type BillPayment = {
  id: number;
  bill_id: number;
  mode: PaymentMode;
  amount: number;
  paid_at: string;
  reference_no: string | null;
};

export type BillItemPayload = {
  item_type: BillItemType;
  item_name: string;
  quantity: number;
  unit_price: number;
  discount: number;
};

export type BillPaymentPayload = {
  mode: PaymentMode;
  amount: number;
  paid_at?: string | null;
  reference_no?: string | null;
};

export type Bill = {
  id: number;
  bill_number: string;
  customer_id: number;
  visit_id: number | null;
  dispensing_order_id: number | null;
  contact_lens_order_id: number | null;
  customer_name_snapshot: string;

  product_name: string;
  frame_name: string | null;

  whole_price: number;
  discount: number;
  final_price: number;
  paid_amount: number;
  subtotal: number;
  discount_total: number;
  tax_total: number;
  grand_total: number;
  paid_total: number;
  balance_amount: number;

  payment_mode: PaymentMode;
  payment_status: PaymentStatus;
  items: BillItem[];
  payments: BillPayment[];

  delivery_date: string | null;
  notes: string | null;
  pdf_url: string | null;

  created_at: string;
  updated_at: string;
  created_by: number | null;
  updated_by: number | null;
  is_deleted: boolean;

  customer_name: string | null;
  customer_business_id: string | null;
  customer_contact_no: string | null;
};

export type BillPayload = {
  customer_id: number;
  visit_id?: number | null;
  dispensing_order_id?: number | null;
  contact_lens_order_id?: number | null;
  product_name: string;
  frame_name?: string | null;
  whole_price: number;
  discount: number;
  paid_amount: number;
  payment_mode: PaymentMode;
  tax_total?: number;
  items?: BillItemPayload[];
  payments?: BillPaymentPayload[];
  delivery_date?: string | null;
  notes?: string | null;
};
