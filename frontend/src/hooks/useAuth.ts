import { useNavigate } from "react-router-dom";

import { useCurrentUser } from "@/features/auth/useCurrentUser";
import { clearAuthTokens, getAccessToken, getRefreshToken } from "@/features/auth/store";

export function useAuth() {
  const navigate = useNavigate();
  const currentUserQuery = useCurrentUser();

  const logout = () => {
    clearAuthTokens();
    navigate("/", { replace: true });
  };

  return {
    isAuthenticated: Boolean(getAccessToken()),
    accessToken: getAccessToken(),
    refreshToken: getRefreshToken(),
    user: currentUserQuery.data ?? null,
    logout
  };
}
