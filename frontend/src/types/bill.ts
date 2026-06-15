export type PaymentMode = "cash" | "upi";
export type PaymentStatus = "pending" | "partial" | "paid";

export type Bill = {
  id: number;
  bill_number: string;
  customer_id: number;
  customer_name_snapshot: string;

  product_name: string;
  frame_name: string | null;

  whole_price: number;
  discount: number;
  final_price: number;
  paid_amount: number;
  balance_amount: number;

  payment_mode: PaymentMode;
  payment_status: PaymentStatus;

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
  product_name: string;
  frame_name?: string | null;
  whole_price: number;
  discount: number;
  paid_amount: number;
  payment_mode: PaymentMode;
  delivery_date?: string | null;
  notes?: string | null;
};
