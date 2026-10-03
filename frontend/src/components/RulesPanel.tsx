import { CheckCircle2, CircleAlert, TriangleAlert } from "lucide-react";
import { useEffect, useState } from "react";
import { api, type LintResult } from "../api/client";
import { useRuleCatalog } from "../api/hooks";
import RuleBuilder, { type BuilderColumn } from "./RuleBuilder";
import RulesEditor from "./RulesEditor";
import { Segmented, Spinner } from "./ui";

type Mode = "builder" | "yaml";

export function LintStatus({ lint }: { lint: LintResult | null | undefined }) {
  if (lint === undefined) return <Spinner className="size-4" />;
  if (lint === null) return <span className="text-xs text-zinc-400">lint unavailable</span>;
  const errors = lint.issues.filter((i) => i.severity === "error").length;
  const warnings = lint.issues.length - errors;
  if (errors)
    return (
      <span className="inline-flex items-center gap-1 text-xs font-medium text-rose-600 dark:text-rose-400">
        <CircleAlert className="size-4" /> {errors} error{errors > 1 ? "s" : ""}
      </span>
    );
  return (
    <span className="inline-flex items-center gap-1 text-xs text-zinc-600 dark:text-zinc-300">
      {warnings ? (
        <TriangleAlert className="size-4 text-amber-500" />
      ) : (
        <CheckCircle2 className="size-4 text-emerald-500" />
      )}
      {lint.checks} check{lint.checks === 1 ? "" : "s"}
      {warnings > 0 && (
        <span className="text-amber-600 dark:text-amber-400">
          · {warnings} warning{warnings > 1 ? "s" : ""}
        </span>
      )}
    </span>
  );
}

/** Builder ⇄ YAML editor over the same rules text, with lint status. */
export default function RulesPanel({
  value,
  onChange,
  columns,
  datasetId,
  onLint,
}: {
  value: string;
  onChange: (v: string) => void;
  columns: BuilderColumn[];
  datasetId?: string;
  onLint?: (r: LintResult | null) => void;
}) {
  const [mode, setMode] = useState<Mode>(() => {
    try {
      return (localStorage.getItem("dvs-rules-mode") as Mode) || "builder";
    } catch {
      return "builder";
    }
  });
  const [lint, setLint] = useState<LintResult | null | undefined>(undefined);
  const catalog = useRuleCatalog();

  // The YAML editor lints on its own; in builder mode lint here (debounced).
  useEffect(() => {
    if (mode !== "builder") return;
    const t = setTimeout(() => {
      api
        .lintRules(value, datasetId)
        .then((r) => {
          setLint(r);
          onLint?.(r);
        })
        .catch(() => {
          setLint(null);
          onLint?.(null);
        });
    }, 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, datasetId, mode]);

  const switchMode = (m: Mode) => {
    setMode(m);
    try {
      localStorage.setItem("dvs-rules-mode", m);
    } catch {
      /* ignore */
    }
  };

  const issues = lint?.issues ?? [];

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <Segmented
          value={mode}
          onChange={switchMode}
          items={[
            { value: "builder", label: "Visual builder" },
            { value: "yaml", label: "YAML" },
          ]}
        />
        <LintStatus lint={lint} />
      </div>

      {mode === "builder" ? (
        <>
          {catalog.data ? (
            <RuleBuilder
              yaml={value}
              onChange={onChange}
              columns={columns}
              catalog={catalog.data}
            />
          ) : (
            <div className="flex justify-center py-10">
              <Spinner />
            </div>
          )}
          {issues.length > 0 && (
            <ul className="mt-4 space-y-1 text-xs">
              {issues.map((i, k) => (
                <li
                  key={k}
                  className={
                    i.severity === "error"
                      ? "text-rose-600 dark:text-rose-400"
                      : "text-amber-700 dark:text-amber-400"
                  }
                >
                  <span className="font-mono">{i.path.join(".") || "rules"}</span> — {i.message}
                </li>
              ))}
            </ul>
          )}
        </>
      ) : (
        <RulesEditor
          value={value}
          onChange={onChange}
          datasetId={datasetId}
          onLint={(r) => {
            setLint(r);
            onLint?.(r);
          }}
        />
      )}
    </div>
  );
}
