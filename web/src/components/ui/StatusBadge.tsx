import { AlertTriangle, CheckCircle2, PauseCircle } from "lucide-react";

import type { JobStatus } from "@/api/types";

// Fixed status palette (never reused for chart series identity), each
// always paired with an icon + label so status is never color-alone.
const STATUS_CONFIG: Record<
  JobStatus,
  { label: string; color: string; bg: string; icon: typeof CheckCircle2 }
> = {
  active: { label: "Active", color: "#0ca30c", bg: "rgb(12 163 12 / 0.1)", icon: CheckCircle2 },
  paused: { label: "Paused", color: "#fab219", bg: "rgb(250 178 25 / 0.14)", icon: PauseCircle },
  error: { label: "Error", color: "#d03b3b", bg: "rgb(208 59 59 / 0.1)", icon: AlertTriangle },
};

export function StatusBadge({ status }: { status: JobStatus }) {
  const cfg = STATUS_CONFIG[status];
  const Icon = cfg.icon;
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium"
      style={{ color: cfg.color, backgroundColor: cfg.bg }}
    >
      <Icon className="size-3.5" strokeWidth={2.25} />
      {cfg.label}
    </span>
  );
}
