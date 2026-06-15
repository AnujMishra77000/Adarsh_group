import {
  BarChart3,
  FileText,
  LayoutDashboard,
  Megaphone,
  MessageSquare,
  Receipt,
  UserCog,
  Users,
  UserSquare2,
  type LucideIcon
} from "lucide-react";
import { NavLink } from "react-router-dom";

import logoMark from "@/assets/logo-mark.svg";
import { useActiveShop } from "@/features/shops/useActiveShop";
import { cn } from "@/lib/cn";
import type { UserRole } from "@/types/auth";

type SidebarProps = {
  role?: UserRole;
};

type NavItem = {
  to: string;
  label: string;
  shortLabel: string;
  icon: LucideIcon;
  roles?: UserRole[];
};

const navItems: NavItem[] = [
  { to: "/dashboard", label: "Dashboard", shortLabel: "Home", icon: LayoutDashboard },
  { to: "/customers", label: "Customers", shortLabel: "Cust", icon: Users },
  { to: "/prescriptions", label: "Prescriptions", shortLabel: "Rx", icon: FileText },
  { to: "/vendors", label: "Vendors", shortLabel: "Vendor", icon: UserSquare2 },
  { to: "/billing", label: "Billing", shortLabel: "Bill", icon: Receipt },
  { to: "/shared-chat", label: "Shared Chat", shortLabel: "Chat", icon: MessageSquare },
  { to: "/campaigns", label: "Campaigns", shortLabel: "Camp", icon: Megaphone },
  { to: "/analytics", label: "Analytics", shortLabel: "Chart", icon: BarChart3, roles: ["admin"] },
  { to: "/staff-management", label: "Staff", shortLabel: "Staff", icon: UserCog, roles: ["admin"] }
];

export function Sidebar({ role }: SidebarProps) {
  const activeShop = useActiveShop();
  const effectiveRole = role ?? "staff";
  const visibleNavItems = navItems.filter((item) => item.roles === undefined || item.roles.includes(effectiveRole));

  return (
    <>
      <aside className="fixed bottom-0 left-0 top-0 z-30 hidden w-16 border-r border-pink-300/20 bg-matte-900/85 px-2 py-3 shadow-panel backdrop-blur lg:flex lg:flex-col lg:items-center">
        <div className="mb-4 rounded-lg border border-pink-300/35 bg-matte-800/75 p-1.5">
          <img alt={activeShop?.name ?? "Eye Boutique"} src={logoMark} className="h-7 w-7" />
        </div>

        <nav className="flex w-full flex-1 flex-col items-center gap-2 overflow-y-auto">
          {visibleNavItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              title={item.label}
              className={({ isActive }) =>
                cn(
                  "flex h-10 w-10 items-center justify-center rounded-xl border transition-all",
                  isActive
                    ? "border-pink-300/45 bg-matte-800 text-pink-100 shadow-neon-ring"
                    : "border-transparent text-slate-300 hover:border-pink-300/25 hover:bg-matte-800/80 hover:text-pink-50"
                )
              }
            >
              <item.icon size={17} />
              <span className="sr-only">{item.label}</span>
            </NavLink>
          ))}
        </nav>
      </aside>

      <nav className="fixed bottom-0 left-0 right-0 z-40 border-t border-pink-300/20 bg-matte-900/95 px-2 py-2 backdrop-blur lg:hidden">
        <div
          className="grid gap-1"
          style={{
            gridTemplateColumns: `repeat(${Math.max(visibleNavItems.length, 1)}, minmax(0, 1fr))`
          }}
        >
          {visibleNavItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  "flex flex-col items-center gap-1 rounded-lg px-1 py-1.5 text-[10px] font-medium",
                  isActive ? "bg-matte-800 text-pink-100" : "text-slate-300 hover:bg-matte-800/75 hover:text-pink-50"
                )
              }
            >
              <item.icon size={14} />
              <span>{item.shortLabel}</span>
            </NavLink>
          ))}
        </div>
      </nav>
    </>
  );
}
