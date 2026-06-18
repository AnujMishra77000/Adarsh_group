import { Circle, CircleCheck, Clock, MinusCircle } from "lucide-react";

import { SECTION_STATE_LABELS } from "@/pages/visits/examSections";
import type { ExamSectionState, VisitExamSection } from "@/types/visit";

type ExamSectionNavProps = {
  sections: VisitExamSection[];
  activeKey: string;
  onSelect: (section: VisitExamSection) => void;
  onActivateContactLens: (section: VisitExamSection) => void;
  activatingContactLens?: boolean;
};

function stateIcon(state: ExamSectionState) {
  if (state === "complete") return CircleCheck;
  if (state === "not_applicable") return MinusCircle;
  if (state === "future") return Clock;
  return Circle;
}

export function ExamSectionNav({ sections, activeKey, onSelect, onActivateContactLens, activatingContactLens = false }: ExamSectionNavProps) {
  const visibleSections = sections.filter((section) => section.is_visible || section.is_disabled);
  const conditionalSections = sections.filter((section) => !section.is_visible && !section.is_disabled);

  return (
    <aside className="space-y-4">
      <div className="rounded-2xl border border-pink-300/20 bg-matte-850/90 p-3 shadow-neon-ring">
        <p className="mb-3 px-1 text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">Sections</p>
        <nav className="space-y-1">
          {visibleSections.map((section) => {
            const Icon = stateIcon(section.state);
            const active = activeKey === section.key;
            return (
              <button
                key={section.key}
                type="button"
                disabled={section.is_disabled}
                onClick={() => onSelect(section)}
                className={`flex w-full items-start gap-2 rounded-lg border px-3 py-2 text-left text-sm transition ${
                  active
                    ? "border-pink-300/45 bg-pink-400/10 text-pink-50"
                    : "border-transparent text-slate-200 hover:border-pink-300/25 hover:bg-matte-800/70"
                } disabled:cursor-not-allowed disabled:opacity-55`}
              >
                <Icon className="mt-0.5 shrink-0" size={15} />
                <span className="min-w-0 flex-1">
                  <span className="block font-medium">{section.title}</span>
                  <span className="block text-xs text-slate-400">{SECTION_STATE_LABELS[section.state]}</span>
                </span>
              </button>
            );
          })}
        </nav>
      </div>

      {conditionalSections.length > 0 && (
        <div className="rounded-2xl border border-slate-600/45 bg-matte-850/70 p-3 text-xs text-slate-300">
          <p className="font-semibold uppercase tracking-wide text-slate-400">Conditional</p>
          {conditionalSections.map((section) => (
            section.key === "contact_lens" ? (
              <button
                key={section.key}
                type="button"
                disabled={activatingContactLens}
                onClick={() => onActivateContactLens(section)}
                className="mt-2 w-full rounded-lg border border-indigo-300/35 bg-indigo-400/10 px-3 py-2 text-left text-xs font-semibold text-indigo-100 disabled:opacity-50"
              >
                {activatingContactLens ? "Starting Contact Lens Work-up..." : "Start Contact Lens Work-up"}
              </button>
            ) : (
              <p key={section.key} className="mt-2">
                {section.title} appears when it is relevant for this visit.
              </p>
            )
          ))}
        </div>
      )}
    </aside>
  );
}
