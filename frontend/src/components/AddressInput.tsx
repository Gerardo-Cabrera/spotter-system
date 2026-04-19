import { useEffect, useRef, useState } from "react";
import { autocompleteAddress } from "../api";
import { MapPin } from "lucide-react";

interface Props {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}

export default function AddressInput({ label, value, onChange, placeholder }: Props) {
  const [suggestions, setSuggestions] = useState<{ display_name: string }[]>([]);
  const [open, setOpen] = useState(false);
  const [focused, setFocused] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = setTimeout(async () => {
      if (!focused || value.trim().length < 3) {
        setSuggestions([]);
        return;
      }
      const results = await autocompleteAddress(value);
      setSuggestions(results);
      setOpen(results.length > 0);
    }, 300);
    return () => clearTimeout(handler);
  }, [value, focused]);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  return (
    <div className="relative" ref={boxRef}>
      <label className="block text-xs font-semibold text-slate-600 mb-1 uppercase tracking-wide">
        {label}
      </label>
      <div className="relative">
        <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => {
            setFocused(true);
            if (suggestions.length) setOpen(true);
          }}
          placeholder={placeholder}
          className="w-full pl-9 pr-3 py-2.5 rounded-lg border border-slate-300 bg-white focus:ring-2 focus:ring-brand-500 focus:border-brand-500 outline-none text-sm"
          autoComplete="off"
        />
      </div>
      {open && suggestions.length > 0 && (
        <ul className="absolute z-50 mt-1 w-full bg-white border border-slate-200 rounded-lg shadow-lg max-h-60 overflow-auto">
          {suggestions.map((s, i) => (
            <li
              key={i}
              onMouseDown={(e) => {
                e.preventDefault();
                onChange(s.display_name);
                setOpen(false);
              }}
              className="px-3 py-2 text-sm hover:bg-brand-50 cursor-pointer border-b border-slate-100 last:border-0"
            >
              {s.display_name}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
