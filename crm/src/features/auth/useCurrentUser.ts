import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";

import { fetchMe } from "@/features/auth/api";
import {
  clearCurrentUser,
  getAccessToken,
  getActiveAuthRole,
  getCurrentUser,
  setCurrentUser
} from "@/features/auth/store";
import { getActiveShopKey } from "@/features/shops/store";

export function useCurrentUser() {
  const activeShopKey = getActiveShopKey();
  const activeRole = getActiveAuthRole();
  const hasAccessToken = activeRole !== null && getAccessToken(activeRole) !== null;

  const query = useQuery({
    queryKey: ["auth", "me", activeShopKey, activeRole],
    queryFn: fetchMe,
    enabled: hasAccessToken,
    retry: false,
    staleTime: 60_000,
    initialData: hasAccessToken && activeRole ? (getCurrentUser(activeRole) ?? undefined) : undefined
  });

  useEffect(() => {
    if (query.data && activeRole) {
      setCurrentUser(query.data, activeRole);
    }
  }, [query.data, activeRole]);

  useEffect(() => {
    if (activeRole && hasAccessToken === false) {
      clearCurrentUser(activeRole);
    }
  }, [activeRole, hasAccessToken]);

  return query;
}
