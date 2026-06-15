export type Prescription = {
  id: number;
  customer_id: number;
  customer_name: string | null;
  customer_business_id: string | null;
  customer_contact_no: string | null;
  prescription_date: string;
  right_sph: number | null;
  right_cyl: number | null;
  right_axis: number | null;
  right_vn: string | null;
  left_sph: number | null;
  left_cyl: number | null;
  left_axis: number | null;
  left_vn: string | null;
  fh: string | null;
  add_power: number | null;
  pd: number | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  created_by: number | null;
  updated_by: number | null;
  is_deleted: boolean;
};

export type PrescriptionPayload = {
  customer_id: number;
  prescription_date: string;
  right_sph?: number | null;
  right_cyl?: number | null;
  right_axis?: number | null;
  right_vn?: string | null;
  left_sph?: number | null;
  left_cyl?: number | null;
  left_axis?: number | null;
  left_vn?: string | null;
  fh?: string | null;
  add_power?: number | null;
  pd?: number | null;
  notes?: string | null;
};

export type PrescriptionPdfResponse = {
  prescription_id: number;
  pdf_url: string;
};

export type PrescriptionSendVendorPayload = {
  vendor_id: number;
  caption?: string | null;
};

export type PrescriptionSendVendorResponse = {
  message: string;
  whatsapp_log_id: number | null;
  provider_message_id: string | null;
};
