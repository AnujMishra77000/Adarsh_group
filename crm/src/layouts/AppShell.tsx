import { Outlet } from "react-router-dom";

import { Header } from "@/components/ui/Header";
import { Sidebar } from "@/components/ui/Sidebar";
import { useCurrentUser } from "@/features/auth/useCurrentUser";

export function AppShell() {
  const currentUserQuery = useCurrentUser();

  return (
    <div className="min-h-screen bg-matte-gradient text-slate-100">
      <Sidebar role={currentUserQuery.data?.role} />
      <div className="lg:pl-16">
        <Header user={currentUserQuery.data} />
        <main className="p-3 pb-24 sm:p-5 sm:pb-28 lg:p-7 lg:pb-7">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
