export type UserRole = "admin" | "staff";

export type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
};

export type LoginRequest = {
  email: string;
  password: string;
};

export type RefreshTokenRequest = {
  refresh_token: string;
};

export type LogoutRequest = {
  refresh_token: string;
};

export type AdminRegisterRequest = {
  full_name: string;
  email: string;
  password: string;
  master_password: string;
};

export type UserProfile = {
  id: number;
  email: string;
  full_name: string | null;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};
