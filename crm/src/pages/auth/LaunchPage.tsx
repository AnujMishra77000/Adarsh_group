import { Navigate } from "react-router-dom";

import { getAccessToken, getActiveAuthRole, setActiveAuthRole } from "@/features/auth/store";
import { getActiveShop } from "@/features/shops/store";
import { CRM_PATHS } from "@/lib/routes";
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
    return <Navigate to={CRM_PATHS.dashboard} replace />;
  }

  if (activeShop) {
    return <Navigate to={CRM_PATHS.landing} replace />;
  }

  return <Navigate to={CRM_PATHS.shopEntry} replace />;
}
