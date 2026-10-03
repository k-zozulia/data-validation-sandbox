import clsx from "clsx";
import { ChevronLeft, ChevronRight } from "lucide-react";
import type { RowsPage, Violation } from "../api/client";
import { cellText, formatNumber } from "../utils/format";
import { Button, Spinner } from "./ui";

type Props = {
  page: RowsPage | undefined;
  loading?: boolean;
  onOffset: (offset: number) => void;
  violations?: Violation[] | null;
  showIssuesColumn?: boolean;
  focusColumn?: string;
};

/** Paged table of rows; cells that broke a rule are highlighted with the reason on hover. */
export default function DataGrid({
  page,
  loading,
  onOffset,
  violations,
  showIssuesColumn,
  focusColumn,
}: Props) {
  const messages = new Map((violations ?? []).map((v) => [`${v.column}|${v.rule}`, v.message]));

  if (!page) {
    return (
      <div className="flex justify-center py-12">
        <Spinner />
      </div>
    );
  }

  const from = page.total ? page.offset + 1 : 0;
  const to = Math.min(page.offset + page.limit, page.total);

  return (
    <div>
      <div
        className="relative overflow-auto rounded-lg border border-zinc-200 dark:border-zinc-800"
        style={{ maxHeight: 560 }}
      >
        <table className="w-full border-collapse text-xs">
          <thead className="sticky top-0 z-10 bg-zinc-50 text-left font-medium text-zinc-500 dark:bg-zinc-900 dark:text-zinc-400">
            <tr>
              <th className="sticky left-0 z-10 border-b border-r border-zinc-200 bg-zinc-50 px-2 py-2 text-right dark:border-zinc-800 dark:bg-zinc-900">
                #
              </th>
              {showIssuesColumn && (
                <th className="border-b border-zinc-200 px-3 py-2 dark:border-zinc-800">Issues</th>
              )}
              {page.columns.map((c) => (
                <th
                  key={c}
                  className={clsx(
                    "border-b border-zinc-200 px-3 py-2 font-mono whitespace-nowrap dark:border-zinc-800",
                    c === focusColumn && "text-indigo-600 dark:text-indigo-400",
                  )}
                >
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className={clsx(loading && "opacity-60")}>
            {page.rows.map((row) => {
              const byColumn = new Map<string, { rule: string; severity: string }[]>();
              for (const i of row.issues) {
                byColumn.set(i.column, [...(byColumn.get(i.column) ?? []), i]);
              }
              return (
                <tr
                  key={row._row}
                  className="border-b border-zinc-100 last:border-0 dark:border-zinc-800/70"
                >
                  <td className="sticky left-0 border-r border-zinc-200 bg-white px-2 py-1.5 text-right tabular-nums text-zinc-400 dark:border-zinc-800 dark:bg-zinc-950">
                    {row._row}
                  </td>
                  {showIssuesColumn && (
                    <td className="max-w-64 px-3 py-1.5">
                      <div className="flex flex-wrap gap-1">
                        {row.issues.map((i, k) => (
                          <span
                            key={k}
                            title={messages.get(`${i.column}|${i.rule}`)}
                            className={clsx(
                              "rounded px-1 py-px font-mono text-[11px] whitespace-nowrap",
                              i.severity === "error"
                                ? "bg-rose-100 text-rose-800 dark:bg-rose-500/15 dark:text-rose-200"
                                : "bg-amber-100 text-amber-900 dark:bg-amber-500/15 dark:text-amber-200",
                            )}
                          >
                            {i.column}: {i.rule}
                          </span>
                        ))}
                      </div>
                    </td>
                  )}
                  {page.columns.map((c) => {
                    const issues = byColumn.get(c);
                    const severity = issues?.some((i) => i.severity === "error")
                      ? "error"
                      : issues?.length
                        ? "warning"
                        : null;
                    const text = cellText(row.values[c]);
                    const tip = issues
                      ?.map((i) => `${i.rule}: ${messages.get(`${c}|${i.rule}`) ?? i.severity}`)
                      .join("\n");
                    return (
                      <td
                        key={c}
                        title={tip ?? (text.length > 40 ? text : undefined)}
                        className={clsx(
                          "max-w-72 truncate px-3 py-1.5 font-mono",
                          severity === "error" &&
                            "bg-rose-50 text-rose-900 shadow-[inset_2px_0_0_var(--status-critical)] dark:bg-rose-500/10 dark:text-rose-100",
                          severity === "warning" &&
                            "bg-amber-50 text-amber-950 shadow-[inset_2px_0_0_var(--status-warning)] dark:bg-amber-500/10 dark:text-amber-100",
                        )}
                      >
                        {text === "" ? (
                          <span className="text-zinc-300 dark:text-zinc-600">null</span>
                        ) : (
                          text
                        )}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
            {page.rows.length === 0 && (
              <tr>
                <td
                  colSpan={page.columns.length + 2}
                  className="px-3 py-10 text-center text-sm text-zinc-500"
                >
                  No rows match this filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="mt-3 flex items-center justify-between text-xs text-zinc-500 dark:text-zinc-400">
        <span className="tabular-nums">
          {formatNumber(from)}–{formatNumber(to)} of {formatNumber(page.total)} rows
        </span>
        <div className="flex gap-1">
          <Button
            size="sm"
            aria-label="Previous page"
            disabled={page.offset === 0}
            onClick={() => onOffset(Math.max(0, page.offset - page.limit))}
            icon={<ChevronLeft className="size-4" />}
          />
          <Button
            size="sm"
            aria-label="Next page"
            disabled={to >= page.total}
            onClick={() => onOffset(page.offset + page.limit)}
            icon={<ChevronRight className="size-4" />}
          />
        </div>
      </div>
    </div>
  );
}
