import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryOptions,
} from "@tanstack/react-query";

import { api } from "@/api/client";
import type {
  RunNowResult,
  ScrapingJob,
  ScrapingJobCreate,
  ScrapingJobUpdate,
} from "@/api/types";

export function useJobs(status?: string) {
  return useQuery({
    queryKey: ["jobs", { status }],
    queryFn: () => api.listJobs(status ? { status } : undefined),
    refetchInterval: 15_000,
  });
}

export function useJob(id: string, options?: Partial<UseQueryOptions<ScrapingJob>>) {
  return useQuery({
    queryKey: ["jobs", id],
    queryFn: () => api.getJob(id),
    refetchInterval: 10_000,
    ...options,
  });
}

export function useCreateJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (job: ScrapingJobCreate) => api.createJob(job),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  });
}

export function useUpdateJob(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (job: ScrapingJobUpdate) => api.updateJob(id, job),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
}

export function useDeleteJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteJob(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  });
}

export function useJobAction(action: "pause" | "resume" | "run") {
  const qc = useQueryClient();
  return useMutation<ScrapingJob | RunNowResult, Error, string>({
    mutationFn: (id: string) => {
      if (action === "pause") return api.pauseJob(id);
      if (action === "resume") return api.resumeJob(id);
      return api.runJob(id);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  });
}

export function useDryRun() {
  return useMutation({ mutationFn: api.dryRun });
}

export function useResults(jobId: string) {
  return useQuery({
    queryKey: ["results", jobId],
    queryFn: () => api.listResults(jobId, { limit: 20 }),
    enabled: !!jobId,
  });
}

export function useDiff(jobId: string, runA?: string, runB?: string) {
  return useQuery({
    queryKey: ["diff", jobId, runA, runB],
    queryFn: () => api.getDiff(jobId, runA, runB),
    enabled: !!jobId,
    retry: false,
  });
}

export function useJobLogs(jobId: string) {
  return useQuery({
    queryKey: ["logs", jobId],
    queryFn: () => api.getJobLogs(jobId, { limit: 30 }),
    enabled: !!jobId,
    refetchInterval: 10_000,
  });
}

export function useOverview() {
  return useQuery({
    queryKey: ["analytics", "overview"],
    queryFn: api.getOverview,
    refetchInterval: 20_000,
  });
}

export function useSuccessRate(days = 7) {
  return useQuery({
    queryKey: ["analytics", "success-rate", days],
    queryFn: () => api.getSuccessRate(days),
  });
}

export function useSlowestJobs(limit = 5) {
  return useQuery({
    queryKey: ["analytics", "slowest", limit],
    queryFn: () => api.getSlowestJobs(limit),
  });
}

export function useJobStats(jobId: string, days = 30) {
  return useQuery({
    queryKey: ["analytics", "job-stats", jobId, days],
    queryFn: () => api.getJobStats(jobId, days),
    enabled: !!jobId,
  });
}
