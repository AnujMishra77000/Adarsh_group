import { LogOut } from "lucide-react";

import { useActiveShop } from "@/features/shops/useActiveShop";
import { useAuth } from "@/hooks/useAuth";
import type { UserProfile } from "@/types/auth";

type HeaderProps = {
  user?: UserProfile;
};

function getDisplayName(user?: UserProfile): string {
  if (!user) {
    return "";
  }

  const fullName = user.full_name?.trim();
  if (fullName) {
    return fullName;
  }

  if (user.email.includes("@")) {
    return user.email.split("@")[0];
  }

  return user.email;
}

export function Header({ user }: HeaderProps) {
  const { logout } = useAuth();
  const activeShop = useActiveShop();
  const displayName = getDisplayName(user);
  const shopName = activeShop?.name ?? "Aadarsh Eye Boutique Center";

  return (
    <header className="sticky top-0 z-20 border-b border-pink-300/20 bg-matte-900/65 backdrop-blur">
      <div className="mx-auto flex w-full items-center justify-between gap-3 px-3 py-3 sm:px-5 lg:px-7">
        <div className="min-w-0">
          <h1 className="truncate text-sm font-semibold text-slate-100 sm:text-base lg:text-lg">{shopName}</h1>
          <p className="truncate text-[11px] text-slate-300 sm:text-xs">
            {user
              ? `${user.role === "admin" ? "Admin" : "Staff"} Access • ${displayName}`
              : "CRM and Operations Dashboard"}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {user && (
            <span className="max-w-[170px] truncate rounded-md border border-pink-300/30 bg-pink-400/10 px-2 py-1 text-[11px] font-medium text-pink-100 sm:max-w-[240px]">
              {displayName}
            </span>
          )}
          <button
            type="button"
            onClick={logout}
            className="inline-flex items-center gap-2 rounded-lg border border-pink-300/35 bg-matte-800 px-2.5 py-2 text-xs font-medium text-pink-100 transition hover:border-pink-200 hover:text-pink-50 sm:px-3 sm:text-sm"
          >
            <LogOut size={15} />
            <span className="hidden sm:inline">Logout</span>
          </button>
        </div>
      </div>
    </header>
  );
}
