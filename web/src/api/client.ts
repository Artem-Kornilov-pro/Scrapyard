import type {
  AnalyticsOverview,
  DiffResult,
  DryRunResult,
  JobLog,
  JobStat,
  RunNowResult,
  ScrapeResult,
  ScrapingJob,
  ScrapingJobCreate,
  ScrapingJobUpdate,
  SlowestJob,
  SuccessRate,
} from "./types";

const API_KEY_STORAGE_KEY = "scrapyard.apiKey";

export function getApiKey(): string {
  return localStorage.getItem(API_KEY_STORAGE_KEY) ?? "";
}

export function setApiKey(key: string): void {
  if (key) {
    localStorage.setItem(API_KEY_STORAGE_KEY, key);
  } else {
    localStorage.removeItem(API_KEY_STORAGE_KEY);
  }
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const apiKey = getApiKey();
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (apiKey) headers.set("X-API-Key", apiKey);

  const response = await fetch(`/api/v1${path}`, { ...options, headers });

  if (!response.ok) {
    let message = response.statusText;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") {
        message = body.detail;
      } else if (Array.isArray(body.detail)) {
        message = body.detail
          .map((e: { loc?: string[]; msg?: string }) =>
            [e.loc?.slice(1).join("."), e.msg].filter(Boolean).join(": "),
          )
          .join("; ");
      }
    } catch {
      // response body wasn't JSON -- keep the statusText fallback
    }
    throw new ApiError(response.status, message);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  // Jobs
  listJobs: (params?: { status?: string; tags?: string[] }) => {
    const qs = new URLSearchParams();
    if (params?.status) qs.set("status", params.status);
    params?.tags?.forEach((t) => qs.append("tags", t));
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return request<ScrapingJob[]>(`/jobs${suffix}`);
  },
  getJob: (id: string) => request<ScrapingJob>(`/jobs/${id}`),
  createJob: (job: ScrapingJobCreate) =>
    request<ScrapingJob>("/jobs", { method: "POST", body: JSON.stringify(job) }),
  updateJob: (id: string, job: ScrapingJobUpdate) =>
    request<ScrapingJob>(`/jobs/${id}`, {
      method: "PUT",
      body: JSON.stringify(job),
    }),
  deleteJob: (id: string) =>
    request<void>(`/jobs/${id}`, { method: "DELETE" }),
  pauseJob: (id: string) =>
    request<ScrapingJob>(`/jobs/${id}/pause`, { method: "POST" }),
  resumeJob: (id: string) =>
    request<ScrapingJob>(`/jobs/${id}/resume`, { method: "POST" }),
  runJob: (id: string) =>
    request<RunNowResult>(`/jobs/${id}/run`, { method: "POST" }),
  dryRun: (payload: {
    url: string;
    selectors: ScrapingJobCreate["selectors"];
    settings?: ScrapingJobCreate["settings"];
  }) =>
    request<DryRunResult>("/jobs/dry-run", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  // Results
  listResults: (jobId: string, params?: { skip?: number; limit?: number }) => {
    const qs = new URLSearchParams();
    if (params?.skip) qs.set("skip", String(params.skip));
    if (params?.limit) qs.set("limit", String(params.limit));
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return request<ScrapeResult[]>(`/jobs/${jobId}/results${suffix}`);
  },
  getDiff: (jobId: string, runA?: string, runB?: string) => {
    const qs = new URLSearchParams();
    if (runA) qs.set("run_a", runA);
    if (runB) qs.set("run_b", runB);
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return request<DiffResult>(`/jobs/${jobId}/results/diff${suffix}`);
  },
  exportUrl: (jobId: string, format: "json" | "csv", runId?: string) => {
    const qs = new URLSearchParams({ format });
    if (runId) qs.set("run_id", runId);
    return `/api/v1/jobs/${jobId}/results/export?${qs.toString()}`;
  },

  // Logs
  getJobLogs: (jobId: string, params?: { skip?: number; limit?: number }) => {
    const qs = new URLSearchParams();
    if (params?.skip) qs.set("skip", String(params.skip));
    if (params?.limit) qs.set("limit", String(params.limit));
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return request<JobLog[]>(`/jobs/${jobId}/logs${suffix}`);
  },

  // Analytics
  getOverview: () => request<AnalyticsOverview>("/analytics/overview"),
  getSuccessRate: (days = 7) =>
    request<SuccessRate>(`/analytics/success-rate?days=${days}`),
  getSlowestJobs: (limit = 5) =>
    request<SlowestJob[]>(`/analytics/slowest?limit=${limit}`),
  getJobStats: (jobId: string, days = 30) =>
    request<JobStat[]>(`/analytics/jobs/${jobId}/stats?days=${days}`),
};
