const API = "http://localhost:8000";

export type ColumnProfile = {
  dtype: string;
  null_count: number;
  null_pct: number;
  unique_count: number;
  min: number | null;
  max: number | null;
  is_array: boolean;
};

export type ColumnInfo = {
  name: string;
  isArray: boolean;
};

export type DatasetProfile = {
  row_count: number;
  column_count: number;
  duplicate_rows: number;
  columns: Record<string, ColumnProfile>;
};

export type Violation = {
  column: string;
  rule: string;
  message: string;
  failed_count: number;
  failed_rows: number[];
};

export type Summary = {
  total_violations: number;
  rules_failed: string[];
  columns_flagged: string[];
};

async function post(path: string, form: FormData): Promise<any> {
  const r = await fetch(`${API}${path}`, { method: "POST", body: form });
  const body = await r.json();
  if (!r.ok) throw new Error(body.detail || body.error || `HTTP ${r.status}`);
  return body;
}

export function profile(
  file: File,
): Promise<{ profile: DatasetProfile; starter_rules_yaml: string }> {
  const fd = new FormData();
  fd.append("file", file);
  return post("/datasets/profile", fd);
}

export function validateSample(
  file: File,
  rulesYaml: string,
): Promise<{ sample_rows: number; violations: Violation[]; summary: Summary }> {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("rules_yaml", rulesYaml);
  return post("/datasets/validate-sample", fd);
}

export function createJob(
  file: File,
  rulesYaml: string,
): Promise<{ job_id: string; status: string }> {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("rules_yaml", rulesYaml);
  return post("/jobs", fd);
}

export async function getJob(jobId: string): Promise<any> {
  const r = await fetch(`${API}/jobs/${jobId}`);
  return r.json();
}

export function exportUrl(jobId: string, kind: "clean" | "quarantine"): string {
  return `${API}/jobs/${jobId}/export/${kind}`;
}
