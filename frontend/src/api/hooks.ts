import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type JobMode, type RowFilter } from "./client";

export const keys = {
  health: ["health"] as const,
  datasets: ["datasets"] as const,
  dataset: (id: string) => ["datasets", id] as const,
  datasetRows: (id: string, offset: number, limit: number) =>
    ["datasets", id, "rows", offset, limit] as const,
  datasetJobs: (id: string) => ["datasets", id, "jobs"] as const,
  catalog: ["rules", "catalog"] as const,
  ruleSets: ["rule-sets"] as const,
  jobs: ["jobs"] as const,
  job: (id: string) => ["jobs", id] as const,
  jobRows: (id: string, ...rest: unknown[]) => ["jobs", id, "rows", ...rest] as const,
};

const isActive = (status?: string) => status === "queued" || status === "running";

export const useHealth = () =>
  useQuery({ queryKey: keys.health, queryFn: api.health, refetchInterval: 15_000, retry: false });

export const useDatasets = () => useQuery({ queryKey: keys.datasets, queryFn: api.listDatasets });

export const useDataset = (id: string) =>
  useQuery({ queryKey: keys.dataset(id), queryFn: () => api.getDataset(id) });

export const useDatasetRows = (id: string, offset: number, limit: number) =>
  useQuery({
    queryKey: keys.datasetRows(id, offset, limit),
    queryFn: () => api.datasetRows(id, offset, limit),
    placeholderData: keepPreviousData,
  });

export const useDatasetJobs = (id: string) =>
  useQuery({
    queryKey: keys.datasetJobs(id),
    queryFn: () => api.datasetJobs(id),
    refetchInterval: (q) => (q.state.data?.some((j) => isActive(j.status)) ? 1500 : false),
  });

export const useRuleCatalog = () =>
  useQuery({ queryKey: keys.catalog, queryFn: api.ruleCatalog, staleTime: Infinity });

export const useRuleSets = () => useQuery({ queryKey: keys.ruleSets, queryFn: api.listRuleSets });

export const useJobs = () =>
  useQuery({
    queryKey: keys.jobs,
    queryFn: api.listJobs,
    refetchInterval: (q) => (q.state.data?.some((j) => isActive(j.status)) ? 2000 : false),
  });

export const useJob = (id: string) =>
  useQuery({
    queryKey: keys.job(id),
    queryFn: () => api.getJob(id),
    refetchInterval: (q) => (isActive(q.state.data?.status) ? 1000 : false),
  });

export const useJobRows = (
  id: string,
  enabled: boolean,
  filter: RowFilter,
  offset: number,
  limit: number,
  column?: string,
) =>
  useQuery({
    queryKey: keys.jobRows(id, filter, offset, limit, column),
    queryFn: () => api.jobRows(id, filter, offset, limit, column),
    enabled,
    placeholderData: keepPreviousData,
  });

// ---------- mutations ----------

export function useUploadDataset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ file, name }: { file: File; name?: string }) => api.uploadDataset(file, name),
    onSuccess: (ds) => {
      qc.setQueryData(keys.dataset(ds.id), ds);
      qc.invalidateQueries({ queryKey: keys.datasets });
    },
  });
}

export function useUpdateDataset(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (patch: { name?: string; rules_yaml?: string }) => api.updateDataset(id, patch),
    onSuccess: (ds) => {
      qc.setQueryData(keys.dataset(id), ds);
      qc.invalidateQueries({ queryKey: keys.datasets, exact: true });
    },
  });
}

export function useDeleteDataset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.deleteDataset,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.datasets });
      qc.invalidateQueries({ queryKey: keys.jobs });
    },
  });
}

export function useCreateJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: {
      dataset_id: string;
      mode: JobMode;
      rules_yaml?: string;
      rule_set_id?: string;
    }) => api.createJob(data),
    onSuccess: (job) => {
      qc.setQueryData(keys.job(job.id), job);
      qc.invalidateQueries({ queryKey: keys.datasetJobs(job.dataset_id) });
      qc.invalidateQueries({ queryKey: keys.datasets, exact: true });
      qc.invalidateQueries({ queryKey: keys.jobs });
    },
  });
}

export function useDeleteJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.deleteJob,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.jobs });
      qc.invalidateQueries({ queryKey: keys.datasets });
    },
  });
}

export function useSaveRuleSet() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      ...data
    }: {
      id?: string;
      name: string;
      description?: string;
      rules_yaml: string;
    }) => (id ? api.updateRuleSet(id, data) : api.createRuleSet(data)),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.ruleSets }),
  });
}

export function useDeleteRuleSet() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.deleteRuleSet,
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.ruleSets }),
  });
}
