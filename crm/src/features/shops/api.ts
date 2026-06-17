import apiClient from "@/lib/api";

export type ShopResolvePayload = {
  mobile?: string;
  identifier?: string;
};

export type ResolvedShop = {
  code: string;
  display_name: string;
  location_label: string;
  center_type: string;
};

export async function resolveShop(payload: ShopResolvePayload): Promise<ResolvedShop> {
  const response = await apiClient.post<ResolvedShop>("/public/shops/resolve", payload);
  return response.data;
}
