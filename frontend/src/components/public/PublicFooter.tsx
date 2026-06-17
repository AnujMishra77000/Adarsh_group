import { Link } from "react-router-dom";

export function PublicFooter() {
  return (
    <footer className="border-t border-slate-200 bg-slate-950 text-white">
      <div className="mx-auto grid max-w-7xl gap-8 px-4 py-10 sm:px-6 md:grid-cols-[1.2fr_0.8fr_0.8fr] lg:px-8">
        <div>
          <p className="text-lg font-semibold">Adarsh Optical Group</p>
          <p className="mt-3 max-w-md text-sm leading-6 text-slate-300">
            Optical retail, optometric care, and boutique eyewear guidance for families and professionals across Kalyan.
          </p>
        </div>
        <div className="space-y-2 text-sm text-slate-300">
          <p className="font-semibold text-white">Visit</p>
          <Link to="/centers" className="block hover:text-white">
            Centers
          </Link>
          <Link to="/collections" className="block hover:text-white">
            Collections
          </Link>
          <Link to="/contact" className="block hover:text-white">
            Contact
          </Link>
        </div>
        <div className="space-y-3 text-sm text-slate-300">
          <p className="font-semibold text-white">Operations</p>
          <Link
            to="/crm"
            className="inline-flex rounded-full bg-white px-4 py-2 font-semibold text-slate-950 transition hover:bg-slate-100"
          >
            CRM Login
          </Link>
        </div>
      </div>
    </footer>
  );
}
