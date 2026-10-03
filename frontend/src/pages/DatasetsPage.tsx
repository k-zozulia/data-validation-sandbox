import { Database, FileSpreadsheet, Trash2 } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router";
import type { Dataset } from "../api/client";
import { useDatasets, useDeleteDataset, useUploadDataset } from "../api/hooks";
import { JobStatusBadge, ScoreBadge } from "../components/Badges";
import { useToast } from "../components/Toaster";
import UploadDropzone from "../components/UploadDropzone";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Loading,
  Modal,
  PageHeader,
} from "../components/ui";
import { formatBytes, formatNumber, timeAgo } from "../utils/format";

export default function DatasetsPage() {
  const { data, isLoading, error } = useDatasets();
  const upload = useUploadDataset();
  const toast = useToast();
  const navigate = useNavigate();

  const onFile = (file: File) =>
    upload.mutate(
      { file },
      {
        onSuccess: (ds) => {
          toast({
            tone: "success",
            title: "Dataset uploaded",
            body: `${ds.name} · ${formatNumber(ds.row_count)} rows profiled`,
          });
          navigate(`/datasets/${ds.id}`);
        },
        onError: (e) => toast({ tone: "error", title: "Upload failed", body: e.message }),
      },
    );

  return (
    <>
      <PageHeader
        icon={<Database className="size-5" />}
        title="Datasets"
        subtitle="Upload a file once — then profile it, iterate on rules and run validations."
      />
      <div className="mb-6">
        <UploadDropzone onFile={onFile} busy={upload.isPending} compact={!!data?.length} />
      </div>

      {error && <Alert title="Could not load datasets">{error.message}</Alert>}
      {isLoading ? (
        <Loading />
      ) : data && data.length > 0 ? (
        <Card padded={false}>
          <DatasetTable items={data} />
        </Card>
      ) : (
        !error && (
          <EmptyState icon={<FileSpreadsheet className="size-10" />} title="No datasets yet">
            Upload your first file above. It will be profiled automatically and you will get a
            starter set of validation rules.
          </EmptyState>
        )
      )}
    </>
  );
}

function DatasetTable({ items }: { items: Dataset[] }) {
  const remove = useDeleteDataset();
  const toast = useToast();
  const [pending, setPending] = useState<Dataset | null>(null);

  return (
    <>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-left text-xs font-medium text-zinc-500 dark:text-zinc-400">
            <tr className="border-b border-zinc-200 dark:border-zinc-800">
              <th className="px-4 py-2.5">Name</th>
              <th className="px-4 py-2.5">Format</th>
              <th className="px-4 py-2.5 text-right">Rows</th>
              <th className="px-4 py-2.5 text-right">Columns</th>
              <th className="px-4 py-2.5 text-right">Size</th>
              <th className="px-4 py-2.5">Last validation</th>
              <th className="px-4 py-2.5">Uploaded</th>
              <th className="px-4 py-2.5" />
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
            {items.map((d) => (
              <tr key={d.id} className="group hover:bg-zinc-50 dark:hover:bg-zinc-800/40">
                <td className="max-w-xs px-4 py-2.5">
                  <Link
                    to={`/datasets/${d.id}`}
                    className="block truncate font-medium text-zinc-900 hover:text-indigo-600 dark:text-zinc-100 dark:hover:text-indigo-400"
                  >
                    {d.name}
                  </Link>
                  {d.name !== d.filename && (
                    <div className="truncate text-xs text-zinc-500">{d.filename}</div>
                  )}
                </td>
                <td className="px-4 py-2.5">
                  <Badge>{d.format}</Badge>
                </td>
                <td className="px-4 py-2.5 text-right tabular-nums">{formatNumber(d.row_count)}</td>
                <td className="px-4 py-2.5 text-right tabular-nums">{d.column_count}</td>
                <td className="px-4 py-2.5 text-right tabular-nums text-zinc-500">
                  {formatBytes(d.size_bytes)}
                </td>
                <td className="px-4 py-2.5">
                  {d.last_job ? (
                    <Link to={`/jobs/${d.last_job.id}`} className="flex items-center gap-2">
                      {d.last_job.status === "succeeded" ? (
                        <ScoreBadge score={d.last_job.score} />
                      ) : (
                        <JobStatusBadge status={d.last_job.status} />
                      )}
                      <span className="text-xs text-zinc-500">{d.last_job.mode}</span>
                    </Link>
                  ) : (
                    <span className="text-xs text-zinc-400">never</span>
                  )}
                </td>
                <td
                  className="px-4 py-2.5 whitespace-nowrap text-zinc-500"
                  title={new Date(d.created_at).toLocaleString()}
                >
                  {timeAgo(d.created_at)}
                </td>
                <td className="px-2 py-2.5 text-right">
                  <Button
                    variant="ghost"
                    size="sm"
                    aria-label={`Delete ${d.name}`}
                    className="opacity-60 group-hover:opacity-100"
                    icon={<Trash2 className="size-4" />}
                    onClick={() => setPending(d)}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Modal
        open={!!pending}
        onClose={() => setPending(null)}
        title="Delete dataset?"
        footer={
          <>
            <Button onClick={() => setPending(null)}>Cancel</Button>
            <Button
              variant="danger"
              loading={remove.isPending}
              onClick={() =>
                pending &&
                remove.mutate(pending.id, {
                  onSuccess: () => {
                    toast({ tone: "success", title: "Dataset deleted" });
                    setPending(null);
                  },
                  onError: (e) => toast({ tone: "error", title: "Delete failed", body: e.message }),
                })
              }
            >
              Delete
            </Button>
          </>
        }
      >
        <p className="text-sm text-zinc-600 dark:text-zinc-300">
          <b>{pending?.name}</b> and all of its validation runs will be permanently removed.
        </p>
      </Modal>
    </>
  );
}
