import type { TokenPair, UserProfile, UserRole } from "@/types/auth";
import { getActiveShopKey } from "@/features/shops/store";

const AUTH_ROLES: UserRole[] = ["admin", "staff"];

const STORAGE_PREFIX = "eye_boutique";
const LEGACY_ACTIVE_AUTH_ROLE_KEY = "eye_boutique_active_auth_role";

function resolveShopKey(shopKey?: string): string | null {
  if (shopKey && shopKey.trim()) {
    return shopKey.trim().toLowerCase();
  }
  return getActiveShopKey();
}

function activeAuthRoleKey(shopKey: string): string {
  return `${STORAGE_PREFIX}_active_auth_role_${shopKey}`;
}

function accessTokenKey(shopKey: string, role: UserRole): string {
  return `${STORAGE_PREFIX}_access_token_${shopKey}_${role}`;
}

function refreshTokenKey(shopKey: string, role: UserRole): string {
  return `${STORAGE_PREFIX}_refresh_token_${shopKey}_${role}`;
}

function userProfileKey(shopKey: string, role: UserRole): string {
  return `${STORAGE_PREFIX}_user_profile_${shopKey}_${role}`;
}

function isUserRole(value: string | null): value is UserRole {
  return value === "admin" || value === "staff";
}

function firstRoleWithSession(shopKey: string, excludeRole?: UserRole): UserRole | null {
  for (const role of AUTH_ROLES) {
    if (excludeRole && role === excludeRole) {
      continue;
    }

    const token = localStorage.getItem(accessTokenKey(shopKey, role));
    if (token) {
      return role;
    }
  }

  return null;
}

function resolveRole(shopKey: string, role?: UserRole): UserRole | null {
  if (role) {
    return role;
  }

  const activeRole = getActiveAuthRole(shopKey);
  if (activeRole) {
    return activeRole;
  }

  return firstRoleWithSession(shopKey);
}

export function setActiveAuthRole(role: UserRole, shopKey?: string) {
  const resolvedShop = resolveShopKey(shopKey);
  if (!resolvedShop) {
    return;
  }
  localStorage.setItem(activeAuthRoleKey(resolvedShop), role);
}

export function getActiveAuthRole(shopKey?: string): UserRole | null {
  const resolvedShop = resolveShopKey(shopKey);
  if (!resolvedShop) {
    return null;
  }
  const raw = localStorage.getItem(activeAuthRoleKey(resolvedShop));
  if (isUserRole(raw)) {
    return raw;
  }
  return null;
}

export function setAuthTokens(tokens: TokenPair, role: UserRole, shopKey?: string) {
  const resolvedShop = resolveShopKey(shopKey);
  if (!resolvedShop) {
    return;
  }
  setActiveAuthRole(role, resolvedShop);
  localStorage.setItem(accessTokenKey(resolvedShop, role), tokens.access_token);
  localStorage.setItem(refreshTokenKey(resolvedShop, role), tokens.refresh_token);
}

export function setCurrentUser(user: UserProfile, role: UserRole, shopKey?: string) {
  const resolvedShop = resolveShopKey(shopKey);
  if (!resolvedShop) {
    return;
  }
  localStorage.setItem(userProfileKey(resolvedShop, role), JSON.stringify(user));
}

export function getAccessToken(role?: UserRole, shopKey?: string) {
  const resolvedShop = resolveShopKey(shopKey);
  if (!resolvedShop) {
    return null;
  }
  const resolvedRole = resolveRole(resolvedShop, role);
  if (!resolvedRole) {
    return null;
  }
  return localStorage.getItem(accessTokenKey(resolvedShop, resolvedRole));
}

export function getRefreshToken(role?: UserRole, shopKey?: string) {
  const resolvedShop = resolveShopKey(shopKey);
  if (!resolvedShop) {
    return null;
  }
  const resolvedRole = resolveRole(resolvedShop, role);
  if (!resolvedRole) {
    return null;
  }
  return localStorage.getItem(refreshTokenKey(resolvedShop, resolvedRole));
}

export function getCurrentUser(role?: UserRole, shopKey?: string): UserProfile | null {
  const resolvedShop = resolveShopKey(shopKey);
  if (!resolvedShop) {
    return null;
  }
  const resolvedRole = resolveRole(resolvedShop, role);
  if (!resolvedRole) {
    return null;
  }

  const raw = localStorage.getItem(userProfileKey(resolvedShop, resolvedRole));
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as UserProfile;
  } catch {
    localStorage.removeItem(userProfileKey(resolvedShop, resolvedRole));
    return null;
  }
}

export function clearCurrentUser(role?: UserRole, shopKey?: string) {
  const resolvedShop = resolveShopKey(shopKey);
  if (!resolvedShop) {
    return;
  }
  const resolvedRole = resolveRole(resolvedShop, role);
  if (!resolvedRole) {
    return;
  }

  localStorage.removeItem(userProfileKey(resolvedShop, resolvedRole));
}

export function clearAuthTokens(role?: UserRole, shopKey?: string) {
  const resolvedShop = resolveShopKey(shopKey);
  if (!resolvedShop) {
    return;
  }
  const resolvedRole = resolveRole(resolvedShop, role);
  if (!resolvedRole) {
    return;
  }

  localStorage.removeItem(accessTokenKey(resolvedShop, resolvedRole));
  localStorage.removeItem(refreshTokenKey(resolvedShop, resolvedRole));
  localStorage.removeItem(userProfileKey(resolvedShop, resolvedRole));

  const activeRole = getActiveAuthRole(resolvedShop);
  if (activeRole === resolvedRole) {
    const fallbackRole = firstRoleWithSession(resolvedShop, resolvedRole);
    if (fallbackRole) {
      setActiveAuthRole(fallbackRole, resolvedShop);
    } else {
      localStorage.removeItem(activeAuthRoleKey(resolvedShop));
    }
  }
}

export function clearAllAuthSessions() {
  const keysToRemove: string[] = [];
  for (let i = 0; i < localStorage.length; i += 1) {
    const key = localStorage.key(i);
    if (!key) {
      continue;
    }
    const isAuthKey =
      key.startsWith(`${STORAGE_PREFIX}_access_token_`) ||
      key.startsWith(`${STORAGE_PREFIX}_refresh_token_`) ||
      key.startsWith(`${STORAGE_PREFIX}_user_profile_`) ||
      key.startsWith(`${STORAGE_PREFIX}_active_auth_role_`);
    if (isAuthKey) {
      keysToRemove.push(key);
    }
  }
  keysToRemove.forEach((key) => localStorage.removeItem(key));

  // Remove legacy non-shop-scoped keys if they exist.
  localStorage.removeItem(LEGACY_ACTIVE_AUTH_ROLE_KEY);
  localStorage.removeItem(`${STORAGE_PREFIX}_access_token_admin`);
  localStorage.removeItem(`${STORAGE_PREFIX}_access_token_staff`);
  localStorage.removeItem(`${STORAGE_PREFIX}_refresh_token_admin`);
  localStorage.removeItem(`${STORAGE_PREFIX}_refresh_token_staff`);
  localStorage.removeItem(`${STORAGE_PREFIX}_user_profile_admin`);
  localStorage.removeItem(`${STORAGE_PREFIX}_user_profile_staff`);
}
