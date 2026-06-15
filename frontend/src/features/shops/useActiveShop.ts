import { getActiveShop } from "@/features/shops/store";

export function useActiveShop() {
  return getActiveShop();
}
