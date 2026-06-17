export type ShopKey =
  | "adarsh-optical-centre"
  | "adarsh-optometric-clinic"
  | "adarsh-opticals-muxar"
  | "adarsh-eye-boutique";

export type ShopBrand = {
  key: ShopKey;
  name: string;
  locationLabel: string;
  centerType: string;
  isActive: boolean;
  legacyCodes?: string[];
  welcomeTitle: string;
};

export const SHOP_BRANDS: ShopBrand[] = [
  {
    key: "adarsh-optical-centre",
    name: "Adarsh Optical Centre",
    locationLabel: "",
    centerType: "Optical centre",
    isActive: true,
    legacyCodes: ["adarsh-optical-center"],
    welcomeTitle: "Welcome to Adarsh Optical Centre CRM"
  },
  {
    key: "adarsh-optometric-clinic",
    name: "Adarsh Optometric Clinic",
    locationLabel: "Khadakpada, Kalyan West",
    centerType: "Optometric clinic",
    isActive: true,
    legacyCodes: ["adarsh-optometric-center"],
    welcomeTitle: "Welcome to Adarsh Optometric Clinic CRM"
  },
  {
    key: "adarsh-opticals-muxar",
    name: "Adarsh Opticals",
    locationLabel: "Near Muxar Hospital",
    centerType: "Optical centre",
    isActive: true,
    welcomeTitle: "Welcome to Adarsh Opticals CRM"
  },
  {
    key: "adarsh-eye-boutique",
    name: "Adarsh Eye Boutique",
    locationLabel: "",
    centerType: "Eye boutique",
    isActive: true,
    legacyCodes: ["aadarsh-eye-boutique-center"],
    welcomeTitle: "Welcome to Adarsh Eye Boutique CRM"
  }
];

export function normalizeShopCode(input: string): string {
  return input.trim().toLowerCase();
}

export function getShopByKey(key: string | null): ShopBrand | null {
  if (!key) {
    return null;
  }

  const normalized = normalizeShopCode(key);
  return (
    SHOP_BRANDS.find((shop) => {
      if (shop.key === normalized) {
        return true;
      }
      return (shop.legacyCodes ?? []).includes(normalized);
    }) ?? null
  );
}

export function getActiveShops(): ShopBrand[] {
  return SHOP_BRANDS.filter((shop) => shop.isActive);
}
