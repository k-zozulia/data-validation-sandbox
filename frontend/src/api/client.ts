// Typed client for the backend API. All paths are relative to /api, which is
// proxied to the backend by Vite (dev) or nginx (Docker).
const API = (import.meta.env.VITE_API_URL ?? "") + "/api";

// ---------- types ----------

export type TopValue = { value: string; count: number };
export type HistogramBin = { start: number; end: number; count: number };

export type ColumnProfile = {
  dtype: string;
  inferred_type: string;
  semantic_type: string | null;
  null_count: number;
  null_pct: number;
  unique_count: number;
  unique_pct: number;
  min: number | null;
  max: number | null;
  mean: number | null;
  median: number | null;
  std: number | null;
  min_length: number | null;
  max_length: number | null;
  top_values: TopValue[];
  histogram: HistogramBin[];
  sample_values: unknown[];
  is_array: boolean;
};

export type DatasetProfile = {
  row_count: number;
  column_count: number;
  duplicate_rows: number;
  missing_cells: number;
  missing_cells_pct: number;
  memory_bytes: number;
  columns: Record<string, ColumnProfile>;
};

export type LastJob = {
  id: string;
  mode: JobMode;
  status: JobStatus;
  score: number | null;
  created_at: string;
};

export type Dataset = {
  id: string;
  name: string;
  filename: string;
  format: string;
  size_bytes: number;
  row_count: number;
  column_count: number;
  created_at: string;
  updated_at: string;
  last_job: LastJob | null;
};

export type DatasetDetail = Dataset & { profile: DatasetProfile; rules_yaml: string };

export type RowIssue = { column: string; rule: string; severity: Severity };
export type Row = { _row: number; values: Record<string, unknown>; issues: RowIssue[] };
export type RowsPage = {
  total: number;
  offset: number;
  limit: number;
  columns: string[];
  rows: Row[];
};

export type Severity = "error" | "warning";
export type LintIssue = {
  path: (string | number)[];
  message: string;
  severity: Severity;
  line: number | null;
};
export type LintResult = { valid: boolean; checks: number; issues: LintIssue[] };

export type ParamSpec = {
  name: string;
  kind: "number" | "text" | "select" | "boolean" | "list" | "column" | "columns";
  required: boolean;
  default: unknown;
  options: string[] | null;
  placeholder: string | null;
  common: boolean;
};
export type RuleType = {
  name: string;
  label: string;
  description: string;
  scope: "column" | "dataset";
  applies_to: "scalar" | "array" | "any";
  params: ParamSpec[];
};

export type RuleSet = {
  id: string;
  name: string;
  description: string;
  rules_yaml: string;
  created_at: string;
  updated_at: string;
};

export type Violation = {
  column: string;
  rule: string;
  severity: Severity;
  message: string;
  failed_count: number;
  failed_rows: number[];
  sample_values: unknown[];
};

export type ColumnSummary = {
  checks: number;
  failed_checks: number;
  error_rows: number;
  warning_rows: number;
};

export type JobSummary = {
  dataset_rows: number;
  rows_checked: number;
  clean_rows: number;
  quarantine_rows: number;
  warning_rows: number;
  warning_only_rows: number;
  checks_total: number;
  checks_failed: number;
  checks_passed: number;
  errors: number;
  warnings: number;
  total_failures: number;
  score: number;
  rules_failed: string[];
  columns_flagged: string[];
  columns: Record<string, ColumnSummary>;
};

export type JobMode = "sample" | "full";
export type JobStatus = "queued" | "running" | "succeeded" | "failed";

export type Job = {
  id: string;
  dataset_id: string;
  rule_set_id: string | null;
  mode: JobMode;
  status: JobStatus;
  progress: number;
  summary: JobSummary | null;
  error: { error: string; detail?: string; issues?: LintIssue[] } | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
};

export type JobDetail = Job & {
  rules_yaml: string;
  violations: Violation[] | null;
  dataset_name: string | null;
};

export type Health = {
  status: string;
  database: string;
  redis: string;
  storage: string;
  inline_jobs: boolean;
};

export type RowFilter = "all" | "issues" | "errors" | "warnings" | "clean";
export type ExportKind = "clean" | "quarantine" | "annotated";
export type ExportFormat = "csv" | "json" | "parquet" | "xlsx";

// ---------- transport ----------

export class ApiError extends Error {
  status: number;
  code: string;
  issues: LintIssue[];

  constructor(status: number, body: any) {
    super(body?.detail || body?.error || `HTTP ${status}`);
    this.status = status;
    this.code = body?.error ?? "http_error";
    this.issues = body?.issues ?? [];
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (init.body && !(init.body instanceof FormData)) headers["Content-Type"] = "application/json";
  const r = await fetch(`${API}${path}`, { ...init, headers: { ...headers, ...init.headers } });
  if (r.status === 204) return undefined as T;
  const text = await r.text();
  const body = text ? JSON.parse(text) : null;
  if (!r.ok) throw new ApiError(r.status, body);
  return body as T;
}

const json = (method: string, data: unknown): RequestInit => ({
  method,
  body: JSON.stringify(data),
});

function qs(params: Record<string, string | number | undefined | null>): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(params))
    if (v !== undefined && v !== null && v !== "") p.set(k, String(v));
  const s = p.toString();
  return s ? `?${s}` : "";
}

// ---------- endpoints ----------

export const api = {
  health: () => request<Health>("/health"),

  listDatasets: () => request<Dataset[]>("/datasets"),
  getDataset: (id: string) => request<DatasetDetail>(`/datasets/${id}`),
  uploadDataset: (file: File, name?: string) => {
    const fd = new FormData();
    fd.append("file", file);
    if (name) fd.append("name", name);
    return request<DatasetDetail>("/datasets", { method: "POST", body: fd });
  },
  updateDataset: (id: string, patch: { name?: string; rules_yaml?: string }) =>
    request<DatasetDetail>(`/datasets/${id}`, json("PATCH", patch)),
  deleteDataset: (id: string) => request<void>(`/datasets/${id}`, { method: "DELETE" }),
  datasetRows: (id: string, offset: number, limit: number) =>
    request<RowsPage>(`/datasets/${id}/rows${qs({ offset, limit })}`),
  suggestedRules: (id: string) =>
    request<{ rules_yaml: string }>(`/datasets/${id}/suggested-rules`),
  datasetJobs: (id: string) => request<Job[]>(`/datasets/${id}/jobs`),

  ruleCatalog: () => request<RuleType[]>("/rules/catalog"),
  lintRules: (rules_yaml: string, dataset_id?: string) =>
    request<LintResult>("/rules/lint", json("POST", { rules_yaml, dataset_id })),

  listRuleSets: () => request<RuleSet[]>("/rule-sets"),
  createRuleSet: (data: { name: string; description?: string; rules_yaml: string }) =>
    request<RuleSet>("/rule-sets", json("POST", data)),
  updateRuleSet: (
    id: string,
    data: Partial<Pick<RuleSet, "name" | "description" | "rules_yaml">>,
  ) => request<RuleSet>(`/rule-sets/${id}`, json("PATCH", data)),
  deleteRuleSet: (id: string) => request<void>(`/rule-sets/${id}`, { method: "DELETE" }),

  createJob: (data: {
    dataset_id: string;
    mode: JobMode;
    rules_yaml?: string;
    rule_set_id?: string;
  }) => request<JobDetail>("/jobs", json("POST", data)),
  listJobs: () => request<Job[]>("/jobs"),
  getJob: (id: string) => request<JobDetail>(`/jobs/${id}`),
  deleteJob: (id: string) => request<void>(`/jobs/${id}`, { method: "DELETE" }),
  jobRows: (id: string, filter: RowFilter, offset: number, limit: number, column?: string) =>
    request<RowsPage>(`/jobs/${id}/rows${qs({ filter, offset, limit, column })}`),
  exportUrl: (id: string, kind: ExportKind, format: ExportFormat) =>
    `${API}/jobs/${id}/export/${kind}${qs({ format })}`,
};
