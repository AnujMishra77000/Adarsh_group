import { Navigate, Outlet } from "react-router-dom";

import { useActiveShop } from "@/features/shops/useActiveShop";
import { CRM_PATHS } from "@/lib/routes";

export function AuthLayout() {
  const activeShop = useActiveShop();
  if (!activeShop) {
    return <Navigate to={CRM_PATHS.shopEntry} replace />;
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-matte-gradient p-5 sm:p-8">
      <div className="w-full max-w-lg rounded-2xl border border-pink-300/25 bg-matte-900/80 p-6 shadow-neon-glow backdrop-blur sm:p-8">
        <div className="mb-4 rounded-xl border border-pink-300/35 bg-pink-500/10 px-4 py-3">
          <h1 className="text-base font-semibold text-pink-50 sm:text-lg">
            {activeShop.welcomeTitle}
          </h1>
        </div>
        <Outlet />
      </div>
    </div>
  );
}
