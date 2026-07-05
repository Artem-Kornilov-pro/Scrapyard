import { clsx } from "clsx";
import { motion } from "framer-motion";
import { Pause, Play, Plus, RefreshCw, Trash2 } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { ConfirmDialog } from "@/components/ConfirmDialog";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useDeleteJob, useJobAction, useJobs } from "@/hooks/useJobs";
import { formatRelative, truncate } from "@/lib/format";
import type { JobStatus, ScrapingJob } from "@/api/types";

const FILTERS: { label: string; value: JobStatus | undefined }[] = [
  { label: "All", value: undefined },
  { label: "Active", value: "active" },
  { label: "Paused", value: "paused" },
  { label: "Error", value: "error" },
];

export function JobsListPage() {
  const [filter, setFilter] = useState<JobStatus | undefined>(undefined);
  const { data: jobs, isLoading, isError } = useJobs(filter);
  const pauseAction = useJobAction("pause");
  const resumeAction = useJobAction("resume");
  const runAction = useJobAction("run");
  const deleteJob = useDeleteJob();
  const [pendingDelete, setPendingDelete] = useState<ScrapingJob | null>(null);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900 dark:text-white">
            Scraping Jobs
          </h1>
          <p className="mt-0.5 text-sm text-slate-500 dark:text-slate-400">
            Manage schedules, run jobs on demand, and inspect results.
          </p>
        </div>
        <Link to="/jobs/new">
          <Button>
            <Plus className="size-4" />
            New Job
          </Button>
        </Link>
      </div>

      <div className="mb-4 flex gap-1">
        {FILTERS.map((f) => (
          <button
            key={f.label}
            onClick={() => setFilter(f.value)}
            className={clsx(
              "rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
              filter === f.value
                ? "bg-slate-900 text-white dark:bg-white dark:text-slate-900"
                : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800",
            )}
          >
            {f.label}
          </button>
        ))}
      </div>

      <Card className="overflow-hidden">
        {isLoading && (
          <div className="divide-y divide-slate-100 dark:divide-slate-800">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-14 animate-pulse bg-slate-50 dark:bg-slate-800/40" />
            ))}
          </div>
        )}

        {isError && (
          <div className="p-8 text-center text-sm text-slate-500">
            Couldn't reach the API. Check your connection or API key.
          </div>
        )}

        {!isLoading && !isError && jobs?.length === 0 && (
          <div className="flex flex-col items-center justify-center gap-3 py-16">
            <p className="text-sm text-slate-500 dark:text-slate-400">
              No jobs yet — create your first one.
            </p>
            <Link to="/jobs/new">
              <Button size="sm">
                <Plus className="size-4" />
                New Job
              </Button>
            </Link>
          </div>
        )}

        {!isLoading && !isError && jobs && jobs.length > 0 && (
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-400 dark:border-slate-800">
                <th className="px-4 py-3 font-medium">Name</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Schedule</th>
                <th className="px-4 py-3 font-medium">Next run</th>
                <th className="px-4 py-3 font-medium">Tags</th>
                <th className="px-4 py-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job, i) => (
                <motion.tr
                  key={job.job_id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: i * 0.02 }}
                  className="border-b border-slate-100 last:border-0 hover:bg-slate-50 dark:border-slate-800/60 dark:hover:bg-slate-800/40"
                >
                  <td className="px-4 py-3">
                    <Link
                      to={`/jobs/${job.job_id}`}
                      className="font-medium text-slate-900 hover:text-brand-600 dark:text-white dark:hover:text-brand-400"
                    >
                      {job.name}
                    </Link>
                    <div className="text-xs text-slate-400">{truncate(job.url, 48)}</div>
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={job.status} />
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-slate-500 dark:text-slate-400">
                    {job.schedule}
                  </td>
                  <td className="px-4 py-3 text-slate-500 dark:text-slate-400">
                    {formatRelative(job.next_run)}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {job.tags.slice(0, 3).map((tag) => (
                        <span
                          key={tag}
                          className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        title="Run now"
                        onClick={() => runAction.mutate(job.job_id)}
                        className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 hover:text-brand-600 dark:text-slate-400 dark:hover:bg-slate-700"
                      >
                        <RefreshCw className="size-4" />
                      </button>
                      {job.status === "paused" ? (
                        <button
                          title="Resume"
                          onClick={() => resumeAction.mutate(job.job_id)}
                          className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 hover:text-emerald-600 dark:text-slate-400 dark:hover:bg-slate-700"
                        >
                          <Play className="size-4" />
                        </button>
                      ) : (
                        <button
                          title="Pause"
                          onClick={() => pauseAction.mutate(job.job_id)}
                          className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 hover:text-amber-600 dark:text-slate-400 dark:hover:bg-slate-700"
                        >
                          <Pause className="size-4" />
                        </button>
                      )}
                      <button
                        title="Delete"
                        onClick={() => setPendingDelete(job)}
                        className="rounded-md p-1.5 text-slate-500 hover:bg-rose-50 hover:text-rose-600 dark:text-slate-400 dark:hover:bg-rose-500/10"
                      >
                        <Trash2 className="size-4" />
                      </button>
                    </div>
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <ConfirmDialog
        open={!!pendingDelete}
        title={`Delete "${pendingDelete?.name}"?`}
        description="This deletes the job configuration. Past results and logs are kept."
        confirmLabel="Delete"
        danger
        loading={deleteJob.isPending}
        onCancel={() => setPendingDelete(null)}
        onConfirm={() => {
          if (!pendingDelete) return;
          deleteJob.mutate(pendingDelete.job_id, {
            onSuccess: () => setPendingDelete(null),
          });
        }}
      />
    </div>
  );
}
