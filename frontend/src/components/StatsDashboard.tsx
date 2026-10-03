// Charts for profiles and validation results (recharts).
// Rules followed: one hue for single-series magnitude, the status palette only for
// quality states (always with a text label/legend), 4px rounded data-ends, a 2px
// surface gap between touching marks, recessive grid, hover tooltip on every mark.
import type { ReactNode } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { HistogramBin, JobSummary, TopValue } from "../api/client";
import { formatNumber, formatPct, formatStat } from "../utils/format";

const axisTick = { fill: "var(--viz-axis)", fontSize: 11 };

function TooltipBox({ title, children }: { title: ReactNode; children: ReactNode }) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-white px-2.5 py-1.5 text-xs shadow-md dark:border-zinc-700 dark:bg-zinc-900">
      <div className="font-medium text-zinc-900 dark:text-zinc-100">{title}</div>
      <div className="mt-0.5 text-zinc-600 dark:text-zinc-300">{children}</div>
    </div>
  );
}

function Swatch({ color }: { color: string }) {
  return <span className="inline-block size-2.5 rounded-sm" style={{ background: color }} />;
}

// ---------- Profile: numeric distribution ----------

export function Histogram({ bins, height = 72 }: { bins: HistogramBin[]; height?: number }) {
  if (!bins.length) return null;
  const data = bins.map((b) => ({ ...b, label: `${formatStat(b.start)} – ${formatStat(b.end)}` }));
  return (
    <div style={{ height }} aria-label="Value distribution">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 4, right: 0, bottom: 0, left: 0 }} barCategoryGap={1}>
          <XAxis dataKey="label" hide />
          <YAxis hide />
          <Tooltip
            cursor={{ fill: "var(--viz-grid)", opacity: 0.6 }}
            content={({ active, payload }) =>
              active && payload?.length ? (
                <TooltipBox title={payload[0].payload.label}>
                  {formatNumber(payload[0].payload.count)} rows
                </TooltipBox>
              ) : null
            }
          />
          <Bar
            dataKey="count"
            fill="var(--viz-series-1)"
            radius={[4, 4, 0, 0]}
            stroke="var(--viz-surface)"
            strokeWidth={1}
            isAnimationActive={false}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ---------- Profile: most frequent values (plain HTML bars) ----------

export function TopValuesBars({
  values,
  total,
  max = 5,
}: {
  values: TopValue[];
  total: number;
  max?: number;
}) {
  const shown = values.slice(0, max);
  const peak = Math.max(...shown.map((v) => v.count), 1);
  return (
    <ul className="space-y-1.5">
      {shown.map((v) => (
        <li key={v.value} className="text-xs" title={`${v.value}: ${formatNumber(v.count)} rows`}>
          <div className="flex justify-between gap-2">
            <span className="truncate font-mono text-zinc-700 dark:text-zinc-300">
              {v.value || "∅"}
            </span>
            <span className="shrink-0 tabular-nums text-zinc-500">
              {formatPct((v.count / Math.max(total, 1)) * 100)}
            </span>
          </div>
          <div className="mt-0.5 h-1.5 rounded-full bg-zinc-100 dark:bg-zinc-800">
            <div
              className="h-full rounded-full"
              style={{ width: `${(v.count / peak) * 100}%`, background: "var(--viz-series-1)" }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}

// ---------- Results: valid / warning / invalid composition ----------

export function RowComposition({ summary }: { summary: JobSummary }) {
  const total = Math.max(summary.rows_checked, 1);
  const warnOnly = summary.warning_only_rows;
  const valid = Math.max(summary.clean_rows - warnOnly, 0);
  const parts = [
    { key: "valid", label: "Valid", value: valid, color: "var(--status-good)" },
    { key: "warning", label: "Warnings only", value: warnOnly, color: "var(--status-warning)" },
    {
      key: "invalid",
      label: "Quarantined",
      value: summary.quarantine_rows,
      color: "var(--status-critical)",
    },
  ];
  return (
    <div>
      <div
        className="flex h-3 w-full gap-[2px] overflow-hidden rounded"
        role="img"
        aria-label="Row composition"
      >
        {parts
          .filter((p) => p.value > 0)
          .map((p) => (
            <div
              key={p.key}
              title={`${p.label}: ${formatNumber(p.value)} rows (${formatPct((p.value / total) * 100)})`}
              className="h-full first:rounded-l last:rounded-r"
              style={{ width: `${(p.value / total) * 100}%`, background: p.color, minWidth: 3 }}
            />
          ))}
      </div>
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-zinc-600 dark:text-zinc-300">
        {parts.map((p) => (
          <span key={p.key} className="inline-flex items-center gap-1.5">
            <Swatch color={p.color} />
            {p.label}
            <span className="tabular-nums text-zinc-500">
              {formatNumber(p.value)} · {formatPct((p.value / total) * 100)}
            </span>
          </span>
        ))}
      </div>
    </div>
  );
}

// ---------- Results: affected rows per column ----------

export function IssuesByColumnChart({ summary }: { summary: JobSummary }) {
  const data = Object.entries(summary.columns)
    .map(([column, c]) => ({ column, errors: c.error_rows, warnings: c.warning_rows }))
    .filter((d) => d.errors + d.warnings > 0)
    .sort((a, b) => b.errors + b.warnings - (a.errors + a.warnings))
    .slice(0, 12);

  if (!data.length) return null;
  const height = 40 + data.length * 30;

  return (
    <div>
      <div className="mb-2 flex gap-4 text-xs text-zinc-600 dark:text-zinc-300">
        <span className="inline-flex items-center gap-1.5">
          <Swatch color="var(--status-critical)" /> Rows with errors
        </span>
        <span className="inline-flex items-center gap-1.5">
          <Swatch color="var(--status-warning)" /> Rows with warnings
        </span>
      </div>
      <div style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 0, right: 16, bottom: 0, left: 0 }}
            barCategoryGap={8}
          >
            <CartesianGrid horizontal={false} stroke="var(--viz-grid)" />
            <XAxis
              type="number"
              tick={axisTick}
              axisLine={false}
              tickLine={false}
              allowDecimals={false}
            />
            <YAxis
              type="category"
              dataKey="column"
              width={130}
              tick={axisTick}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v: string) => (v.length > 18 ? v.slice(0, 17) + "…" : v)}
            />
            <Tooltip
              cursor={{ fill: "var(--viz-grid)", opacity: 0.5 }}
              content={({ active, payload }) =>
                active && payload?.length ? (
                  <TooltipBox title={payload[0].payload.column}>
                    <div>{formatNumber(payload[0].payload.errors)} rows with errors</div>
                    <div>{formatNumber(payload[0].payload.warnings)} rows with warnings</div>
                  </TooltipBox>
                ) : null
              }
            />
            <Bar
              dataKey="errors"
              stackId="a"
              fill="var(--status-critical)"
              stroke="var(--viz-surface)"
              strokeWidth={2}
              isAnimationActive={false}
            />
            <Bar
              dataKey="warnings"
              stackId="a"
              fill="var(--status-warning)"
              stroke="var(--viz-surface)"
              strokeWidth={2}
              radius={[0, 4, 4, 0]}
              isAnimationActive={false}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
