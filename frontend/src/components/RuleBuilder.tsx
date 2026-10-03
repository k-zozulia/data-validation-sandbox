// Visual rules builder. Everything it can edit comes from the server's rule
// catalog, so adding a rule type on the backend makes it appear here for free.
import clsx from "clsx";
import { AlertTriangle, Plus, Search, X } from "lucide-react";
import { useMemo, useState } from "react";
import type { ParamSpec, RuleType } from "../api/client";
import { parseModel, serializeModel, type Params, type RulesModel } from "../utils/rulesModel";
import { TypeBadge } from "./Badges";
import { Alert, Button, Input, Label, Modal, Select } from "./ui";

export type BuilderColumn = {
  name: string;
  type: string;
  semantic?: string | null;
  isArray: boolean;
};

type Target = { scope: "column"; column: string } | { scope: "dataset" };
type Editing = { target: Target; rule: string | null; params: Params; isNew: boolean };

function describe(params: Params): string {
  return Object.entries(params)
    .filter(([k, v]) => k !== "message" && v !== undefined && v !== "")
    .map(([k, v]) =>
      k === "severity"
        ? v === "warning"
          ? "warning"
          : ""
        : `${k}=${Array.isArray(v) ? `[${v.join(", ")}]` : String(v)}`,
    )
    .filter(Boolean)
    .join(" · ");
}

function CheckChip({
  label,
  params,
  onEdit,
  onRemove,
}: {
  label: string;
  params: Params;
  onEdit: () => void;
  onRemove: () => void;
}) {
  const text = describe(params);
  const warning = params.severity === "warning";
  return (
    <span
      className={clsx(
        "inline-flex max-w-full items-center overflow-hidden rounded-md text-xs ring-1 ring-inset",
        warning
          ? "bg-amber-50 text-amber-900 ring-amber-300 dark:bg-amber-500/10 dark:text-amber-200 dark:ring-amber-500/30"
          : "bg-zinc-50 text-zinc-800 ring-zinc-300 dark:bg-zinc-800 dark:text-zinc-200 dark:ring-zinc-700",
      )}
    >
      <button
        onClick={onEdit}
        className="min-w-0 truncate px-2 py-1 text-left hover:underline"
        title="Edit check"
      >
        <span className="font-medium">{label}</span>
        {text && <span className="ml-1 opacity-70">{text}</span>}
      </button>
      <button
        onClick={onRemove}
        className="border-l border-current/15 px-1.5 py-1 opacity-60 hover:opacity-100"
        aria-label={`Remove ${label}`}
      >
        <X className="size-3" />
      </button>
    </span>
  );
}

function parseListInput(text: string): (string | number)[] {
  return text
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean)
    .map((s) => (s !== "" && !Number.isNaN(Number(s)) ? Number(s) : s));
}

function ParamInput({
  spec,
  value,
  onChange,
  columns,
}: {
  spec: ParamSpec;
  value: unknown;
  onChange: (v: unknown) => void;
  columns: BuilderColumn[];
}) {
  const label = (
    <Label hint={spec.required ? "required" : undefined}>{spec.name.replace(/_/g, " ")}</Label>
  );
  switch (spec.kind) {
    case "number":
      return (
        <label className="block">
          {label}
          <Input
            type="number"
            step="any"
            value={value === undefined || value === null ? "" : String(value)}
            onChange={(e) => onChange(e.target.value === "" ? undefined : Number(e.target.value))}
          />
        </label>
      );
    case "boolean":
      return (
        <label className="flex items-center gap-2 pt-5 text-sm">
          <input
            type="checkbox"
            className="size-4 rounded accent-indigo-600"
            checked={value === undefined ? Boolean(spec.default) : Boolean(value)}
            onChange={(e) => onChange(e.target.checked)}
          />
          {spec.name.replace(/_/g, " ")}
        </label>
      );
    case "select":
      return (
        <label className="block">
          {label}
          <Select
            value={value === undefined || value === null ? "" : String(value)}
            onChange={(e) => onChange(e.target.value || undefined)}
          >
            {!spec.required && (
              <option value="">{spec.default ? `default (${spec.default})` : "—"}</option>
            )}
            {spec.required && value === undefined && <option value="">Choose…</option>}
            {spec.options?.map((o) => (
              <option key={o} value={o}>
                {o}
              </option>
            ))}
          </Select>
        </label>
      );
    case "column":
      return (
        <label className="block">
          {label}
          <Select
            value={(value as string) ?? ""}
            onChange={(e) => onChange(e.target.value || undefined)}
          >
            <option value="">Choose a column…</option>
            {columns.map((c) => (
              <option key={c.name} value={c.name}>
                {c.name}
              </option>
            ))}
          </Select>
        </label>
      );
    case "columns": {
      const selected = new Set((value as string[]) ?? []);
      return (
        <fieldset className="col-span-full">
          {label}
          <div className="flex max-h-40 flex-wrap gap-1.5 overflow-y-auto rounded-lg p-1 ring-1 ring-zinc-200 dark:ring-zinc-700">
            {columns.map((c) => (
              <label
                key={c.name}
                className={clsx(
                  "flex cursor-pointer items-center gap-1 rounded-md px-2 py-1 font-mono text-xs ring-1 ring-inset",
                  selected.has(c.name)
                    ? "bg-indigo-50 text-indigo-700 ring-indigo-300 dark:bg-indigo-500/15 dark:text-indigo-200 dark:ring-indigo-500/40"
                    : "ring-zinc-200 dark:ring-zinc-700",
                )}
              >
                <input
                  type="checkbox"
                  className="sr-only"
                  checked={selected.has(c.name)}
                  onChange={(e) => {
                    const next = new Set(selected);
                    if (e.target.checked) next.add(c.name);
                    else next.delete(c.name);
                    onChange(columns.map((x) => x.name).filter((n) => next.has(n)));
                  }}
                />
                {c.name}
              </label>
            ))}
          </div>
        </fieldset>
      );
    }
    case "list":
      return (
        <label className="col-span-full block">
          <Label hint="comma-separated">{spec.name.replace(/_/g, " ")}</Label>
          <Input
            defaultValue={Array.isArray(value) ? value.join(", ") : ""}
            placeholder="e.g. UA, PL, DE"
            onChange={(e) => onChange(parseListInput(e.target.value))}
          />
        </label>
      );
    default:
      return (
        <label
          className={clsx(
            "block",
            spec.name === "pattern" || spec.name === "message" ? "col-span-full" : "",
          )}
        >
          {label}
          <Input
            value={(value as string) ?? ""}
            placeholder={spec.placeholder ?? undefined}
            className={spec.name === "pattern" ? "font-mono" : undefined}
            onChange={(e) => onChange(e.target.value === "" ? undefined : e.target.value)}
          />
        </label>
      );
  }
}

function ruleFits(rule: RuleType, col?: BuilderColumn): boolean {
  if (!col) return true;
  if (rule.applies_to === "any") return true;
  return rule.applies_to === "array" ? col.isArray : !col.isArray;
}

export default function RuleBuilder({
  yaml: yamlText,
  onChange,
  columns,
  catalog,
}: {
  yaml: string;
  onChange: (yaml: string) => void;
  columns: BuilderColumn[];
  catalog: RuleType[];
}) {
  const model = useMemo(() => parseModel(yamlText), [yamlText]);
  const [editing, setEditing] = useState<Editing | null>(null);
  const [query, setQuery] = useState("");
  const [onlyWithChecks, setOnlyWithChecks] = useState(false);
  const byName = useMemo(() => new Map(catalog.map((r) => [r.name, r])), [catalog]);

  if (!model) {
    return (
      <Alert tone="amber" title="The YAML can't be shown in the builder">
        Fix the syntax error in the YAML tab first — the builder needs a valid document.
      </Alert>
    );
  }

  const update = (fn: (m: RulesModel) => void) => {
    const next: RulesModel = structuredClone(model);
    fn(next);
    onChange(serializeModel(next));
  };

  const known = new Set(columns.map((c) => c.name));
  const orphan = Object.keys(model.columns).filter((c) => !known.has(c));
  const allColumns: (BuilderColumn & { orphan?: boolean })[] = [
    ...columns,
    ...orphan.map((name) => ({ name, type: "unknown", isArray: false, orphan: true })),
  ];
  const visible = allColumns.filter(
    (c) =>
      c.name.toLowerCase().includes(query.toLowerCase()) &&
      (!onlyWithChecks || Object.keys(model.columns[c.name] ?? {}).length > 0),
  );

  const save = () => {
    if (!editing?.rule) return;
    const { target, rule, params } = editing;
    update((m) => {
      if (target.scope === "dataset") m.dataset[rule] = params;
      else (m.columns[target.column] ??= {})[rule] = params;
    });
    setEditing(null);
  };

  const editingRule = editing?.rule ? byName.get(editing.rule) : undefined;
  const editingColumn =
    editing?.target.scope === "column"
      ? allColumns.find((c) => c.name === (editing.target as { column: string }).column)
      : undefined;
  const missingRequired = editingRule?.params.some(
    (p) =>
      p.required &&
      (editing?.params[p.name] === undefined ||
        (Array.isArray(editing?.params[p.name]) && !(editing?.params[p.name] as unknown[]).length)),
  );
  const existing =
    editing?.target.scope === "dataset"
      ? model.dataset
      : editing
        ? (model.columns[(editing.target as { column: string }).column] ?? {})
        : {};

  return (
    <div className="space-y-6">
      {/* Column checks */}
      <section>
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
          <h4 className="text-sm font-semibold">Column checks</h4>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-1.5 text-xs text-zinc-500">
              <input
                type="checkbox"
                className="accent-indigo-600"
                checked={onlyWithChecks}
                onChange={(e) => setOnlyWithChecks(e.target.checked)}
              />
              only with checks
            </label>
            <div className="relative">
              <Search className="pointer-events-none absolute top-2.5 left-2.5 size-4 text-zinc-400" />
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Filter columns"
                className="w-48 pl-8"
              />
            </div>
          </div>
        </div>
        <ul className="divide-y divide-zinc-100 rounded-lg ring-1 ring-zinc-200 dark:divide-zinc-800 dark:ring-zinc-800">
          {visible.map((col) => {
            const checks = model.columns[col.name] ?? {};
            return (
              <li
                key={col.name}
                className="flex flex-col gap-2 px-3 py-2.5 sm:flex-row sm:items-start"
              >
                <div className="flex w-full shrink-0 items-center gap-2 sm:w-56">
                  <span className="truncate font-mono text-sm" title={col.name}>
                    {col.name}
                  </span>
                  {col.orphan ? (
                    <span title="This column is not in the dataset" className="text-amber-500">
                      <AlertTriangle className="size-4" />
                    </span>
                  ) : (
                    <TypeBadge type={col.type} />
                  )}
                </div>
                <div className="flex min-w-0 flex-1 flex-wrap items-center gap-1.5">
                  {Object.entries(checks).map(([rule, params]) => (
                    <CheckChip
                      key={rule}
                      label={byName.get(rule)?.label ?? rule}
                      params={params}
                      onEdit={() =>
                        setEditing({
                          target: { scope: "column", column: col.name },
                          rule,
                          params: { ...params },
                          isNew: false,
                        })
                      }
                      onRemove={() =>
                        update((m) => {
                          delete m.columns[col.name][rule];
                        })
                      }
                    />
                  ))}
                  <Button
                    size="sm"
                    variant="ghost"
                    icon={<Plus className="size-3.5" />}
                    onClick={() =>
                      setEditing({
                        target: { scope: "column", column: col.name },
                        rule: null,
                        params: {},
                        isNew: true,
                      })
                    }
                  >
                    Add
                  </Button>
                </div>
              </li>
            );
          })}
          {visible.length === 0 && (
            <li className="px-3 py-6 text-center text-sm text-zinc-500">No columns match.</li>
          )}
        </ul>
      </section>

      {/* Dataset checks */}
      <section>
        <h4 className="mb-2 text-sm font-semibold">Dataset checks</h4>
        <div className="flex flex-wrap items-center gap-1.5 rounded-lg px-3 py-2.5 ring-1 ring-zinc-200 dark:ring-zinc-800">
          {Object.entries(model.dataset).map(([rule, params]) => (
            <CheckChip
              key={rule}
              label={byName.get(rule)?.label ?? rule}
              params={params}
              onEdit={() =>
                setEditing({
                  target: { scope: "dataset" },
                  rule,
                  params: { ...params },
                  isNew: false,
                })
              }
              onRemove={() =>
                update((m) => {
                  delete m.dataset[rule];
                })
              }
            />
          ))}
          <Button
            size="sm"
            variant="ghost"
            icon={<Plus className="size-3.5" />}
            onClick={() =>
              setEditing({ target: { scope: "dataset" }, rule: null, params: {}, isNew: true })
            }
          >
            Add
          </Button>
        </div>
      </section>

      <Modal
        open={!!editing}
        onClose={() => setEditing(null)}
        title={
          editing?.target.scope === "dataset" ? (
            "Dataset check"
          ) : (
            <>
              Check for{" "}
              <span className="font-mono">
                {(editing?.target as { column: string } | undefined)?.column}
              </span>
            </>
          )
        }
        footer={
          <>
            <Button onClick={() => setEditing(null)}>Cancel</Button>
            <Button variant="primary" disabled={!editing?.rule || missingRequired} onClick={save}>
              {editing?.isNew ? "Add check" : "Save"}
            </Button>
          </>
        }
      >
        {editing && (
          <div className="space-y-4">
            {editing.isNew && (
              <div className="grid gap-2 sm:grid-cols-2">
                {catalog
                  .filter(
                    (r) =>
                      r.scope === editing.target.scope &&
                      ruleFits(r, editingColumn) &&
                      !(r.name in existing),
                  )
                  .map((r) => (
                    <button
                      key={r.name}
                      onClick={() => setEditing({ ...editing, rule: r.name, params: {} })}
                      className={clsx(
                        "rounded-lg p-2.5 text-left ring-1 ring-inset transition-colors",
                        editing.rule === r.name
                          ? "bg-indigo-50 ring-indigo-400 dark:bg-indigo-500/10 dark:ring-indigo-500/50"
                          : "ring-zinc-200 hover:bg-zinc-50 dark:ring-zinc-700 dark:hover:bg-zinc-800",
                      )}
                    >
                      <div className="text-sm font-medium">{r.label}</div>
                      <div className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">
                        {r.description}
                      </div>
                    </button>
                  ))}
              </div>
            )}
            {editingRule && (
              <div
                className={clsx(
                  editing.isNew && "border-t border-zinc-200 pt-4 dark:border-zinc-800",
                )}
              >
                {!editing.isNew && (
                  <p className="mb-3 text-sm text-zinc-500 dark:text-zinc-400">
                    {editingRule.description}
                  </p>
                )}
                <div className="grid gap-3 sm:grid-cols-2">
                  {editingRule.params
                    .filter((p) => !p.common)
                    .map((p) => (
                      <ParamInput
                        key={`${editingRule.name}-${p.name}`}
                        spec={p}
                        value={editing.params[p.name]}
                        columns={columns}
                        onChange={(v) =>
                          setEditing({ ...editing, params: { ...editing.params, [p.name]: v } })
                        }
                      />
                    ))}
                </div>
                <details
                  className="mt-4"
                  open={editing.params.severity === "warning" || !!editing.params.message}
                >
                  <summary className="cursor-pointer text-xs font-medium text-zinc-500 select-none">
                    Severity &amp; message
                  </summary>
                  <div className="mt-3 grid gap-3 sm:grid-cols-2">
                    {editingRule.params
                      .filter((p) => p.common)
                      .map((p) => (
                        <ParamInput
                          key={`${editingRule.name}-${p.name}`}
                          spec={p}
                          value={editing.params[p.name]}
                          columns={columns}
                          onChange={(v) =>
                            setEditing({ ...editing, params: { ...editing.params, [p.name]: v } })
                          }
                        />
                      ))}
                  </div>
                  <p className="mt-2 text-xs text-zinc-500">
                    Warnings are reported but don't move rows to quarantine.
                  </p>
                </details>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
