export type StaffUser = {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
};

export type StaffCreatePayload = {
  email: string;
  full_name?: string | null;
  password: string;
};

export type StaffLoginActivity = {
  id: number;
  staff_user_id: number;
  staff_email: string;
  staff_full_name: string | null;
  attempted_at: string;
  ip_address: string | null;
  user_agent: string | null;
};
