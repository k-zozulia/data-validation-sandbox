import { CheckCircle2, CircleDashed, Loader2, XCircle } from "lucide-react";
import type { JobMode, JobStatus, Severity } from "../api/client";
import { formatPct, scoreTone } from "../utils/format";
import { Badge } from "./ui";

export function JobStatusBadge({ status, progress }: { status: JobStatus; progress?: number }) {
  switch (status) {
    case "succeeded":
      return (
        <Badge tone="green">
          <CheckCircle2 className="size-3" /> Done
        </Badge>
      );
    case "failed":
      return (
        <Badge tone="red">
          <XCircle className="size-3" /> Failed
        </Badge>
      );
    case "running":
      return (
        <Badge tone="indigo">
          <Loader2 className="size-3 animate-spin" /> Running{progress ? ` ${progress}%` : ""}
        </Badge>
      );
    default:
      return (
        <Badge>
          <CircleDashed className="size-3" /> Queued
        </Badge>
      );
  }
}

export function ModeBadge({ mode }: { mode: JobMode }) {
  return mode === "sample" ? (
    <Badge tone="sky">Sample</Badge>
  ) : (
    <Badge tone="violet">Full run</Badge>
  );
}

export function ScoreBadge({ score }: { score: number | null | undefined }) {
  const tone = scoreTone(score);
  if (tone === "none") return <span className="text-zinc-400">—</span>;
  return (
    <Badge
      tone={tone === "good" ? "green" : tone === "warn" ? "amber" : "red"}
      title="Share of valid rows"
    >
      {formatPct(score)}
    </Badge>
  );
}

export function SeverityBadge({ severity }: { severity: Severity }) {
  return severity === "error" ? (
    <Badge tone="red">error</Badge>
  ) : (
    <Badge tone="amber">warning</Badge>
  );
}

const typeTones: Record<string, "indigo" | "sky" | "green" | "amber" | "violet" | "neutral"> = {
  integer: "indigo",
  float: "indigo",
  string: "green",
  boolean: "amber",
  datetime: "sky",
  array: "violet",
};

export function TypeBadge({ type, semantic }: { type: string; semantic?: string | null }) {
  return (
    <span className="inline-flex flex-wrap gap-1">
      <Badge tone={typeTones[type] ?? "neutral"}>{type}</Badge>
      {semantic && <Badge tone="neutral">{semantic}</Badge>}
    </span>
  );
}
