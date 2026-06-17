import { Eye, Menu, X } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { crmUrl } from "@/config";

const navItems = [
  { label: "Home", to: "/" },
  { label: "About Us", to: "/about" },
  { label: "Our Centers", to: "/centers" },
  { label: "Collections", to: "/collections" },
  { label: "Services", to: "/#services" },
  { label: "Contact", to: "/contact" }
];

export function PublicHeader() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 border-b border-white/10 bg-[#0a1f5c]/95 text-white shadow-lg shadow-blue-950/10 backdrop-blur">
      <div className="mx-auto flex min-h-[76px] w-full max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        <Link to="/" className="flex min-w-0 items-center gap-3" onClick={() => setIsOpen(false)}>
          <span className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-[#ffd700] text-[#071a4a]">
            <Eye size={25} />
          </span>
          <span className="min-w-0">
            <span className="block truncate text-sm font-extrabold uppercase sm:text-base">Adarsh Optical Group</span>
            <span className="block truncate text-[11px] font-semibold text-blue-100 sm:text-xs">
              Est. 1985 - Kalyan's Most Trusted
            </span>
          </span>
        </Link>

        <nav className="hidden items-center gap-6 text-sm font-semibold text-blue-50 lg:flex" aria-label="Primary navigation">
          {navItems.map((item) => (
            <Link key={item.to} to={item.to} className="transition hover:text-[#ffd700]">
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          <a
            className="hidden rounded-full bg-[#ffd700] px-4 py-2 text-sm font-extrabold text-[#071a4a] shadow-sm transition hover:bg-[#ffe66c] sm:inline-flex"
            href="#contact"
          >
            Book Eye Test
          </a>
          <a
            className="hidden rounded-full border border-white/25 px-4 py-2 text-sm font-extrabold text-white transition hover:border-[#ffd700] hover:text-[#ffd700] md:inline-flex"
            href={crmUrl}
          >
            CRM Login
          </a>
          <button
            type="button"
            aria-label="Open navigation menu"
            aria-expanded={isOpen}
            className="grid h-10 w-10 place-items-center rounded-full border border-white/20 text-white lg:hidden"
            onClick={() => setIsOpen((value) => !value)}
          >
            {isOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>

      {isOpen ? (
        <div className="border-t border-white/10 bg-[#071a4a] px-4 py-4 lg:hidden">
          <nav className="mx-auto flex max-w-7xl flex-col gap-3 text-sm font-semibold text-blue-50" aria-label="Mobile navigation">
            {navItems.map((item) => (
              <Link
                key={item.to}
                to={item.to}
                className="rounded-lg px-3 py-2 transition hover:bg-white/10 hover:text-[#ffd700]"
                onClick={() => setIsOpen(false)}
              >
                {item.label}
              </Link>
            ))}
            <a
              href={crmUrl}
              className="rounded-lg border border-white/20 px-3 py-2 font-extrabold text-white transition hover:border-[#ffd700] hover:text-[#ffd700]"
              onClick={() => setIsOpen(false)}
            >
              CRM Login
            </a>
          </nav>
        </div>
      ) : null}
    </header>
  );
}
