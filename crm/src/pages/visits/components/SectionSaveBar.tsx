import { AlertCircle, CheckCircle2, Loader2, Save } from "lucide-react";

type SaveState = "idle" | "dirty" | "saving" | "saved" | "failed";

type SectionSaveBarProps = {
  saveState: SaveState;
  errorMessage?: string | null;
  disabled?: boolean;
  onSave: () => void;
};

export function SectionSaveBar({ saveState, errorMessage, disabled = false, onSave }: SectionSaveBarProps) {
  const isSaving = saveState === "saving";

  return (
    <div className="sticky bottom-3 z-10 rounded-xl border border-pink-300/20 bg-matte-900/95 p-3 shadow-neon-ring backdrop-blur">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="text-sm">
          {saveState === "saving" && (
            <p className="inline-flex items-center gap-2 text-slate-200">
              <Loader2 className="animate-spin" size={16} />
              Saving
            </p>
          )}
          {saveState === "saved" && (
            <p className="inline-flex items-center gap-2 text-emerald-200">
              <CheckCircle2 size={16} />
              Saved
            </p>
          )}
          {saveState === "failed" && (
            <div className="space-y-1 text-rose-200">
              <p className="inline-flex items-center gap-2 font-medium">
                <AlertCircle size={16} />
                Save failed
              </p>
              {errorMessage && <p className="text-xs">{errorMessage}</p>}
            </div>
          )}
          {(saveState === "dirty" || saveState === "idle") && (
            <p className={saveState === "dirty" ? "text-amber-100" : "text-slate-300"}>
              {saveState === "dirty" ? "Unsaved changes" : "No unsaved changes"}
            </p>
          )}
        </div>

        <button
          type="button"
          disabled={disabled || isSaving}
          onClick={onSave}
          className="inline-flex items-center justify-center gap-2 rounded-lg border border-pink-300/45 bg-pink-500/15 px-4 py-2 text-sm font-medium text-pink-50 hover:bg-neon-pink/20 disabled:cursor-not-allowed disabled:opacity-55"
        >
          {isSaving ? <Loader2 className="animate-spin" size={16} /> : <Save size={16} />}
          Save Section
        </button>
      </div>
    </div>
  );
}
