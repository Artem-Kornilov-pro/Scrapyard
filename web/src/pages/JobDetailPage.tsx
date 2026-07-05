import {
  ArrowLeft,
  Download,
  ExternalLink,
  Pencil,
  RefreshCw,
} from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { ApiError } from "@/api/client";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Tabs } from "@/components/ui/Tabs";
import {
  useDeleteJob,
  useDiff,
  useJob,
  useJobAction,
  useJobLogs,
  useResults,
} from "@/hooks/useJobs";
import { formatDateTime, formatDuration, formatRelative } from "@/lib/format";
import { api } from "@/api/client";

const LOG_STATUS_STYLE: Record<string, string> = {
  completed: "text-emerald-600 dark:text-emerald-400",
  started: "text-slate-500 dark:text-slate-400",
  failed: "text-rose-600 dark:text-rose-400",
  skipped: "text-amber-600 dark:text-amber-400",
};

export function JobDetailPage() {
  const { id } = useParams();
  const jobId = id!;
  const navigate = useNavigate();
  const [tab, setTab] = useState("results");
  const [confirmDelete, setConfirmDelete] = useState(false);

  const { data: job, isLoading } = useJob(jobId);
  const runAction = useJobAction("run");
  const deleteJob = useDeleteJob();

  if (isLoading || !job) {
    return <div className="h-40 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800" />;
  }

  return (
    <div>
      <button
        onClick={() => navigate("/")}
        className="mb-4 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
      >
        <ArrowLeft className="size-4" />
        All jobs
      </button>

      <div className="mb-6 flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-semibold text-slate-900 dark:text-white">
              {job.name}
            </h1>
            <StatusBadge status={job.status} />
          </div>
          <a
            href={job.url}
            target="_blank"
            rel="noreferrer"
            className="mt-1 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-brand-600 dark:text-slate-400"
          >
            {job.url}
            <ExternalLink className="size-3" />
          </a>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" onClick={() => runAction.mutate(jobId)} loading={runAction.isPending}>
            <RefreshCw className="size-3.5" />
            Run now
          </Button>
          <Link to={`/jobs/${jobId}/edit`}>
            <Button variant="secondary" size="sm">
              <Pencil className="size-3.5" />
              Edit
            </Button>
          </Link>
          <Button variant="danger" size="sm" onClick={() => setConfirmDelete(true)}>
            Delete
          </Button>
        </div>
      </div>

      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <SummaryStat label="Schedule" value={job.schedule} mono />
        <SummaryStat label="Last run" value={formatRelative(job.last_run)} />
        <SummaryStat label="Next run" value={formatRelative(job.next_run)} />
        <SummaryStat label="Consecutive failures" value={String(job.consecutive_failures)} />
      </div>

      {job.tags.length > 0 && (
        <div className="mb-6 flex flex-wrap gap-1.5">
          {job.tags.map((t) => (
            <span
              key={t}
              className="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-300"
            >
              {t}
            </span>
          ))}
        </div>
      )}

      <Tabs
        value={tab}
        onChange={setTab}
        tabs={[
          { value: "results", label: "Results" },
          { value: "logs", label: "Logs" },
          { value: "diff", label: "Diff" },
        ]}
      />

      <div className="mt-4">
        {tab === "results" && <ResultsTab jobId={jobId} />}
        {tab === "logs" && <LogsTab jobId={jobId} />}
        {tab === "diff" && <DiffTab jobId={jobId} />}
      </div>

      <ConfirmDialog
        open={confirmDelete}
        title={`Delete "${job.name}"?`}
        description="This deletes the job configuration. Past results and logs are kept."
        confirmLabel="Delete"
        danger
        loading={deleteJob.isPending}
        onCancel={() => setConfirmDelete(false)}
        onConfirm={() =>
          deleteJob.mutate(jobId, { onSuccess: () => navigate("/") })
        }
      />
    </div>
  );
}

function SummaryStat({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <Card className="p-3">
      <p className="text-xs text-slate-500 dark:text-slate-400">{label}</p>
      <p className={`mt-1 truncate text-sm font-medium text-slate-900 dark:text-white ${mono ? "font-mono" : ""}`}>
        {value}
      </p>
    </Card>
  );
}

function ResultsTab({ jobId }: { jobId: string }) {
  const { data: results, isLoading } = useResults(jobId);

  if (isLoading) return <div className="h-32 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800" />;
  if (!results || results.length === 0) {
    return <EmptyState text="No runs yet. Click “Run now” to scrape for the first time." />;
  }

  return (
    <Card className="overflow-hidden">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-400 dark:border-slate-800">
            <th className="px-4 py-3 font-medium">Run</th>
            <th className="px-4 py-3 font-medium">Status</th>
            <th className="px-4 py-3 font-medium">Items</th>
            <th className="px-4 py-3 font-medium">Duration</th>
            <th className="px-4 py-3 font-medium text-right">Export</th>
          </tr>
        </thead>
        <tbody>
          {results.map((r) => (
            <tr
              key={r.run_id}
              className="border-b border-slate-100 last:border-0 dark:border-slate-800/60"
            >
              <td className="px-4 py-3 text-slate-700 dark:text-slate-300">
                {formatDateTime(r.timestamp)}
              </td>
              <td className="px-4 py-3">
                <span
                  className={
                    r.metadata.status === "success"
                      ? "text-emerald-600 dark:text-emerald-400"
                      : "text-rose-600 dark:text-rose-400"
                  }
                >
                  {r.metadata.status}
                </span>
              </td>
              <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{r.items_count}</td>
              <td className="px-4 py-3 text-slate-500 dark:text-slate-400">
                {formatDuration(r.metadata.duration_ms)}
              </td>
              <td className="px-4 py-3 text-right">
                <a
                  href={api.exportUrl(jobId, "json", r.run_id)}
                  className="mr-2 text-xs text-slate-500 hover:text-brand-600 dark:text-slate-400"
                >
                  JSON
                </a>
                <a
                  href={api.exportUrl(jobId, "csv", r.run_id)}
                  className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-brand-600 dark:text-slate-400"
                >
                  <Download className="size-3" />
                  CSV
                </a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

function LogsTab({ jobId }: { jobId: string }) {
  const { data: logs, isLoading } = useJobLogs(jobId);

  if (isLoading) return <div className="h-32 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800" />;
  if (!logs || logs.length === 0) return <EmptyState text="No logs yet." />;

  return (
    <Card className="max-h-96 divide-y divide-slate-100 overflow-auto scrollbar-thin dark:divide-slate-800/60">
      {logs.map((log, i) => (
        <div key={i} className="flex items-center justify-between px-4 py-2.5 text-sm">
          <div className="flex items-center gap-3">
            <span className={`font-medium ${LOG_STATUS_STYLE[log.status] ?? ""}`}>
              {log.status}
            </span>
            {log.reason && (
              <span className="text-xs text-slate-400">{log.reason}</span>
            )}
            {log.error_type && (
              <span className="text-xs text-rose-500">{log.error_type}</span>
            )}
          </div>
          <div className="flex items-center gap-3 text-xs text-slate-400">
            {typeof log.items_scraped === "number" && <span>{log.items_scraped} items</span>}
            {typeof log.duration_ms === "number" && <span>{formatDuration(log.duration_ms)}</span>}
            <span>{formatDateTime(log.timestamp)}</span>
          </div>
        </div>
      ))}
    </Card>
  );
}

function DiffTab({ jobId }: { jobId: string }) {
  const { data: diff, isLoading, isError, error } = useDiff(jobId);

  if (isLoading) return <div className="h-32 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800" />;
  if (isError) {
    const message = error instanceof ApiError ? error.message : "Not enough runs to diff yet.";
    return <EmptyState text={message} />;
  }
  if (!diff) return null;

  return (
    <div className="space-y-4">
      <p className="text-xs text-slate-500 dark:text-slate-400">
        Comparing {formatDateTime(diff.run_a.timestamp)} → {formatDateTime(diff.run_b.timestamp)}
        {diff.diff_key && <> · matched by <code>{diff.diff_key}</code></>}
      </p>

      <DiffSection title="Added" items={diff.added} color="text-emerald-600 dark:text-emerald-400" />
      <DiffSection title="Removed" items={diff.removed} color="text-rose-600 dark:text-rose-400" />

      {diff.changed.length > 0 && (
        <Card className="p-4">
          <h3 className="mb-2 text-sm font-semibold text-amber-600 dark:text-amber-400">
            Changed ({diff.changed.length})
          </h3>
          <div className="space-y-2">
            {diff.changed.map((c, i) => (
              <div key={i} className="rounded-lg bg-slate-50 p-2.5 text-xs dark:bg-slate-800/60">
                {c.key !== undefined && (
                  <p className="mb-1 font-medium text-slate-700 dark:text-slate-300">{String(c.key)}</p>
                )}
                {Object.entries(c.changes).map(([field, change]) => (
                  <p key={field} className="text-slate-500 dark:text-slate-400">
                    <span className="font-medium">{field}</span>:{" "}
                    <span className="text-rose-500 line-through">{JSON.stringify(change.old)}</span>{" "}
                    → <span className="text-emerald-600 dark:text-emerald-400">{JSON.stringify(change.new)}</span>
                  </p>
                ))}
              </div>
            ))}
          </div>
        </Card>
      )}

      {diff.added.length === 0 && diff.removed.length === 0 && diff.changed.length === 0 && (
        <EmptyState text="No differences between the two most recent runs." />
      )}
    </div>
  );
}

function DiffSection({ title, items, color }: { title: string; items: Record<string, unknown>[]; color: string }) {
  if (items.length === 0) return null;
  return (
    <Card className="p-4">
      <h3 className={`mb-2 text-sm font-semibold ${color}`}>
        {title} ({items.length})
      </h3>
      <pre className="max-h-48 overflow-auto text-xs text-slate-600 scrollbar-thin dark:text-slate-400">
        {JSON.stringify(items, null, 2)}
      </pre>
    </Card>
  );
}

function EmptyState({ text }: { text: string }) {
  return (
    <div className="rounded-xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
      {text}
    </div>
  );
}
