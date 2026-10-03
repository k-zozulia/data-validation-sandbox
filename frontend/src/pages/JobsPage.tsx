import { History } from "lucide-react";
import { useMemo } from "react";
import { useDatasets, useJobs } from "../api/hooks";
import JobsTable from "../components/JobsTable";
import { Alert, Card, EmptyState, Loading, PageHeader } from "../components/ui";

export default function JobsPage() {
  const jobs = useJobs();
  const datasets = useDatasets();
  const byId = useMemo(() => new Map((datasets.data ?? []).map((d) => [d.id, d])), [datasets.data]);

  return (
    <>
      <PageHeader
        icon={<History className="size-5" />}
        title="Validation runs"
        subtitle="Every sample check and full run across all datasets, newest first."
      />
      {jobs.error && <Alert title="Could not load runs">{jobs.error.message}</Alert>}
      {jobs.isLoading ? (
        <Loading />
      ) : jobs.data?.length ? (
        <Card padded={false}>
          <JobsTable jobs={jobs.data} datasets={byId} />
        </Card>
      ) : (
        !jobs.error && (
          <EmptyState icon={<History className="size-10" />} title="No runs yet">
            Open a dataset and validate it to see runs here.
          </EmptyState>
        )
      )}
    </>
  );
}
