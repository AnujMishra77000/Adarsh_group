export type Vendor = {
  id: number;
  vendor_name: string;
  contact_person: string | null;
  whatsapp_no: string;
  address: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type VendorPayload = {
  vendor_name: string;
  contact_person?: string | null;
  whatsapp_no: string;
  address?: string | null;
  is_active: boolean;
};
