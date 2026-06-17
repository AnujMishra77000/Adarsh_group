export type PaymentStatus = "pending" | "partial" | "paid";
export type Gender = "male" | "female" | "other";

export type Customer = {
  id: number;
  customer_id: string;
  name: string;
  age: number | null;
  contact_no: string;
  email: string | null;
  whatsapp_no: string | null;
  gender: Gender | null;
  address: string | null;
  purpose_of_visit: string | null;
  whatsapp_opt_in: boolean;
  created_at: string;
  updated_at: string;
  created_by: number | null;
  updated_by: number | null;
  is_deleted: boolean;
};

export type CustomerPrescriptionSummary = {
  id: number;
  prescription_date: string;
  notes: string | null;
};

export type CustomerBillSummary = {
  id: number;
  bill_number: string;
  final_price: number;
  balance_amount: number;
  payment_status: PaymentStatus;
  created_at: string;
};

export type CustomerDetail = Customer & {
  prescriptions: CustomerPrescriptionSummary[];
  bills: CustomerBillSummary[];
};

export type CustomerPayload = {
  name: string;
  age?: number | null;
  contact_no: string;
  email?: string | null;
  whatsapp_no?: string | null;
  gender?: Gender | null;
  address?: string | null;
  purpose_of_visit?: string | null;
  whatsapp_opt_in: boolean;
};
