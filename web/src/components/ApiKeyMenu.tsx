import { KeyRound } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { getApiKey, setApiKey } from "@/api/client";

export function ApiKeyMenu() {
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState(getApiKey());
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  function save() {
    setApiKey(value.trim());
    setOpen(false);
  }

  const active = !!getApiKey();

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
        title="API key"
      >
        <KeyRound className="size-4" />
        {active ? "Key set" : "No key"}
      </button>
      {open && (
        <div className="absolute right-0 z-20 mt-2 w-72 rounded-xl border border-slate-200 bg-white p-3 shadow-lg dark:border-slate-800 dark:bg-slate-900">
          <p className="mb-2 text-xs text-slate-500 dark:text-slate-400">
            Sent as <code className="rounded bg-slate-100 px-1 dark:bg-slate-800">X-API-Key</code>{" "}
            on every request. Leave empty if the API doesn't require auth.
          </p>
          <input
            type="password"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="API_KEY"
            className="mb-2 w-full rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-800"
            onKeyDown={(e) => e.key === "Enter" && save()}
          />
          <button
            onClick={save}
            className="w-full rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700"
          >
            Save
          </button>
        </div>
      )}
    </div>
  );
}
