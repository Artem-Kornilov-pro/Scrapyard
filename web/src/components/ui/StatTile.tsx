import { Card } from "./Card";

interface StatTileProps {
  label: string;
  value: string | number;
  accent?: string;
}

export function StatTile({ label, value, accent }: StatTileProps) {
  return (
    <Card className="p-4">
      <p className="text-xs font-medium text-slate-500 dark:text-slate-400">{label}</p>
      <p
        className="mt-1.5 text-2xl font-semibold tabular-nums text-slate-900 dark:text-white"
        style={accent ? { color: accent } : undefined}
      >
        {value}
      </p>
    </Card>
  );
}
