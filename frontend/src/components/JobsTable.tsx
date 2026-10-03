import { Trash2 } from "lucide-react";
import { Link, useNavigate } from "react-router";
import type { Dataset, Job } from "../api/client";
import { useDeleteJob } from "../api/hooks";
import { duration, formatNumber, timeAgo } from "../utils/format";
import { JobStatusBadge, ModeBadge, ScoreBadge } from "./Badges";
import { useToast } from "./Toaster";
import { Button } from "./ui";

export default function JobsTable({
  jobs,
  datasets,
}: {
  jobs: Job[];
  datasets?: Map<string, Dataset>;
}) {
  const navigate = useNavigate();
  const remove = useDeleteJob();
  const toast = useToast();

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="text-left text-xs font-medium text-zinc-500 dark:text-zinc-400">
          <tr className="border-b border-zinc-200 dark:border-zinc-800">
            <th className="px-4 py-2.5">Started</th>
            {datasets && <th className="px-4 py-2.5">Dataset</th>}
            <th className="px-4 py-2.5">Mode</th>
            <th className="px-4 py-2.5">Status</th>
            <th className="px-4 py-2.5">Score</th>
            <th className="px-4 py-2.5 text-right">Rows checked</th>
            <th className="px-4 py-2.5 text-right">Failed checks</th>
            <th className="px-4 py-2.5 text-right">Duration</th>
            <th />
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
          {jobs.map((j) => (
            <tr
              key={j.id}
              className="group cursor-pointer hover:bg-zinc-50 dark:hover:bg-zinc-800/40"
              onClick={() => navigate(`/jobs/${j.id}`)}
            >
              <td
                className="px-4 py-2.5 whitespace-nowrap"
                title={new Date(j.created_at).toLocaleString()}
              >
                <Link
                  to={`/jobs/${j.id}`}
                  className="font-medium hover:text-indigo-600 dark:hover:text-indigo-400"
                  onClick={(e) => e.stopPropagation()}
                >
                  {timeAgo(j.created_at)}
                </Link>
              </td>
              {datasets && (
                <td className="max-w-56 truncate px-4 py-2.5 text-zinc-600 dark:text-zinc-300">
                  {datasets.get(j.dataset_id)?.name ?? "—"}
                </td>
              )}
              <td className="px-4 py-2.5">
                <ModeBadge mode={j.mode} />
              </td>
              <td className="px-4 py-2.5">
                <JobStatusBadge status={j.status} progress={j.progress} />
              </td>
              <td className="px-4 py-2.5">
                <ScoreBadge score={j.summary?.score} />
              </td>
              <td className="px-4 py-2.5 text-right tabular-nums">
                {formatNumber(j.summary?.rows_checked)}
              </td>
              <td className="px-4 py-2.5 text-right tabular-nums">
                {j.summary ? (
                  <>
                    {j.summary.checks_failed}
                    <span className="text-zinc-400"> / {j.summary.checks_total}</span>
                  </>
                ) : (
                  "—"
                )}
              </td>
              <td className="px-4 py-2.5 text-right whitespace-nowrap tabular-nums text-zinc-500">
                {duration(j.started_at, j.finished_at)}
              </td>
              <td className="px-2 py-2.5 text-right">
                <Button
                  size="sm"
                  variant="ghost"
                  aria-label="Delete run"
                  className="opacity-0 group-hover:opacity-100 focus:opacity-100"
                  disabled={j.status === "queued" || j.status === "running"}
                  icon={<Trash2 className="size-4" />}
                  onClick={(e) => {
                    e.stopPropagation();
                    remove.mutate(j.id, {
                      onError: (err) =>
                        toast({ tone: "error", title: "Delete failed", body: err.message }),
                    });
                  }}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
