import apiClient from "@/lib/api";
import type {
  AdminRegisterRequest,
  LoginRequest,
  LogoutRequest,
  TokenPair,
  UserProfile,
  RefreshTokenRequest
} from "@/types/auth";

export async function registerAdmin(payload: AdminRegisterRequest): Promise<UserProfile> {
  const response = await apiClient.post<UserProfile>("/auth/admin/register", payload);
  return response.data;
}

export async function login(payload: LoginRequest): Promise<TokenPair> {
  const response = await apiClient.post<TokenPair>("/auth/login", payload);
  return response.data;
}

export async function refresh(payload: RefreshTokenRequest): Promise<TokenPair> {
  const response = await apiClient.post<TokenPair>("/auth/refresh", payload);
  return response.data;
}

export async function logout(payload: LogoutRequest): Promise<{ message: string }> {
  const response = await apiClient.post<{ message: string }>("/auth/logout", payload);
  return response.data;
}

export async function fetchMe(): Promise<UserProfile> {
  const response = await apiClient.get<UserProfile>("/auth/me");
  return response.data;
}
