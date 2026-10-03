import { Download, FileCode2, FlaskConical, History, RefreshCw, Trash2 } from "lucide-react";
import { useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import {
  api,
  type ExportFormat,
  type ExportKind,
  type JobDetail,
  type RowFilter,
} from "../api/client";
import { useCreateJob, useDeleteJob, useJob, useJobRows } from "../api/hooks";
import { JobStatusBadge, ModeBadge } from "../components/Badges";
import DataGrid from "../components/DataGrid";
import RulesEditor from "../components/RulesEditor";
import { IssuesByColumnChart, RowComposition } from "../components/StatsDashboard";
import { useToast } from "../components/Toaster";
import {
  Alert,
  Button,
  Card,
  EmptyState,
  Loading,
  PageHeader,
  ProgressBar,
  Segmented,
  Select,
  Stat,
} from "../components/ui";
import ViolationsTable from "../components/ViolationsTable";
import { duration, formatNumber, formatPct, scoreTone, timeAgo } from "../utils/format";

export default function JobPage() {
  const { id = "" } = useParams();
  const { data: job, isLoading, error } = useJob(id);

  if (isLoading) return <Loading />;
  if (error || !job)
    return (
      <EmptyState icon={<History className="size-10" />} title="Run not found">
        {error?.message}
      </EmptyState>
    );

  return (
    <>
      <Header job={job} />
      {(job.status === "queued" || job.status === "running") && (
        <Card>
          <div className="mb-2 flex items-center justify-between text-sm">
            <span className="font-medium">
              {job.status === "queued" ? "Waiting for a worker…" : "Validating…"}
            </span>
            <span className="tabular-nums text-zinc-500">{job.progress}%</span>
          </div>
          <ProgressBar value={job.progress} />
          <p className="mt-3 text-xs text-zinc-500">
            You can leave this page — the run continues in the background and shows up under{" "}
            <b>Validation runs</b>.
          </p>
        </Card>
      )}
      {job.status === "failed" && (
        <Alert title={`Run failed: ${job.error?.error ?? "unknown error"}`}>
          {job.error?.detail}
          {job.error?.issues && (
            <ul className="mt-1 list-inside list-disc text-xs">
              {job.error.issues.map((i, k) => (
                <li key={k}>
                  <span className="font-mono">{i.path.join(".")}</span> {i.message}
                </li>
              ))}
            </ul>
          )}
        </Alert>
      )}
      {job.status === "succeeded" && <Results job={job} />}
      <RulesSnapshot yaml={job.rules_yaml} />
    </>
  );
}

function Header({ job }: { job: JobDetail }) {
  const createJob = useCreateJob();
  const remove = useDeleteJob();
  const navigate = useNavigate();
  const toast = useToast();
  const active = job.status === "queued" || job.status === "running";

  return (
    <PageHeader
      icon={
        job.mode === "sample" ? <FlaskConical className="size-5" /> : <History className="size-5" />
      }
      title={
        <span className="flex flex-wrap items-center gap-2">
          Validation run <ModeBadge mode={job.mode} />{" "}
          <JobStatusBadge status={job.status} progress={job.progress} />
        </span>
      }
      subtitle={
        <span className="flex flex-wrap gap-x-2">
          <Link
            to={`/datasets/${job.dataset_id}`}
            className="font-medium text-indigo-600 hover:underline dark:text-indigo-400"
          >
            {job.dataset_name ?? "dataset"}
          </Link>
          <span>·</span>
          <span title={new Date(job.created_at).toLocaleString()}>
            started {timeAgo(job.created_at)}
          </span>
          {job.finished_at && (
            <>
              <span>·</span>
              <span>took {duration(job.started_at, job.finished_at)}</span>
            </>
          )}
        </span>
      }
      actions={
        <>
          <Button
            icon={<RefreshCw className="size-4" />}
            loading={createJob.isPending}
            disabled={active}
            onClick={() =>
              createJob.mutate(
                { dataset_id: job.dataset_id, mode: "full", rules_yaml: job.rules_yaml },
                {
                  onSuccess: (j) => navigate(`/jobs/${j.id}`),
                  onError: (e) =>
                    toast({ tone: "error", title: "Could not start the run", body: e.message }),
                },
              )
            }
          >
            {job.mode === "sample" ? "Run on full dataset" : "Re-run"}
          </Button>
          <Button
            variant="ghost"
            aria-label="Delete run"
            disabled={active}
            icon={<Trash2 className="size-4" />}
            onClick={() =>
              remove.mutate(job.id, {
                onSuccess: () => navigate(`/datasets/${job.dataset_id}?tab=runs`),
                onError: (e) => toast({ tone: "error", title: "Delete failed", body: e.message }),
              })
            }
          />
        </>
      }
    />
  );
}

function Results({ job }: { job: JobDetail }) {
  const s = job.summary!;
  const violations = job.violations ?? [];
  const tone = scoreTone(s.score);
  const [filter, setFilter] = useState<RowFilter>(violations.length ? "issues" : "all");
  const [column, setColumn] = useState<string>("");
  const [offset, setOffset] = useState(0);
  const rows = useJobRows(job.id, true, filter, offset, 50, column || undefined);
  const explorer = useRef<HTMLDivElement>(null);

  const flagged = Object.entries(s.columns)
    .filter(([, c]) => c.error_rows + c.warning_rows > 0)
    .map(([name]) => name);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
        <Stat
          label="Quality score"
          value={formatPct(s.score)}
          tone={tone === "none" ? undefined : tone}
          hint="share of rows without errors"
        />
        <Stat
          label="Rows checked"
          value={formatNumber(s.rows_checked)}
          hint={
            job.mode === "sample"
              ? `random sample of ${formatNumber(s.dataset_rows)}`
              : "full dataset"
          }
        />
        <Stat
          label="Quarantined"
          value={formatNumber(s.quarantine_rows)}
          tone={s.quarantine_rows ? "bad" : "good"}
          hint="rows with errors"
        />
        <Stat
          label="Warnings"
          value={formatNumber(s.warning_rows)}
          tone={s.warning_rows ? "warn" : undefined}
          hint="rows with warnings"
        />
        <Stat
          label="Checks passed"
          value={
            <>
              {s.checks_passed}
              <span className="text-base text-zinc-400"> / {s.checks_total}</span>
            </>
          }
          tone={s.checks_failed ? "warn" : "good"}
          hint={`${s.errors} error · ${s.warnings} warning checks failed`}
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <Card title="Row status" className="xl:col-span-2">
          <RowComposition summary={s} />
          {flagged.length > 0 && (
            <div className="mt-6">
              <h4 className="mb-2 text-xs font-medium text-zinc-500 dark:text-zinc-400">
                Affected rows per column
              </h4>
              <IssuesByColumnChart summary={s} />
            </div>
          )}
        </Card>
        <ExportCard job={job} />
      </div>

      {violations.length > 0 ? (
        <Card title={`Failed checks (${violations.length})`} padded={false}>
          <ViolationsTable
            violations={violations}
            rowsChecked={s.rows_checked}
            onSelect={(v) => {
              setColumn(flagged.includes(v.column) ? v.column : "");
              setFilter(v.severity === "error" ? "errors" : "warnings");
              setOffset(0);
              explorer.current?.scrollIntoView({ behavior: "smooth", block: "start" });
            }}
          />
        </Card>
      ) : (
        <Alert tone="indigo" title="All checks passed">
          Every row satisfied every rule{job.mode === "sample" ? " in this sample" : ""}.
        </Alert>
      )}

      <div ref={explorer} className="scroll-mt-6">
        <Card
          title="Rows"
          actions={
            <>
              <div className="w-44">
                <Select
                  value={column}
                  onChange={(e) => {
                    setColumn(e.target.value);
                    setOffset(0);
                  }}
                  className="h-8 text-xs"
                  aria-label="Filter by column"
                >
                  <option value="">All columns</option>
                  {flagged.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </Select>
              </div>
              <Segmented
                value={filter}
                onChange={(f) => {
                  setFilter(f);
                  setOffset(0);
                }}
                items={[
                  { value: "issues", label: "With issues" },
                  { value: "errors", label: "Errors" },
                  { value: "warnings", label: "Warnings" },
                  { value: "clean", label: "Clean" },
                  { value: "all", label: "All" },
                ]}
              />
            </>
          }
        >
          <DataGrid
            page={rows.data}
            loading={rows.isFetching}
            onOffset={setOffset}
            violations={violations}
            showIssuesColumn={filter !== "clean"}
            focusColumn={column || undefined}
          />
        </Card>
      </div>
    </div>
  );
}

function ExportCard({ job }: { job: JobDetail }) {
  const [format, setFormat] = useState<ExportFormat>("csv");
  const s = job.summary!;
  const items: { kind: ExportKind; label: string; hint: string }[] = [
    {
      kind: "clean",
      label: "Clean rows",
      hint: `${formatNumber(s.clean_rows)} rows without errors`,
    },
    {
      kind: "quarantine",
      label: "Quarantine",
      hint: `${formatNumber(s.quarantine_rows)} rows + _issues column`,
    },
    { kind: "annotated", label: "Annotated", hint: "all rows + _status and _issues" },
  ];
  return (
    <Card
      title="Export"
      actions={
        <Segmented
          value={format}
          onChange={setFormat}
          items={(["csv", "json", "parquet", "xlsx"] as ExportFormat[]).map((f) => ({
            value: f,
            label: f,
          }))}
        />
      }
    >
      <ul className="space-y-2">
        {items.map((it) => (
          <li key={it.kind} className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <div className="text-sm font-medium">{it.label}</div>
              <div className="truncate text-xs text-zinc-500">{it.hint}</div>
            </div>
            <a href={api.exportUrl(job.id, it.kind, format)} download>
              <Button size="sm" icon={<Download className="size-4" />}>
                .{format}
              </Button>
            </a>
          </li>
        ))}
      </ul>
      {job.mode === "sample" && (
        <p className="mt-3 text-xs text-zinc-500">
          This is a sample run — exports contain only the sampled rows.
        </p>
      )}
    </Card>
  );
}

function RulesSnapshot({ yaml }: { yaml: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-6">
      <Button
        variant="ghost"
        size="sm"
        icon={<FileCode2 className="size-4" />}
        onClick={() => setOpen((o) => !o)}
      >
        {open ? "Hide" : "Show"} rules used for this run
      </Button>
      {open && (
        <div className="mt-2">
          <RulesEditor value={yaml} readOnly height="auto" />
        </div>
      )}
    </div>
  );
}
