import { ArrowRight, BadgeCheck, CalendarCheck, Gem, Glasses, MapPin, ShieldCheck, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";

import { PublicFooter } from "@/components/public/PublicFooter";
import { PublicHeader } from "@/components/public/PublicHeader";

const centers = [
  {
    name: "Adarsh Optical Centre",
    location: "Kalyan",
    type: "Optical centre",
    detail: "Everyday frames, lenses, repairs, and family eyewear support."
  },
  {
    name: "Adarsh Optometric Clinic",
    location: "Khadakpada, Kalyan West",
    type: "Optometric clinic",
    detail: "Clinical eye checks, prescription support, and guided care."
  },
  {
    name: "Adarsh Opticals",
    location: "Near Muxar Hospital",
    type: "Optical centre",
    detail: "Convenient optical service close to hospital and neighborhood needs."
  },
  {
    name: "Adarsh Eye Boutique",
    location: "Kalyan",
    type: "Eye boutique",
    detail: "Premium styling, curated frames, and a more personal fitting experience."
  }
];

const collections = [
  "Prescription eyewear",
  "Sunglasses",
  "Computer lenses",
  "Kids frames",
  "Contact lens guidance",
  "Premium boutique frames"
];

export function PublicHomePage() {
  return (
    <div className="min-h-screen bg-[#fbfaf7] text-slate-950">
      <PublicHeader />

      <main>
        <section className="relative overflow-hidden border-b border-slate-200 bg-[#f4f0ea]">
          <div className="mx-auto grid min-h-[calc(100vh-76px)] max-w-7xl items-center gap-10 px-4 py-12 sm:px-6 lg:grid-cols-[1.02fr_0.98fr] lg:px-8">
            <div className="max-w-3xl">
              <p className="mb-4 inline-flex items-center gap-2 rounded-full border border-slate-300 bg-white px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-slate-600">
                <Sparkles size={14} />
                Four centers. One trusted eye care group.
              </p>
              <h1 className="text-4xl font-semibold leading-tight text-slate-950 sm:text-5xl lg:text-6xl">
                Adarsh Optical Group
              </h1>
              <p className="mt-5 max-w-2xl text-base leading-7 text-slate-600 sm:text-lg">
                Complete optical retail, optometric care, and boutique eyewear styling across Kalyan, built around clear
                guidance and dependable service.
              </p>
              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                <Link
                  to="/centers"
                  className="inline-flex items-center justify-center gap-2 rounded-full bg-slate-950 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800"
                >
                  Explore Centers
                  <ArrowRight size={16} />
                </Link>
                <Link
                  to="/crm"
                  className="inline-flex items-center justify-center rounded-full border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-950 transition hover:border-slate-950"
                >
                  CRM Login
                </Link>
              </div>
            </div>

            <div className="relative min-h-[360px] lg:min-h-[520px]" aria-label="Eyewear showcase">
              <div className="absolute inset-x-6 top-2 h-56 rounded-[2rem] border border-white/70 bg-white/80 shadow-2xl sm:left-12 sm:right-0 sm:h-72" />
              <div className="absolute left-0 top-20 w-[72%] rounded-[2rem] border border-slate-200 bg-slate-950 p-5 text-white shadow-2xl sm:w-[68%]">
                <div className="aspect-[4/3] rounded-2xl bg-[radial-gradient(circle_at_22%_32%,rgba(255,255,255,0.95),transparent_8%),radial-gradient(circle_at_73%_36%,rgba(255,255,255,0.95),transparent_8%),linear-gradient(135deg,#c9a77b_0%,#191919_48%,#7d9d9a_100%)]">
                  <div className="flex h-full items-end justify-between p-5">
                    <span className="rounded-full bg-white/90 px-3 py-1 text-xs font-semibold text-slate-950">Boutique frames</span>
                    <Glasses className="text-white" size={46} />
                  </div>
                </div>
                <p className="mt-4 text-sm leading-6 text-slate-300">
                  Curated frame styling with lenses matched to work, driving, study, and daily comfort.
                </p>
              </div>
              <div className="absolute bottom-2 right-0 w-[62%] rounded-[1.5rem] border border-slate-200 bg-white p-5 shadow-xl">
                <div className="flex items-center gap-3">
                  <span className="rounded-full bg-emerald-50 p-3 text-emerald-700">
                    <ShieldCheck size={24} />
                  </span>
                  <div>
                    <p className="font-semibold text-slate-950">Prescription-first care</p>
                    <p className="mt-1 text-sm text-slate-600">Frames, lenses, records, and follow-ups in sync.</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section id="about" className="border-b border-slate-200 bg-white px-4 py-16 sm:px-6 lg:px-8">
          <div className="mx-auto grid max-w-7xl gap-8 lg:grid-cols-[0.8fr_1.2fr]">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">About</p>
              <h2 className="mt-3 text-3xl font-semibold text-slate-950 sm:text-4xl">Optical care that feels personal.</h2>
            </div>
            <div className="grid gap-4 sm:grid-cols-3">
              {[
                { icon: BadgeCheck, title: "Trusted guidance", body: "Clear recommendations without rushed choices." },
                { icon: CalendarCheck, title: "Daily operations", body: "Built for repeat visits, records, and follow-ups." },
                { icon: Gem, title: "Curated choice", body: "From practical frames to premium boutique selections." }
              ].map((item) => (
                <div key={item.title} className="rounded-lg border border-slate-200 bg-[#fbfaf7] p-5">
                  <item.icon className="text-slate-700" size={22} />
                  <h3 className="mt-4 font-semibold text-slate-950">{item.title}</h3>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{item.body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="centers" className="border-b border-slate-200 bg-[#fbfaf7] px-4 py-16 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-7xl">
            <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">Centers</p>
                <h2 className="mt-3 text-3xl font-semibold text-slate-950 sm:text-4xl">Four Adarsh centers</h2>
              </div>
              <Link to="/contact" className="inline-flex items-center gap-2 text-sm font-semibold text-slate-700 hover:text-slate-950">
                Plan a visit
                <ArrowRight size={16} />
              </Link>
            </div>

            <div className="mt-8 grid gap-4 md:grid-cols-2">
              {centers.map((center) => (
                <article key={center.name} className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
                  <div className="flex items-start gap-4">
                    <span className="rounded-full bg-slate-100 p-3 text-slate-700">
                      <MapPin size={20} />
                    </span>
                    <div>
                      <h3 className="text-lg font-semibold text-slate-950">{center.name}</h3>
                      <p className="mt-1 text-sm font-medium text-slate-600">{center.location}</p>
                      <p className="mt-3 text-sm leading-6 text-slate-600">{center.detail}</p>
                      <p className="mt-4 inline-flex rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">
                        {center.type}
                      </p>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="collections" className="border-b border-slate-200 bg-white px-4 py-16 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-7xl">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">Collections</p>
            <h2 className="mt-3 max-w-3xl text-3xl font-semibold text-slate-950 sm:text-4xl">
              Eyewear for clinics, workdays, schools, screens, and occasions.
            </h2>
            <div className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {collections.map((item) => (
                <div key={item} className="rounded-lg border border-slate-200 bg-[#fbfaf7] px-4 py-4 text-sm font-semibold text-slate-800">
                  {item}
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="contact" className="bg-[#f4f0ea] px-4 py-16 sm:px-6 lg:px-8">
          <div className="mx-auto grid max-w-7xl gap-8 lg:grid-cols-[1fr_1fr]">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">Contact</p>
              <h2 className="mt-3 text-3xl font-semibold text-slate-950 sm:text-4xl">Visit the center closest to you.</h2>
              <p className="mt-4 text-sm leading-6 text-slate-600">
                For appointments, eyewear availability, repairs, or prescription follow-ups, contact your nearest Adarsh
                Optical Group center.
              </p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
              <p className="text-lg font-semibold text-slate-950">Adarsh Optical Group CRM</p>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                Staff and admins can continue to the secure CRM from the public website.
              </p>
              <Link
                to="/crm"
                className="mt-5 inline-flex items-center gap-2 rounded-full bg-slate-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800"
              >
                CRM Login
                <ArrowRight size={16} />
              </Link>
            </div>
          </div>
        </section>
      </main>

      <PublicFooter />
    </div>
  );
}
