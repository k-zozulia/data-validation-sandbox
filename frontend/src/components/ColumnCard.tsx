import type { ReactNode } from "react";
import type { ColumnProfile } from "../api/client";
import { formatNumber, formatPct, formatStat } from "../utils/format";
import { TypeBadge } from "./Badges";
import { Histogram, TopValuesBars } from "./StatsDashboard";

function Metric({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="text-[11px] uppercase tracking-wide text-zinc-400">{label}</dt>
      <dd className="truncate text-sm font-medium tabular-nums">{value}</dd>
    </div>
  );
}

export default function ColumnCard({
  name,
  col,
  rowCount,
}: {
  name: string;
  col: ColumnProfile;
  rowCount: number;
}) {
  const numeric = col.inferred_type === "integer" || col.inferred_type === "float";
  const completeness = 100 - col.null_pct;

  return (
    <article className="flex flex-col rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
      <header className="mb-3 flex items-start justify-between gap-2">
        <h4 className="min-w-0 truncate font-mono text-sm font-semibold" title={name}>
          {name}
        </h4>
        <TypeBadge type={col.inferred_type} semantic={col.semantic_type} />
      </header>

      <div className="mb-3">
        <div className="mb-1 flex justify-between text-xs text-zinc-500 dark:text-zinc-400">
          <span>Completeness</span>
          <span className="tabular-nums">
            {formatPct(completeness)}
            {col.null_count > 0 && <> · {formatNumber(col.null_count)} missing</>}
          </span>
        </div>
        <div
          className="h-1.5 rounded-full bg-zinc-100 dark:bg-zinc-800"
          title={`${formatPct(completeness)} filled`}
        >
          <div
            className="h-full rounded-full"
            style={{ width: `${completeness}%`, background: "var(--viz-series-1)" }}
          />
        </div>
      </div>

      <dl className="mb-3 grid grid-cols-3 gap-2">
        <Metric label="Unique" value={col.is_array ? "—" : formatNumber(col.unique_count)} />
        {numeric ? (
          <>
            <Metric label="Min" value={formatStat(col.min)} />
            <Metric label="Max" value={formatStat(col.max)} />
            <Metric label="Mean" value={formatStat(col.mean)} />
            <Metric label="Median" value={formatStat(col.median)} />
            <Metric label="Std" value={formatStat(col.std)} />
          </>
        ) : col.min_length !== null ? (
          <>
            <Metric label={col.is_array ? "Min items" : "Min len"} value={col.min_length} />
            <Metric label={col.is_array ? "Max items" : "Max len"} value={col.max_length} />
          </>
        ) : (
          <Metric label="Distinct %" value={formatPct(col.unique_pct)} />
        )}
      </dl>

      <div className="mt-auto">
        {numeric && col.histogram.length > 1 ? (
          <Histogram bins={col.histogram} />
        ) : col.top_values.length > 0 && col.unique_pct < 100 ? (
          <TopValuesBars values={col.top_values} total={rowCount - col.null_count} max={4} />
        ) : col.sample_values.length > 0 ? (
          <div className="space-y-0.5 text-xs">
            <div className="text-[11px] uppercase tracking-wide text-zinc-400">Examples</div>
            {col.sample_values.map((v, i) => (
              <div key={i} className="truncate font-mono text-zinc-600 dark:text-zinc-300">
                {typeof v === "object" ? JSON.stringify(v) : String(v)}
              </div>
            ))}
          </div>
        ) : null}
      </div>
    </article>
  );
}
