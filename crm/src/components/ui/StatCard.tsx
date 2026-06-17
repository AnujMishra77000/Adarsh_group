type StatCardProps = {
  label: string;
  value: string;
  hint: string;
};

export function StatCard({ label, value, hint }: StatCardProps) {
  return (
    <div className="rounded-xl border border-pink-400/20 bg-matte-850/85 p-4 shadow-neon-ring">
      <p className="text-xs uppercase tracking-wide text-slate-400">{label}</p>
      <p className="mt-3 text-2xl font-semibold text-pink-100">{value}</p>
      <p className="mt-1 text-xs text-slate-500">{hint}</p>
    </div>
  );
}
