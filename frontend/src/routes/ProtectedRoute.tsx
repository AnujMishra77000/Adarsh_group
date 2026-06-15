import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { getAccessToken, getActiveAuthRole, getCurrentUser } from "@/features/auth/store";
import { useCurrentUser } from "@/features/auth/useCurrentUser";
import type { UserRole } from "@/types/auth";

type ProtectedRouteProps = {
  children: ReactNode;
  allowedRoles?: UserRole[];
};

export function ProtectedRoute({ children, allowedRoles }: ProtectedRouteProps) {
  const location = useLocation();
  const activeRole = getActiveAuthRole();
  const accessToken = getAccessToken(activeRole ?? undefined);
  const currentUserQuery = useCurrentUser();
  const resolvedUser = currentUserQuery.data ?? getCurrentUser(activeRole ?? undefined);

  if (activeRole === null || accessToken === null) {
    return <Navigate to="/" replace state={{ from: location.pathname }} />;
  }

  if (currentUserQuery.isLoading && !resolvedUser) {
    return (
      <div className="mx-auto mt-24 w-full max-w-md rounded-xl border border-pink-300/30 bg-matte-850/90 p-4 text-center text-sm text-slate-200 shadow-neon-ring">
        Validating session...
      </div>
    );
  }

  if (!resolvedUser && currentUserQuery.isError) {
    return (
      <div className="mx-auto mt-24 w-full max-w-md rounded-xl border border-amber-300/35 bg-amber-500/10 p-4 text-center text-sm text-amber-100 shadow-neon-ring">
        <p>Session validation failed. Please retry.</p>
        <button
          type="button"
          onClick={() => {
            void currentUserQuery.refetch();
          }}
          className="mt-3 rounded-md border border-pink-300/45 bg-pink-500/15 px-3 py-1.5 text-xs font-medium text-pink-100"
        >
          Retry Validation
        </button>
      </div>
    );
  }

  if (!resolvedUser) {
    return (
      <div className="mx-auto mt-24 w-full max-w-md rounded-xl border border-pink-300/30 bg-matte-850/90 p-4 text-center text-sm text-slate-200 shadow-neon-ring">
        Loading profile...
      </div>
    );
  }

  if (allowedRoles && !allowedRoles.includes(resolvedUser.role)) {
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
}
