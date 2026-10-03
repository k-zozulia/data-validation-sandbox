import { ChevronRight } from "lucide-react";
import type { Violation } from "../api/client";
import { cellText, formatNumber, formatPct } from "../utils/format";
import { SeverityBadge } from "./Badges";

export default function ViolationsTable({
  violations,
  rowsChecked,
  onSelect,
  compact,
}: {
  violations: Violation[];
  rowsChecked: number;
  onSelect?: (v: Violation) => void;
  /** Stacked list layout for narrow panels. */
  compact?: boolean;
}) {
  if (!violations.length) return null;
  const sorted = [...violations].sort((a, b) =>
    a.severity === b.severity ? b.failed_count - a.failed_count : a.severity === "error" ? -1 : 1,
  );
  if (compact) {
    return (
      <ul className="divide-y divide-zinc-100 dark:divide-zinc-800">
        {sorted.map((v, i) => (
          <li key={i} className="px-4 py-2.5">
            <div className="flex items-center justify-between gap-2">
              <span className="min-w-0 truncate font-mono text-xs">
                {v.column} · {v.rule}
              </span>
              <span className="flex shrink-0 items-center gap-2">
                <span className="text-xs tabular-nums text-zinc-500">
                  {formatNumber(v.failed_count)} rows
                </span>
                <SeverityBadge severity={v.severity} />
              </span>
            </div>
            <div className="mt-0.5 text-sm text-zinc-700 dark:text-zinc-300">{v.message}</div>
            {v.sample_values.length > 0 && (
              <div className="mt-1 flex flex-wrap gap-1">
                {v.sample_values.slice(0, 3).map((s, k) => (
                  <code
                    key={k}
                    className="max-w-40 truncate rounded bg-zinc-100 px-1 text-[11px] text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300"
                  >
                    {cellText(s) || "null"}
                  </code>
                ))}
              </div>
            )}
          </li>
        ))}
      </ul>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="text-left text-xs font-medium text-zinc-500 dark:text-zinc-400">
          <tr className="border-b border-zinc-200 dark:border-zinc-800">
            <th className="px-3 py-2">Column</th>
            <th className="px-3 py-2">Rule</th>
            <th className="px-3 py-2">Severity</th>
            <th className="px-3 py-2 text-right">Rows</th>
            <th className="px-3 py-2">Details</th>
            {onSelect && <th />}
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
          {sorted.map((v, i) => (
            <tr
              key={i}
              onClick={() => onSelect?.(v)}
              className={
                onSelect ? "cursor-pointer hover:bg-zinc-50 dark:hover:bg-zinc-800/40" : undefined
              }
            >
              <td className="px-3 py-2 font-mono text-xs">{v.column}</td>
              <td className="px-3 py-2 font-mono text-xs">{v.rule}</td>
              <td className="px-3 py-2">
                <SeverityBadge severity={v.severity} />
              </td>
              <td className="px-3 py-2 text-right tabular-nums">
                {v.failed_count ? (
                  <>
                    {formatNumber(v.failed_count)}
                    <span className="ml-1 text-xs text-zinc-400">
                      {formatPct((v.failed_count / Math.max(rowsChecked, 1)) * 100)}
                    </span>
                  </>
                ) : (
                  <span className="text-zinc-400">—</span>
                )}
              </td>
              <td className="px-3 py-2">
                <div className="text-zinc-700 dark:text-zinc-300">{v.message}</div>
                {v.sample_values.length > 0 && (
                  <div className="mt-1 flex flex-wrap gap-1">
                    {v.sample_values.map((s, k) => (
                      <code
                        key={k}
                        className="max-w-48 truncate rounded bg-zinc-100 px-1 text-[11px] text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300"
                      >
                        {cellText(s) || "null"}
                      </code>
                    ))}
                  </div>
                )}
              </td>
              {onSelect && (
                <td className="px-2 text-zinc-400">
                  <ChevronRight className="size-4" />
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
