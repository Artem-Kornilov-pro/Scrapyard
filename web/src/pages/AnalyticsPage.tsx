import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Card } from "@/components/ui/Card";
import { StatTile } from "@/components/ui/StatTile";
import { useOverview, useSlowestJobs, useSuccessRate } from "@/hooks/useJobs";

// Roles pulled from the validated reference palette (dataviz skill) --
// categorical slot 1 for magnitude, fixed status colors for good/critical.
const SERIES_BLUE = "#2a78d6";
const STATUS_GOOD = "#0ca30c";
const STATUS_CRITICAL = "#d03b3b";

const RANGE_OPTIONS = [7, 30, 90];

export function AnalyticsPage() {
  const [days, setDays] = useState(7);
  const { data: overview, isLoading: overviewLoading } = useOverview();
  const { data: successRate, isLoading: rateLoading } = useSuccessRate(days);
  const { data: slowest, isLoading: slowestLoading } = useSlowestJobs(8);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900 dark:text-white">Analytics</h1>
        <p className="mt-0.5 text-sm text-slate-500 dark:text-slate-400">
          System-wide overview of jobs and scrape performance.
        </p>
      </div>

      {overviewLoading ? (
        <SkeletonGrid count={5} />
      ) : (
        overview && (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
            <StatTile label="Total jobs" value={overview.total_jobs} />
            <StatTile label="Active" value={overview.active_jobs} accent={STATUS_GOOD} />
            <StatTile label="Paused" value={overview.paused_jobs} accent="#fab219" />
            <StatTile label="Error" value={overview.error_jobs} accent={STATUS_CRITICAL} />
            <StatTile label="Total results" value={overview.total_results} />
          </div>
        )
      )}

      <Card className="p-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-900 dark:text-white">
            Success rate
          </h2>
          <div className="flex gap-1">
            {RANGE_OPTIONS.map((d) => (
              <button
                key={d}
                onClick={() => setDays(d)}
                className={`rounded-md px-2 py-1 text-xs font-medium ${
                  days === d
                    ? "bg-slate-900 text-white dark:bg-white dark:text-slate-900"
                    : "text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
                }`}
              >
                {d}d
              </button>
            ))}
          </div>
        </div>

        {rateLoading || !successRate ? (
          <div className="h-16 animate-pulse rounded-lg bg-slate-100 dark:bg-slate-800" />
        ) : successRate.total === 0 ? (
          <p className="text-sm text-slate-500 dark:text-slate-400">
            No runs in the selected window.
          </p>
        ) : (
          <div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-semibold tabular-nums text-slate-900 dark:text-white">
                {successRate.success_rate}%
              </span>
              <span className="text-sm text-slate-500 dark:text-slate-400">
                {successRate.successes} succeeded · {successRate.failures} failed · {successRate.total} total
              </span>
            </div>
            <div className="mt-3 flex h-2.5 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
              <div
                className="h-full"
                style={{
                  width: `${(successRate.successes / successRate.total) * 100}%`,
                  backgroundColor: STATUS_GOOD,
                }}
                title={`${successRate.successes} succeeded`}
              />
              <div
                className="h-full"
                style={{
                  width: `${(successRate.failures / successRate.total) * 100}%`,
                  backgroundColor: STATUS_CRITICAL,
                }}
                title={`${successRate.failures} failed`}
              />
            </div>
            <div className="mt-2 flex gap-4 text-xs text-slate-500 dark:text-slate-400">
              <LegendDot color={STATUS_GOOD} label="Succeeded" />
              <LegendDot color={STATUS_CRITICAL} label="Failed" />
            </div>
          </div>
        )}
      </Card>

      <Card className="p-5">
        <h2 className="mb-4 text-sm font-semibold text-slate-900 dark:text-white">
          Slowest active jobs
        </h2>
        {slowestLoading ? (
          <div className="h-64 animate-pulse rounded-lg bg-slate-100 dark:bg-slate-800" />
        ) : !slowest || slowest.length === 0 ? (
          <p className="text-sm text-slate-500 dark:text-slate-400">
            No successful runs yet.
          </p>
        ) : (
          <ResponsiveContainer width="100%" height={Math.max(160, slowest.length * 42)}>
            <BarChart
              data={slowest.map((s) => ({ ...s, seconds: +(s.avg_duration / 1000).toFixed(2) }))}
              layout="vertical"
              margin={{ left: 8, right: 24, top: 4, bottom: 4 }}
              barCategoryGap={10}
            >
              <CartesianGrid horizontal={false} stroke="currentColor" className="text-slate-100 dark:text-slate-800" />
              <XAxis
                type="number"
                tickFormatter={(v) => `${v}s`}
                stroke="currentColor"
                className="text-xs text-slate-400"
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                type="category"
                dataKey="name"
                width={140}
                stroke="currentColor"
                className="text-xs text-slate-500 dark:text-slate-400"
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                cursor={{ fill: "rgba(148, 163, 184, 0.1)" }}
                formatter={(value: number) => [`${value}s`, "Avg duration"]}
                contentStyle={{
                  borderRadius: 8,
                  border: "1px solid #e2e8f0",
                  fontSize: 12,
                }}
              />
              <Bar dataKey="seconds" radius={[0, 4, 4, 0]} maxBarSize={22}>
                {slowest.map((_, i) => (
                  <Cell key={i} fill={SERIES_BLUE} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </Card>
    </div>
  );
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="size-2 rounded-full" style={{ backgroundColor: color }} />
      {label}
    </span>
  );
}

function SkeletonGrid({ count }: { count: number }) {
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
      {[...Array(count)].map((_, i) => (
        <div key={i} className="h-20 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800" />
      ))}
    </div>
  );
}
