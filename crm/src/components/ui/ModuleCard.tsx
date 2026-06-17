import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";

type ModuleCardProps = {
  title: string;
  description: string;
  to: string;
};

export function ModuleCard({ title, description, to }: ModuleCardProps) {
  return (
    <Link
      to={to}
      className="group rounded-2xl border border-pink-400/20 bg-matte-850/80 p-5 shadow-neon-ring transition duration-200 hover:border-pink-300/40 hover:shadow-neon-glow"
    >
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-base font-semibold text-slate-100">{title}</h3>
        <ArrowRight size={16} className="text-pink-300 transition group-hover:translate-x-0.5" />
      </div>
      <p className="text-sm text-slate-400">{description}</p>
    </Link>
  );
}
