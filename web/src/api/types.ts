export type PaginationType = "url" | "click" | "scroll" | null;

export interface PaginationSettings {
  type?: PaginationType;
  max_pages?: number;
  param?: string;
  start_page?: number;
  next_selector?: string;
}

export interface ScrapeSettings {
  wait_until?: string;
  timeout?: number;
  pagination?: PaginationSettings;
}

export interface SelectorField {
  selector: string;
  attr?: string;
  transform?: string;
}

export interface Selectors {
  items: string;
  fields: Record<string, SelectorField>;
}

export type JobStatus = "active" | "paused" | "error";

export interface ScrapingJob {
  job_id: string;
  name: string;
  url: string;
  method: "GET" | "POST";
  selectors: Selectors;
  schedule: string;
  tags: string[];
  settings: ScrapeSettings;
  notify_webhook: string | null;
  diff_key: string | null;
  status: JobStatus;
  consecutive_failures: number;
  last_run: string | null;
  next_run: string | null;
  created_at: string;
  updated_at: string;
}

export interface ScrapingJobCreate {
  name: string;
  url: string;
  method?: "GET" | "POST";
  selectors: Selectors;
  schedule?: string;
  tags?: string[];
  settings?: ScrapeSettings;
  notify_webhook?: string | null;
  diff_key?: string | null;
}

export type ScrapingJobUpdate = Partial<ScrapingJobCreate>;

export interface ScrapeResultMetadata {
  duration_ms: number;
  pages_processed: number;
  status: "success" | "partial" | "failed";
  error_message: string | null;
}

export interface ScrapeResult {
  job_id: string;
  run_id: string;
  timestamp: string;
  items_count: number;
  items: Record<string, unknown>[];
  metadata: ScrapeResultMetadata;
}

export interface JobLog {
  job_id: string;
  run_id?: string;
  status: "started" | "completed" | "failed" | "skipped";
  timestamp: string;
  duration_ms?: number;
  items_scraped?: number;
  error_type?: string;
  reason?: string;
}

export interface DryRunResult {
  success: boolean;
  items_count: number;
  items: Record<string, unknown>[];
  truncated: boolean;
  error: string | null;
}

export interface AnalyticsOverview {
  total_jobs: number;
  active_jobs: number;
  paused_jobs: number;
  error_jobs: number;
  total_results: number;
}

export interface SuccessRate {
  total: number;
  successes: number;
  failures: number;
  success_rate: number;
}

export interface SlowestJob {
  job_id: string;
  name: string;
  avg_duration: number;
  last_run: string;
}

export interface JobStat {
  _id: string;
  runs: number;
  total_items: number;
  avg_duration: number;
  errors: number;
}

export interface DiffFieldChange {
  key?: unknown;
  changes: Record<string, { old: unknown; new: unknown }>;
}

export interface DiffResult {
  job_id: string;
  diff_key: string | null;
  run_a: { run_id: string; timestamp: string };
  run_b: { run_id: string; timestamp: string };
  added: Record<string, unknown>[];
  removed: Record<string, unknown>[];
  changed: DiffFieldChange[];
}

export interface RunNowResult {
  job_id: string;
  task_id: string;
  status: string;
}
