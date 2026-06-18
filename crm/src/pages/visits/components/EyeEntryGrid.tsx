import { ClinicalSelect } from "@/pages/visits/components/ClinicalSelect";

export type EyePayload = Record<string, string>;
export type EyeEntryValue = {
  right?: EyePayload;
  left?: EyePayload;
  both?: EyePayload;
};

export type EyeFieldConfig = {
  key: string;
  label: string;
  options?: string[];
};

type EyeEntryGridProps = {
  title: string;
  value: EyeEntryValue;
  fields: EyeFieldConfig[];
  rows?: Array<"right" | "left" | "both">;
  onChange: (value: EyeEntryValue) => void;
  disabled?: boolean;
};

const EYE_LABELS = {
  right: "Right Eye",
  left: "Left Eye",
  both: "Both Eyes"
} as const;

function readEyeValue(value: EyeEntryValue, eye: "right" | "left" | "both", field: string): string {
  return value[eye]?.[field] ?? "";
}

export function EyeEntryGrid({ title, value, fields, rows = ["right", "left"], onChange, disabled = false }: EyeEntryGridProps) {
  const update = (eye: "right" | "left" | "both", field: string, nextValue: string) => {
    onChange({
      ...value,
      [eye]: {
        ...(value[eye] ?? {}),
        [field]: nextValue
      }
    });
  };

  return (
    <div className="space-y-3 rounded-xl border border-pink-300/20 bg-matte-800/70 p-4">
      <h4 className="text-sm font-semibold uppercase tracking-wide text-pink-100">{title}</h4>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead className="border-b border-pink-300/15 text-xs uppercase tracking-wide text-slate-400">
            <tr>
              <th className="w-24 py-2 pr-3">Eye</th>
              {fields.map((field) => (
                <th key={field.key} className="py-2 pr-3">
                  {field.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((eye) => (
              <tr key={eye} className="border-b border-slate-700/55 last:border-0">
                <td className="py-3 pr-3 font-medium text-slate-100">{EYE_LABELS[eye]}</td>
                {fields.map((field) => (
                  <td key={field.key} className="py-3 pr-3">
                    {field.options ? (
                      <ClinicalSelect
                        label={`${title} ${eye} ${field.label}`}
                        value={readEyeValue(value, eye, field.key)}
                        options={field.options}
                        onChange={(next) => update(eye, field.key, next)}
                        disabled={disabled}
                      />
                    ) : (
                      <input
                        aria-label={`${title} ${eye} ${field.label}`}
                        disabled={disabled}
                        value={readEyeValue(value, eye, field.key)}
                        onChange={(event) => update(eye, field.key, event.target.value)}
                        className="h-10 w-full rounded-lg border border-pink-300/25 bg-matte-900 px-3 text-sm text-slate-100 outline-none focus:border-pink-200"
                      />
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
