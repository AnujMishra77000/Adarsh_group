type ClinicalSelectProps = {
  label: string;
  value: string;
  options: string[];
  customValue?: string;
  onChange: (value: string) => void;
  onCustomChange?: (value: string) => void;
  disabled?: boolean;
};

export function ClinicalSelect({ label, value, options, customValue = "", onChange, onCustomChange, disabled = false }: ClinicalSelectProps) {
  const knownValue = options.includes(value) ? value : "custom";

  return (
    <label className="block text-sm text-slate-200">
      <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-400">{label}</span>
      <select
        disabled={disabled}
        value={knownValue}
        onChange={(event) => {
          const next = event.target.value;
          if (next === "custom") {
            onChange(customValue || "");
            return;
          }
          onChange(next);
        }}
        className="h-10 w-full rounded-lg border border-pink-300/25 bg-matte-900 px-3 text-sm text-slate-100 outline-none focus:border-pink-200"
      >
        {options.map((option) => (
          <option key={option || "blank"} value={option}>
            {option || "Select"}
          </option>
        ))}
        <option value="custom">Custom</option>
      </select>

      {knownValue === "custom" && (
        <input
          disabled={disabled}
          value={customValue || value}
          onChange={(event) => {
            onCustomChange?.(event.target.value);
            onChange(event.target.value);
          }}
          placeholder="Custom value"
          className="mt-2 h-10 w-full rounded-lg border border-pink-300/25 bg-matte-900 px-3 text-sm text-slate-100 outline-none focus:border-pink-200"
        />
      )}
    </label>
  );
}
