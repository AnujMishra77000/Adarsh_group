import { ArrowLeft, ArrowRight, ShieldCheck, UserPlus, Users } from "lucide-react";
import { Link, Navigate } from "react-router-dom";

import { useActiveShop } from "@/features/shops/useActiveShop";

const actions = [
  {
    title: "Admin Registration",
    description: "Create and configure a new admin account for platform control.",
    to: "/admin-register",
    cta: "Register Admin",
    icon: UserPlus
  },
  {
    title: "Login Admin",
    description: "Full-access admin login to manage staff, campaigns, settings, and analytics.",
    to: "/login/admin",
    cta: "Admin Login",
    icon: ShieldCheck
  },
  {
    title: "Login Staff",
    description: "Secure staff access for customer, prescription, billing, and operations workflows.",
    to: "/login/staff",
    cta: "Staff Login",
    icon: Users
  }
];

export function LandingPage() {
  const activeShop = useActiveShop();
  if (!activeShop) {
    return <Navigate to="/shop-entry" replace />;
  }

  return (
    <div className="min-h-screen bg-matte-gradient px-4 py-8 text-slate-100 sm:px-6 sm:py-12 lg:px-10 lg:py-16">
      <div className="mx-auto w-full max-w-6xl">
        <header className="mb-8 rounded-2xl border border-pink-300/25 bg-matte-900/65 px-5 py-6 text-center shadow-neon-ring sm:mb-12 sm:px-8 sm:py-8">
          <div className="mb-4 flex justify-start">
            <Link
              to="/shop-entry"
              className="inline-flex items-center gap-2 rounded-lg border border-pink-300/40 bg-pink-500/10 px-3 py-1.5 text-xs font-medium text-pink-100 transition hover:bg-pink-500/20 sm:text-sm"
            >
              <ArrowLeft size={14} />
              Back to Contact Number Entry
            </Link>
          </div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-50 sm:text-3xl lg:text-4xl">
            {activeShop.welcomeTitle}
          </h1>
          <p className="mx-auto mt-3 max-w-3xl text-sm text-slate-200/90 sm:text-base">
            Choose your access path to continue to the CRM platform.
          </p>
        </header>

        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {actions.map((item) => (
            <Link
              key={item.title}
              to={item.to}
              className="group rounded-2xl border border-pink-300/30 bg-matte-850/90 p-5 shadow-neon-ring transition hover:-translate-y-0.5 hover:border-pink-200/55 hover:shadow-neon-glow"
            >
              <div className="mb-4 inline-flex rounded-lg border border-pink-300/35 bg-pink-300/10 p-2 text-pink-100">
                <item.icon size={18} />
              </div>

              <h2 className="text-lg font-semibold text-slate-50">{item.title}</h2>
              <p className="mt-2 text-sm text-slate-200/90">{item.description}</p>

              <div className="mt-5 inline-flex items-center gap-2 text-sm font-medium text-pink-100">
                <span>{item.cta}</span>
                <ArrowRight size={15} className="transition group-hover:translate-x-0.5" />
              </div>
            </Link>
          ))}
        </section>
      </div>
    </div>
  );
}
