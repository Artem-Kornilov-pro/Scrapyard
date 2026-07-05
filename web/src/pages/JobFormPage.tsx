import { ArrowLeft, FlaskConical } from "lucide-react";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { ApiError } from "@/api/client";
import type { PaginationType, Selectors } from "@/api/types";
import { SelectorsEditor, type FieldRow } from "@/components/SelectorsEditor";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { FieldError, FieldHint, Input, Label } from "@/components/ui/Field";
import { useCreateJob, useDryRun, useJob, useUpdateJob } from "@/hooks/useJobs";

function fieldsToSelectors(itemsSelector: string, fields: FieldRow[]): Selectors {
  const result: Selectors = { items: itemsSelector, fields: {} };
  for (const f of fields) {
    if (!f.name || !f.selector) continue;
    result.fields[f.name] = {
      selector: f.selector,
      ...(f.attr && f.attr !== "text" ? { attr: f.attr } : {}),
      ...(f.transform ? { transform: f.transform } : {}),
    };
  }
  return result;
}

function selectorsToFields(selectors: Selectors | undefined): FieldRow[] {
  if (!selectors?.fields) return [];
  return Object.entries(selectors.fields).map(([name, cfg]) => ({
    name,
    selector: cfg.selector,
    attr: cfg.attr ?? "text",
    transform: cfg.transform ?? "",
  }));
}

export function JobFormPage() {
  const { id } = useParams();
  const isEdit = !!id;
  const navigate = useNavigate();

  const { data: existing } = useJob(id ?? "", { enabled: isEdit });
  const createJob = useCreateJob();
  const updateJob = useUpdateJob(id ?? "");
  const dryRun = useDryRun();

  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [method, setMethod] = useState<"GET" | "POST">("GET");
  const [schedule, setSchedule] = useState("0 */6 * * *");
  const [tags, setTags] = useState("");
  const [notifyWebhook, setNotifyWebhook] = useState("");
  const [diffKey, setDiffKey] = useState("");
  const [itemsSelector, setItemsSelector] = useState("");
  const [fields, setFields] = useState<FieldRow[]>([
    { name: "title", selector: "", attr: "text", transform: "" },
  ]);
  const [paginationType, setPaginationType] = useState<PaginationType>(null);
  const [maxPages, setMaxPages] = useState(1);

  useEffect(() => {
    if (!existing) return;
    setName(existing.name);
    setUrl(existing.url);
    setMethod(existing.method);
    setSchedule(existing.schedule);
    setTags(existing.tags.join(", "));
    setNotifyWebhook(existing.notify_webhook ?? "");
    setDiffKey(existing.diff_key ?? "");
    setItemsSelector(existing.selectors.items);
    setFields(selectorsToFields(existing.selectors));
    setPaginationType(existing.settings.pagination?.type ?? null);
    setMaxPages(existing.settings.pagination?.max_pages ?? 1);
  }, [existing]);

  const selectors = useMemo(() => fieldsToSelectors(itemsSelector, fields), [
    itemsSelector,
    fields,
  ]);

  const mutation = isEdit ? updateJob : createJob;
  const submitError =
    mutation.error instanceof ApiError ? mutation.error.message : mutation.error ? "Something went wrong." : null;
  const dryRunError =
    dryRun.error instanceof ApiError ? dryRun.error.message : dryRun.error ? "Dry run failed." : null;

  function buildPayload() {
    return {
      name,
      url,
      method,
      schedule,
      tags: tags
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean),
      selectors,
      settings: {
        wait_until: "networkidle",
        timeout: 30,
        pagination: { type: paginationType, max_pages: maxPages },
      },
      notify_webhook: notifyWebhook || null,
      diff_key: diffKey || null,
    };
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const payload = buildPayload();
    const onSuccess = (job: { job_id: string }) => navigate(`/jobs/${job.job_id}`);
    if (isEdit) {
      updateJob.mutate(payload, { onSuccess });
    } else {
      createJob.mutate(payload, { onSuccess });
    }
  }

  function handleDryRun() {
    dryRun.mutate({ url, selectors, settings: { pagination: { type: paginationType, max_pages: maxPages } } });
  }

  return (
    <div className="mx-auto max-w-3xl">
      <button
        onClick={() => navigate(-1)}
        className="mb-4 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
      >
        <ArrowLeft className="size-4" />
        Back
      </button>

      <h1 className="mb-6 text-xl font-semibold text-slate-900 dark:text-white">
        {isEdit ? "Edit Job" : "New Scraping Job"}
      </h1>

      <form onSubmit={handleSubmit} className="space-y-6">
        <Card className="p-5">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Product Prices"
              />
            </div>
            <div>
              <Label htmlFor="method">Method</Label>
              <select
                id="method"
                value={method}
                onChange={(e) => setMethod(e.target.value as "GET" | "POST")}
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800"
              >
                <option value="GET">GET</option>
                <option value="POST">POST</option>
              </select>
            </div>
          </div>

          <div className="mt-4">
            <Label htmlFor="url">Target URL</Label>
            <Input
              id="url"
              required
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com/products"
            />
          </div>

          <div className="mt-4 grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="schedule">Schedule (cron)</Label>
              <Input
                id="schedule"
                required
                value={schedule}
                onChange={(e) => setSchedule(e.target.value)}
                className="font-mono text-xs"
              />
              <FieldHint>e.g. "0 */6 * * *" — every 6 hours</FieldHint>
            </div>
            <div>
              <Label htmlFor="tags">Tags (comma separated)</Label>
              <Input
                id="tags"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                placeholder="ecommerce, prices"
              />
            </div>
          </div>
        </Card>

        <Card className="p-5">
          <h2 className="mb-3 text-sm font-semibold text-slate-900 dark:text-white">
            Selectors
          </h2>
          <SelectorsEditor
            itemsSelector={itemsSelector}
            onItemsSelectorChange={setItemsSelector}
            fields={fields}
            onFieldsChange={setFields}
          />

          <div className="mt-4 grid grid-cols-2 gap-4 border-t border-slate-100 pt-4 dark:border-slate-800">
            <div>
              <Label htmlFor="pagination">Pagination</Label>
              <select
                id="pagination"
                value={paginationType ?? ""}
                onChange={(e) =>
                  setPaginationType((e.target.value || null) as PaginationType)
                }
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800"
              >
                <option value="">None</option>
                <option value="url">URL param</option>
                <option value="click">Click "next"</option>
                <option value="scroll">Infinite scroll</option>
              </select>
            </div>
            <div>
              <Label htmlFor="max-pages">Max pages</Label>
              <Input
                id="max-pages"
                type="number"
                min={1}
                value={maxPages}
                onChange={(e) => setMaxPages(Number(e.target.value))}
                disabled={!paginationType}
              />
            </div>
          </div>

          <div className="mt-4 flex items-center justify-between rounded-lg bg-slate-50 p-3 dark:bg-slate-800/50">
            <div>
              <Button type="button" variant="secondary" size="sm" onClick={handleDryRun} loading={dryRun.isPending}>
                <FlaskConical className="size-3.5" />
                Test selectors
              </Button>
              {dryRunError && <FieldError>{dryRunError}</FieldError>}
            </div>
            {dryRun.data && (
              <span className="text-xs text-slate-500 dark:text-slate-400">
                {dryRun.data.success
                  ? `Found ${dryRun.data.items_count} item(s)`
                  : "Selectors matched nothing or the page failed to load"}
              </span>
            )}
          </div>

          {dryRun.data && dryRun.data.items.length > 0 && (
            <pre className="mt-3 max-h-64 overflow-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-100 scrollbar-thin">
              {JSON.stringify(dryRun.data.items, null, 2)}
            </pre>
          )}
        </Card>

        <Card className="p-5">
          <h2 className="mb-3 text-sm font-semibold text-slate-900 dark:text-white">
            Notifications &amp; diffing
          </h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="webhook">Webhook on failure</Label>
              <Input
                id="webhook"
                type="url"
                value={notifyWebhook}
                onChange={(e) => setNotifyWebhook(e.target.value)}
                placeholder="https://hooks.example.com/alert"
              />
              <FieldHint>Fires after 5 consecutive failed runs.</FieldHint>
            </div>
            <div>
              <Label htmlFor="diff-key">Diff key</Label>
              <Input
                id="diff-key"
                value={diffKey}
                onChange={(e) => setDiffKey(e.target.value)}
                placeholder="title"
              />
              <FieldHint>Matches items across runs for per-field diffing.</FieldHint>
            </div>
          </div>
        </Card>

        {submitError && (
          <div className="rounded-lg bg-rose-50 p-3 text-sm text-rose-700 dark:bg-rose-500/10 dark:text-rose-400">
            {submitError}
          </div>
        )}

        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={() => navigate(-1)}>
            Cancel
          </Button>
          <Button type="submit" loading={mutation.isPending}>
            {isEdit ? "Save changes" : "Create job"}
          </Button>
        </div>
      </form>
    </div>
  );
}
