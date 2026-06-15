export type ShopKey = "aadarsh-eye-boutique-center" | "adarsh-optometric-center" | "adarsh-optical-center";

export type ShopBrand = {
  key: ShopKey;
  name: string;
  phone: string;
  passcode: string;
  passcodeAliases?: string[];
  welcomeTitle: string;
};

export const SHOP_BRANDS: ShopBrand[] = [
  {
    key: "aadarsh-eye-boutique-center",
    name: "Aadarsh Eye Boutique Center",
    phone: "9082967356",
    passcode: "9082967356",
    welcomeTitle: "Welcome to Aadarsh Eye Boutique CRM Center"
  },
  {
    key: "adarsh-optometric-center",
    name: "Adarsh Optometric Center",
    phone: "6124157631",
    passcode: "6124157631",
    welcomeTitle: "Welcome to Aadarsh Optometric CRM Center"
  },
  {
    key: "adarsh-optical-center",
    name: "Adarsh Optical Center",
    phone: "6124157622",
    passcode: "6124157622",
    passcodeAliases: ["612415722"],
    welcomeTitle: "Welcome to Aadarsh Optical CRM Center"
  }
];

export function normalizePhone(input: string): string {
  return input.replace(/\D/g, "");
}

export function getShopByKey(key: string | null): ShopBrand | null {
  if (!key) {
    return null;
  }
  return SHOP_BRANDS.find((shop) => shop.key === key) ?? null;
}

export function getShopByPhone(phone: string): ShopBrand | null {
  const normalized = normalizePhone(phone);
  return SHOP_BRANDS.find((shop) => normalizePhone(shop.phone) === normalized) ?? null;
}

export function getShopByPasscode(passcode: string): ShopBrand | null {
  const normalized = normalizePhone(passcode);
  return (
    SHOP_BRANDS.find((shop) => {
      if (normalizePhone(shop.passcode) === normalized) {
        return true;
      }
      return (shop.passcodeAliases ?? []).some((alias) => normalizePhone(alias) === normalized);
    }) ?? null
  );
}
