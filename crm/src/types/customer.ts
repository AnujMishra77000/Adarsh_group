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
  occupation: string | null;
  guardian_name: string | null;
  guardian_contact_no: string | null;
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

export type CustomerVisitSummary = {
  id: number;
  visit_date: string;
  reason_for_visit: string;
  referred_by: string | null;
  status: "draft" | "in_progress" | "completed" | "cancelled";
  assigned_examiner_id: number | null;
  visit_notes: string | null;
  created_at: string;
};

export type CustomerReferralSummary = {
  visit_id: number;
  visit_date: string;
  specialist_type: string | null;
  referral_status: string | null;
  notes: string | null;
  follow_up: string | null;
};

export type CustomerContactLensOrderSummary = {
  id: number;
  visit_id: number;
  order_reference: string;
  status: "draft" | "ready_for_vendor" | "sent_to_vendor" | "in_production" | "ready_for_delivery" | "delivered" | "cancelled";
  vendor_id: number | null;
  created_at: string;
};

export type CustomerFollowUpTaskSummary = {
  id: number;
  visit_id: number;
  contact_lens_order_id: number;
  task_type: string;
  due_date: string;
  status: "pending" | "completed" | "cancelled";
  notes: string | null;
  completed_at: string | null;
};

export type CustomerDetail = Customer & {
  visits: CustomerVisitSummary[];
  referrals: CustomerReferralSummary[];
  prescriptions: CustomerPrescriptionSummary[];
  bills: CustomerBillSummary[];
  contact_lens_orders: CustomerContactLensOrderSummary[];
  follow_up_tasks: CustomerFollowUpTaskSummary[];
};

export type CustomerPayload = {
  name: string;
  age?: number | null;
  contact_no: string;
  email?: string | null;
  whatsapp_no?: string | null;
  gender?: Gender | null;
  occupation?: string | null;
  guardian_name?: string | null;
  guardian_contact_no?: string | null;
  address?: string | null;
  purpose_of_visit?: string | null;
  whatsapp_opt_in: boolean;
  registration_idempotency_key?: string | null;
};
