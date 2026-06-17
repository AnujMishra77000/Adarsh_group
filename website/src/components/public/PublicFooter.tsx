import { Eye } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import { crmUrl } from "@/config";

const centers = ["Adarsh Optical Centre", "Adarsh Optometric Clinic", "Adarsh Opticals", "Adarsh Eye Boutique"];
const services = ["Comprehensive Eye Exams", "Frame Fitting & Styling", "Lens Consultation", "Children's Eye Care"];

export function PublicFooter() {
  return (
    <footer className="bg-[#06143a] text-white">
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-[1.35fr_0.9fr_0.9fr_1fr]">
          <div>
            <div className="flex items-center gap-3">
              <span className="grid h-11 w-11 place-items-center rounded-full bg-[#ffd700] text-[#071a4a]">
                <Eye size={25} />
              </span>
              <span>
                <span className="block text-sm font-extrabold uppercase">Adarsh Optical Group</span>
                <span className="block text-xs font-semibold text-blue-100">Est. 1985 - Kalyan</span>
              </span>
            </div>
            <p className="mt-5 max-w-sm text-sm leading-7 text-blue-100">
              Trusted eye care, authentic branded eyewear, and premium optical services in Kalyan since 1985.
            </p>
            <div className="mt-5 flex gap-2" aria-label="Social media links">
              {["IG", "FB", "G"].map((item) => (
                <a
                  key={item}
                  href="#contact"
                  className="grid h-9 w-9 place-items-center rounded-full border border-white/15 text-xs font-bold transition hover:border-[#ffd700] hover:text-[#ffd700]"
                >
                  {item}
                </a>
              ))}
            </div>
          </div>

          <FooterColumn title="Our Centers">
            {centers.map((center) => (
              <Link key={center} to="/centers">
                {center}
              </Link>
            ))}
          </FooterColumn>

          <FooterColumn title="Services">
            {services.map((service) => (
              <Link key={service} to="/#services">
                {service}
              </Link>
            ))}
          </FooterColumn>

          <FooterColumn title="Contact Info">
            <span>Kalyan, Maharashtra, India</span>
            <span>+91 XXXXX XXXXX</span>
            <span>info@adarshopticalgroup.com</span>
            <span>Store timings placeholder</span>
            <a
              href={crmUrl}
              className="mt-2 inline-flex w-fit rounded-full bg-[#ffd700] px-4 py-2 text-sm font-extrabold text-[#071a4a] transition hover:bg-[#ffe66c]"
            >
              CRM Login
            </a>
          </FooterColumn>
        </div>

        <div className="mt-10 flex flex-col gap-3 border-t border-white/10 pt-6 text-sm text-blue-100 sm:flex-row sm:items-center sm:justify-between">
          <span>Copyright 2026 Adarsh Optical Group. All Rights Reserved.</span>
          <strong className="text-[#ffd700]">Seeing Better. Looking Better. Living Better.</strong>
        </div>
      </div>
    </footer>
  );
}

function FooterColumn({ children, title }: { children: ReactNode; title: string }) {
  return (
    <div className="flex flex-col gap-2 text-sm text-blue-100">
      <h3 className="mb-2 text-base font-extrabold text-white">{title}</h3>
      {children}
    </div>
  );
}
