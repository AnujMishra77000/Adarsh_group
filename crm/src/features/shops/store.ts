import { getShopByKey, type ShopBrand, type ShopKey } from "@/features/shops/config";

const ACTIVE_SHOP_KEY = "eye_boutique_active_shop_key";

export function setActiveShop(shopKey: ShopKey) {
  // Keep active shop tab-scoped so refresh restores exact shop/page in the same tab
  // without inheriting stale cross-tab values.
  sessionStorage.setItem(ACTIVE_SHOP_KEY, shopKey);
  localStorage.removeItem(ACTIVE_SHOP_KEY);
}

export function getActiveShopKey(): ShopKey | null {
  const sessionRaw = sessionStorage.getItem(ACTIVE_SHOP_KEY);
  const sessionShop = getShopByKey(sessionRaw);
  if (sessionShop) {
    return sessionShop.key;
  }

  // One-time migration from old localStorage behavior.
  const legacyRaw = localStorage.getItem(ACTIVE_SHOP_KEY);
  const legacyShop = getShopByKey(legacyRaw);
  if (!legacyShop) {
    return null;
  }

  sessionStorage.setItem(ACTIVE_SHOP_KEY, legacyShop.key);
  localStorage.removeItem(ACTIVE_SHOP_KEY);
  return legacyShop.key;
}

export function getActiveShop(): ShopBrand | null {
  return getShopByKey(getActiveShopKey());
}

export function clearActiveShop() {
  sessionStorage.removeItem(ACTIVE_SHOP_KEY);
  localStorage.removeItem(ACTIVE_SHOP_KEY);
}
