import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { getActiveShop } from "@/features/shops/store";

type ShopRouteProps = {
  children: ReactNode;
};

export function ShopRoute({ children }: ShopRouteProps) {
  const location = useLocation();
  const activeShop = getActiveShop();

  if (!activeShop) {
    return <Navigate to="/shop-entry" replace state={{ from: location.pathname + location.search }} />;
  }

  return <>{children}</>;
}
