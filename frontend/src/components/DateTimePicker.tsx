import { useEffect, useRef, useState } from "react";
import { Calendar } from "lucide-react";

/**
 * Date + time picker with an explicit **OK** button.
 *
 * We cannot inject buttons into a native `<input type="datetime-local">`
 * overlay — it is drawn by the browser. So we render a button that shows
 * the current selection, a popover with separate `date` and `time` fields,
 * and **Cancel / OK** actions: the user commits explicitly instead of the
 * picker auto-closing on every partial change.
 *
 * Contract:
 *   - `value` is always in the `YYYY-MM-DDTHH:mm` format (empty string
 *     when nothing is selected) so it is a drop-in replacement for the
 *     native input's value and plays nicely with the rest of the form
 *     (and the existing ISO-on-submit conversion in TripForm).
 */

interface Props {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}

function splitDt(dt: string): { date: string; time: string } {
  if (!dt) return { date: "", time: "" };
  const [d, t] = dt.split("T");
  return { date: d ?? "", time: (t ?? "").slice(0, 5) };
}

function formatDisplay(dt: string): string {
  if (!dt) return "";
  try {
    return new Date(dt).toLocaleString(undefined, {
      weekday: "short",
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return dt;
  }
}

export default function DateTimePicker({ value, onChange, placeholder }: Props) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState(() => splitDt(value));
  const rootRef = useRef<HTMLDivElement>(null);

  // Keep the draft in sync if the external value changes while closed.
  useEffect(() => {
    if (!open) setDraft(splitDt(value));
  }, [value, open]);

  // Dismiss on click-outside or Escape (standard popover UX).
  useEffect(() => {
    if (!open) return;
    const onDocMouseDown = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
        setDraft(splitDt(value));
      }
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
        setDraft(splitDt(value));
      }
    };
    document.addEventListener("mousedown", onDocMouseDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onDocMouseDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open, value]);

  // An empty state (both fields cleared) is valid — it means "no departure".
  const canCommit = (!!draft.date && !!draft.time) || (!draft.date && !draft.time);

  const commit = () => {
    if (!canCommit) return;
    onChange(draft.date && draft.time ? `${draft.date}T${draft.time}` : "");
    setOpen(false);
  };
  const cancel = () => {
    setDraft(splitDt(value));
    setOpen(false);
  };
  const clear = () => {
    setDraft({ date: "", time: "" });
    onChange("");
    setOpen(false);
  };

  return (
    <div className="relative" ref={rootRef}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="dialog"
        aria-expanded={open}
        className="w-full px-3 py-2.5 rounded-lg border border-slate-300 bg-white focus:ring-2 focus:ring-brand-500 focus:border-brand-500 outline-none text-sm text-left flex items-center justify-between gap-2"
      >
        <span className={value ? "text-slate-900" : "text-slate-400"}>
          {value ? formatDisplay(value) : (placeholder ?? "Pick a date and time")}
        </span>
        <Calendar className="w-4 h-4 text-slate-400" aria-hidden />
      </button>

      {open && (
        <div
          role="dialog"
          aria-label="Pick a date and time"
          className="absolute z-50 mt-1 left-0 right-0 bg-white rounded-lg border border-slate-200 shadow-lg p-3 space-y-3"
        >
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-[10px] font-semibold text-slate-500 mb-1 uppercase tracking-wide">
                Date
              </label>
              <input
                type="date"
                value={draft.date}
                onChange={(e) => setDraft((d) => ({ ...d, date: e.target.value }))}
                className="w-full px-2 py-1.5 rounded border border-slate-300 text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500 outline-none"
              />
            </div>
            <div>
              <label className="block text-[10px] font-semibold text-slate-500 mb-1 uppercase tracking-wide">
                Time
              </label>
              <input
                type="time"
                value={draft.time}
                onChange={(e) => setDraft((d) => ({ ...d, time: e.target.value }))}
                className="w-full px-2 py-1.5 rounded border border-slate-300 text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500 outline-none"
              />
            </div>
          </div>

          <div className="flex items-center justify-between gap-2">
            <button
              type="button"
              onClick={clear}
              className="text-xs text-slate-500 hover:text-slate-700 px-2 py-1 rounded"
            >
              Clear
            </button>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={cancel}
                className="text-xs px-3 py-1.5 rounded border border-slate-300 text-slate-700 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={commit}
                disabled={!canCommit}
                className="text-xs px-4 py-1.5 rounded bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed font-semibold"
              >
                OK
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
