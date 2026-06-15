import { Navigate } from "react-router-dom";

import { getAccessToken, getActiveAuthRole, setActiveAuthRole } from "@/features/auth/store";
import { getActiveShop } from "@/features/shops/store";
import type { UserRole } from "@/types/auth";

function resolveRoleFromStoredSession(): UserRole | null {
  if (getAccessToken("admin")) {
    return "admin";
  }
  if (getAccessToken("staff")) {
    return "staff";
  }
  return null;
}

export function LaunchPage() {
  const activeShop = getActiveShop();
  let activeRole = getActiveAuthRole();

  if (!activeRole || !getAccessToken(activeRole)) {
    const fallbackRole = resolveRoleFromStoredSession();
    if (fallbackRole) {
      setActiveAuthRole(fallbackRole);
      activeRole = fallbackRole;
    }
  }

  const isAuthenticated = Boolean(activeRole && getAccessToken(activeRole));

  if (isAuthenticated && activeShop) {
    return <Navigate to="/dashboard" replace />;
  }

  return <Navigate to="/shop-entry" replace />;
}
