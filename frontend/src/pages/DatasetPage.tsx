import {
  ArrowRight,
  Download,
  FileSpreadsheet,
  FlaskConical,
  FolderOpen,
  Pencil,
  Play,
  RotateCcw,
  Save,
  Search,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router";
import { api, ApiError, type DatasetDetail, type JobDetail, type LintResult } from "../api/client";
import {
  useCreateJob,
  useDataset,
  useDatasetJobs,
  useDatasetRows,
  useRuleSets,
  useSaveRuleSet,
  useUpdateDataset,
} from "../api/hooks";
import { ScoreBadge } from "../components/Badges";
import ColumnCard from "../components/ColumnCard";
import DataGrid from "../components/DataGrid";
import JobsTable from "../components/JobsTable";
import RulesPanel from "../components/RulesPanel";
import { RowComposition } from "../components/StatsDashboard";
import { useToast } from "../components/Toaster";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Input,
  Label,
  Loading,
  Modal,
  PageHeader,
  Stat,
  Tabs,
  Textarea,
} from "../components/ui";
import ViolationsTable from "../components/ViolationsTable";
import { formatBytes, formatNumber, formatPct, timeAgo } from "../utils/format";

type Tab = "overview" | "data" | "rules" | "runs";

export default function DatasetPage() {
  const { id = "" } = useParams();
  const { data: ds, isLoading, error } = useDataset(id);
  const jobs = useDatasetJobs(id);
  const [params, setParams] = useSearchParams();
  const tab = (params.get("tab") as Tab) || "overview";
  const setTab = (t: Tab) => setParams({ tab: t }, { replace: true });
  const [renaming, setRenaming] = useState(false);

  if (isLoading) return <Loading />;
  if (error || !ds)
    return (
      <EmptyState icon={<FileSpreadsheet className="size-10" />} title="Dataset not found">
        {error?.message}
      </EmptyState>
    );

  return (
    <>
      <PageHeader
        icon={<FileSpreadsheet className="size-5" />}
        title={
          <span className="inline-flex items-center gap-2">
            {ds.name}
            <button
              onClick={() => setRenaming(true)}
              className="rounded p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700 dark:hover:bg-zinc-800"
              aria-label="Rename dataset"
            >
              <Pencil className="size-3.5" />
            </button>
          </span>
        }
        subtitle={
          <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <Badge>{ds.format}</Badge>
            <span>{ds.filename}</span>
            <span>·</span>
            <span>{formatBytes(ds.size_bytes)}</span>
            <span>·</span>
            <span title={new Date(ds.created_at).toLocaleString()}>
              uploaded {timeAgo(ds.created_at)}
            </span>
          </span>
        }
        actions={
          <Button
            variant="primary"
            icon={<Play className="size-4" />}
            onClick={() => setTab("rules")}
          >
            Validate
          </Button>
        }
      />

      <Tabs
        className="mb-6"
        value={tab}
        onChange={setTab}
        items={[
          { value: "overview", label: "Overview" },
          { value: "data", label: "Data" },
          { value: "rules", label: "Rules & validation" },
          { value: "runs", label: "Runs", count: jobs.data?.length },
        ]}
      />

      {tab === "overview" && <Overview ds={ds} />}
      {tab === "data" && <DataTab ds={ds} />}
      {tab === "rules" && <RulesTab ds={ds} />}
      {tab === "runs" &&
        (jobs.data?.length ? (
          <Card padded={false}>
            <JobsTable jobs={jobs.data} />
          </Card>
        ) : (
          <EmptyState icon={<FlaskConical className="size-10" />} title="No runs yet">
            Validate a sample or run a full validation from the <b>Rules &amp; validation</b> tab.
          </EmptyState>
        ))}

      <RenameModal
        key={renaming ? "open" : "closed"}
        ds={ds}
        open={renaming}
        onClose={() => setRenaming(false)}
      />
    </>
  );
}

// ---------------------------------------------------------------------------

function Overview({ ds }: { ds: DatasetDetail }) {
  const p = ds.profile;
  const [query, setQuery] = useState("");
  const cols = Object.entries(p.columns).filter(([name]) =>
    name.toLowerCase().includes(query.toLowerCase()),
  );
  const complete = 100 - p.missing_cells_pct;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
        <Stat label="Rows" value={formatNumber(p.row_count)} />
        <Stat label="Columns" value={p.column_count} />
        <Stat
          label="Completeness"
          value={formatPct(complete)}
          hint={`${formatNumber(p.missing_cells)} missing cells`}
          tone={complete >= 99 ? "good" : complete >= 90 ? "warn" : "bad"}
        />
        <Stat
          label="Duplicate rows"
          value={formatNumber(p.duplicate_rows)}
          tone={p.duplicate_rows ? "warn" : "good"}
          hint={
            p.row_count ? formatPct((p.duplicate_rows / p.row_count) * 100) + " of rows" : undefined
          }
        />
        <Stat
          label="Last validation"
          value={
            ds.last_job?.status === "succeeded" ? <ScoreBadge score={ds.last_job.score} /> : "—"
          }
          hint={
            ds.last_job ? (
              <Link
                to={`/jobs/${ds.last_job.id}`}
                className="text-indigo-600 hover:underline dark:text-indigo-400"
              >
                {ds.last_job.mode} · {timeAgo(ds.last_job.created_at)}
              </Link>
            ) : (
              "not validated yet"
            )
          }
        />
      </div>

      <div>
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-semibold">Column profiles</h2>
          {p.column_count > 6 && (
            <div className="relative">
              <Search className="pointer-events-none absolute top-2.5 left-2.5 size-4 text-zinc-400" />
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Filter columns"
                className="w-56 pl-8"
              />
            </div>
          )}
        </div>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {cols.map(([name, col]) => (
            <ColumnCard key={name} name={name} col={col} rowCount={p.row_count} />
          ))}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------

function DataTab({ ds }: { ds: DatasetDetail }) {
  const [offset, setOffset] = useState(0);
  const { data, isFetching } = useDatasetRows(ds.id, offset, 50);
  return (
    <Card>
      <DataGrid page={data} loading={isFetching} onOffset={setOffset} />
    </Card>
  );
}

// ---------------------------------------------------------------------------

function useAutosave(ds: DatasetDetail, draft: string) {
  const update = useUpdateDataset(ds.id);
  const [state, setState] = useState<"saved" | "saving" | "dirty" | "error">("saved");
  const last = useRef(ds.rules_yaml);

  useEffect(() => {
    if (draft === last.current) return;
    setState("dirty");
    const t = setTimeout(() => {
      setState("saving");
      update.mutate(
        { rules_yaml: draft },
        {
          onSuccess: () => {
            last.current = draft;
            setState("saved");
          },
          onError: () => setState("error"),
        },
      );
    }, 800);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draft]);

  return state;
}

function RulesTab({ ds }: { ds: DatasetDetail }) {
  const [draft, setDraft] = useState(ds.rules_yaml);
  const [lint, setLint] = useState<LintResult | null>(null);
  const [sample, setSample] = useState<JobDetail | null>(null);
  const [runError, setRunError] = useState<ApiError | null>(null);
  const [dialog, setDialog] = useState<"save" | "load" | "reset" | null>(null);
  const saveState = useAutosave(ds, draft);
  const createJob = useCreateJob();
  const navigate = useNavigate();
  const toast = useToast();

  const columns = useMemo(
    () =>
      Object.entries(ds.profile.columns).map(([name, c]) => ({
        name,
        type: c.inferred_type,
        semantic: c.semantic_type,
        isArray: c.is_array,
      })),
    [ds.profile],
  );
  const hasErrors = !!lint && !lint.valid;

  const run = (mode: "sample" | "full") => {
    setRunError(null);
    createJob.mutate(
      { dataset_id: ds.id, mode, rules_yaml: draft },
      {
        onSuccess: (job) => {
          if (mode === "sample") setSample(job);
          else {
            toast({ tone: "success", title: "Full validation started" });
            navigate(`/jobs/${job.id}`);
          }
        },
        onError: (e) =>
          setRunError(e instanceof ApiError ? e : new ApiError(0, { detail: e.message })),
      },
    );
  };

  return (
    <div className="grid gap-6 xl:grid-cols-5">
      <Card
        className="xl:col-span-3"
        title={
          <span className="flex items-center gap-2">
            Rules
            <span className="text-xs font-normal text-zinc-400">
              {saveState === "saving"
                ? "saving…"
                : saveState === "dirty"
                  ? "unsaved"
                  : saveState === "error"
                    ? "save failed"
                    : "draft saved"}
            </span>
          </span>
        }
        actions={
          <>
            <Button
              size="sm"
              variant="ghost"
              icon={<FolderOpen className="size-4" />}
              onClick={() => setDialog("load")}
            >
              Load set
            </Button>
            <Button
              size="sm"
              variant="ghost"
              icon={<Save className="size-4" />}
              onClick={() => setDialog("save")}
            >
              Save as set
            </Button>
            <Button
              size="sm"
              variant="ghost"
              icon={<RotateCcw className="size-4" />}
              onClick={() => setDialog("reset")}
            >
              Suggested
            </Button>
          </>
        }
      >
        <RulesPanel
          value={draft}
          onChange={setDraft}
          columns={columns}
          datasetId={ds.id}
          onLint={setLint}
        />
      </Card>

      <div className="space-y-4 xl:col-span-2">
        <Card title="Run validation">
          <p className="mb-4 text-sm text-zinc-500 dark:text-zinc-400">
            Check a random sample of up to <b>1,000</b> rows for instant feedback, then run the full
            validation on all <b>{formatNumber(ds.row_count)}</b> rows in the background.
          </p>
          <div className="flex flex-wrap gap-2">
            <Button
              icon={<FlaskConical className="size-4" />}
              loading={createJob.isPending && createJob.variables?.mode === "sample"}
              disabled={hasErrors || createJob.isPending}
              onClick={() => run("sample")}
            >
              Validate sample
            </Button>
            <Button
              variant="primary"
              icon={<Play className="size-4" />}
              loading={createJob.isPending && createJob.variables?.mode === "full"}
              disabled={hasErrors || createJob.isPending}
              onClick={() => run("full")}
            >
              Run full validation
            </Button>
          </div>
          {hasErrors && (
            <p className="mt-3 text-xs text-rose-600 dark:text-rose-400">
              Fix the rule errors before running.
            </p>
          )}
          {runError && (
            <div className="mt-3">
              <Alert title={runError.message}>
                {runError.issues.length > 0 && (
                  <ul className="mt-1 list-inside list-disc text-xs">
                    {runError.issues.map((i, k) => (
                      <li key={k}>
                        <span className="font-mono">{i.path.join(".")}</span> {i.message}
                      </li>
                    ))}
                  </ul>
                )}
              </Alert>
            </div>
          )}
        </Card>

        {sample && <SampleResult job={sample} />}
      </div>

      <SaveRuleSetModal
        key={dialog === "save" ? "open" : "closed"}
        open={dialog === "save"}
        onClose={() => setDialog(null)}
        rulesYaml={draft}
        defaultName={ds.name}
      />
      <LoadRuleSetModal
        open={dialog === "load"}
        onClose={() => setDialog(null)}
        onLoad={(yaml) => {
          setDraft(yaml);
          setDialog(null);
        }}
      />
      <Modal
        open={dialog === "reset"}
        onClose={() => setDialog(null)}
        title="Replace with suggested rules?"
        footer={
          <>
            <Button onClick={() => setDialog(null)}>Cancel</Button>
            <Button
              variant="danger"
              onClick={async () => {
                try {
                  setDraft((await api.suggestedRules(ds.id)).rules_yaml);
                } catch (e) {
                  toast({
                    tone: "error",
                    title: "Could not load suggestions",
                    body: (e as Error).message,
                  });
                }
                setDialog(null);
              }}
            >
              Replace
            </Button>
          </>
        }
      >
        <p className="text-sm text-zinc-600 dark:text-zinc-300">
          Your current draft will be replaced by rules generated from the dataset profile. Save it
          as a rule set first if you want to keep it.
        </p>
      </Modal>
    </div>
  );
}

function SampleResult({ job }: { job: JobDetail }) {
  if (job.status === "failed") {
    return <Alert title="Sample check failed">{job.error?.detail ?? job.error?.error}</Alert>;
  }
  const s = job.summary!;
  const violations = job.violations ?? [];
  return (
    <Card
      title={
        <span className="flex items-center gap-2">
          Sample result <ScoreBadge score={s.score} />
        </span>
      }
      actions={
        <Link to={`/jobs/${job.id}`}>
          <Button size="sm" variant="ghost" icon={<ArrowRight className="size-4" />}>
            Details
          </Button>
        </Link>
      }
    >
      <p className="mb-3 text-sm text-zinc-600 dark:text-zinc-300">
        {formatNumber(s.rows_checked)} of {formatNumber(s.dataset_rows)} rows checked ·{" "}
        {s.checks_failed} of {s.checks_total} checks failed
      </p>
      <RowComposition summary={s} />
      {violations.length > 0 ? (
        <div className="-mx-4 mt-4 border-t border-zinc-200 dark:border-zinc-800">
          <ViolationsTable violations={violations} rowsChecked={s.rows_checked} compact />
        </div>
      ) : (
        <p className="mt-4 text-sm font-medium text-emerald-600 dark:text-emerald-400">
          All checks passed on the sample.
        </p>
      )}
    </Card>
  );
}

// ---------------------------------------------------------------------------

function RenameModal({
  ds,
  open,
  onClose,
}: {
  ds: DatasetDetail;
  open: boolean;
  onClose: () => void;
}) {
  const [name, setName] = useState(ds.name);
  const update = useUpdateDataset(ds.id);
  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Rename dataset"
      footer={
        <>
          <Button onClick={onClose}>Cancel</Button>
          <Button
            variant="primary"
            disabled={!name.trim()}
            loading={update.isPending}
            onClick={() => update.mutate({ name: name.trim() }, { onSuccess: onClose })}
          >
            Save
          </Button>
        </>
      }
    >
      <Input value={name} onChange={(e) => setName(e.target.value)} autoFocus />
    </Modal>
  );
}

function SaveRuleSetModal({
  open,
  onClose,
  rulesYaml,
  defaultName,
}: {
  open: boolean;
  onClose: () => void;
  rulesYaml: string;
  defaultName: string;
}) {
  const [name, setName] = useState(`${defaultName.replace(/\.[^.]+$/, "")} rules`);
  const [description, setDescription] = useState("");
  const save = useSaveRuleSet();
  const toast = useToast();

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Save as rule set"
      footer={
        <>
          <Button onClick={onClose}>Cancel</Button>
          <Button
            variant="primary"
            disabled={!name.trim()}
            loading={save.isPending}
            onClick={() =>
              save.mutate(
                { name: name.trim(), description, rules_yaml: rulesYaml },
                {
                  onSuccess: () => {
                    toast({ tone: "success", title: "Rule set saved" });
                    onClose();
                  },
                },
              )
            }
          >
            Save
          </Button>
        </>
      }
    >
      <div className="space-y-3">
        <label className="block">
          <Label>Name</Label>
          <Input value={name} onChange={(e) => setName(e.target.value)} autoFocus />
        </label>
        <label className="block">
          <Label hint="optional">Description</Label>
          <Textarea rows={3} value={description} onChange={(e) => setDescription(e.target.value)} />
        </label>
        {save.error && <Alert>{save.error.message}</Alert>}
        <p className="text-xs text-zinc-500">
          Rule sets can be reused on any dataset with the same columns.
        </p>
      </div>
    </Modal>
  );
}

function LoadRuleSetModal({
  open,
  onClose,
  onLoad,
}: {
  open: boolean;
  onClose: () => void;
  onLoad: (yaml: string) => void;
}) {
  const { data, isLoading } = useRuleSets();
  return (
    <Modal open={open} onClose={onClose} title="Load a rule set">
      {isLoading ? (
        <Loading />
      ) : data?.length ? (
        <ul className="divide-y divide-zinc-100 dark:divide-zinc-800">
          {data.map((rs) => (
            <li key={rs.id} className="flex items-center justify-between gap-3 py-2.5">
              <div className="min-w-0">
                <div className="truncate text-sm font-medium">{rs.name}</div>
                <div className="truncate text-xs text-zinc-500">
                  {rs.description || `updated ${timeAgo(rs.updated_at)}`}
                </div>
              </div>
              <Button
                size="sm"
                icon={<Download className="size-4" />}
                onClick={() => onLoad(rs.rules_yaml)}
              >
                Load
              </Button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-zinc-500">
          No saved rule sets yet. Use “Save as set” to create one.
        </p>
      )}
    </Modal>
  );
}
