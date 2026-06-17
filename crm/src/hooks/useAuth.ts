import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { logout as logoutRequest } from "@/features/auth/api";
import { useCurrentUser } from "@/features/auth/useCurrentUser";
import { clearAuthTokens, getAccessToken, getRefreshToken } from "@/features/auth/store";
import { getErrorMessage } from "@/lib/errors";
import { CRM_PATHS } from "@/lib/routes";

export function useAuth() {
  const navigate = useNavigate();
  const currentUserQuery = useCurrentUser();

  const logout = async () => {
    const refreshToken = getRefreshToken();

    try {
      if (refreshToken) {
        await logoutRequest({ refresh_token: refreshToken });
      }
    } catch (error) {
      console.error("Logout request failed:", getErrorMessage(error));
      toast.error("Session cleared locally. Server logout could not be confirmed.");
    } finally {
      clearAuthTokens();
      navigate(CRM_PATHS.root, { replace: true });
    }
  };

  return {
    isAuthenticated: Boolean(getAccessToken()),
    accessToken: getAccessToken(),
    refreshToken: getRefreshToken(),
    user: currentUserQuery.data ?? null,
    logout
  };
}
