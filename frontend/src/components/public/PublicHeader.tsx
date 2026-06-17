import { Link } from "react-router-dom";

import logoMark from "@/assets/logo-mark.svg";

const navItems = [
  { label: "About", to: "/about" },
  { label: "Centers", to: "/centers" },
  { label: "Collections", to: "/collections" },
  { label: "Contact", to: "/contact" }
];

export function PublicHeader() {
  return (
    <header className="sticky top-0 z-30 border-b border-slate-200/80 bg-white/90 backdrop-blur">
      <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6 lg:px-8">
        <Link to="/" className="flex min-w-0 items-center gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-slate-200 bg-white shadow-sm">
            <img src={logoMark} alt="" className="h-7 w-7" />
          </span>
          <span className="min-w-0">
            <span className="block truncate text-sm font-semibold text-slate-950 sm:text-base">Adarsh Optical Group</span>
            <span className="block truncate text-[11px] font-medium text-slate-500 sm:text-xs">Vision care across Kalyan</span>
          </span>
        </Link>

        <nav className="hidden items-center gap-6 text-sm font-medium text-slate-600 md:flex">
          {navItems.map((item) => (
            <Link key={item.to} to={item.to} className="transition hover:text-slate-950">
              {item.label}
            </Link>
          ))}
        </nav>

        <Link
          to="/crm"
          className="rounded-full bg-slate-950 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800"
        >
          CRM Login
        </Link>
      </div>
    </header>
  );
}
