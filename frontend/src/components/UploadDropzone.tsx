import clsx from "clsx";
import { UploadCloud } from "lucide-react";
import { useRef, useState } from "react";
import { Spinner } from "./ui";

const ACCEPT = ".csv,.tsv,.txt,.json,.jsonl,.ndjson,.parquet,.xlsx";

export default function UploadDropzone({
  onFile,
  busy,
  compact,
}: {
  onFile: (file: File) => void;
  busy?: boolean;
  compact?: boolean;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label="Upload a data file"
      onClick={() => !busy && input.current?.click()}
      onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && input.current?.click()}
      onDragOver={(e) => {
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setOver(false);
        const f = e.dataTransfer.files?.[0];
        if (f && !busy) onFile(f);
      }}
      className={clsx(
        "flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed text-center transition-colors",
        compact ? "px-4 py-6" : "px-6 py-12",
        over
          ? "border-indigo-500 bg-indigo-50/60 dark:bg-indigo-500/10"
          : "border-zinc-300 bg-white hover:border-indigo-400 hover:bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-900 dark:hover:bg-zinc-800/60",
        busy && "pointer-events-none opacity-70",
      )}
    >
      {busy ? <Spinner className="size-8" /> : <UploadCloud className="size-8 text-indigo-500" />}
      <div className="mt-3 text-sm font-medium">
        {busy ? "Uploading and profiling…" : "Drop a file here or click to browse"}
      </div>
      <div className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
        CSV / TSV · JSON · JSON Lines · Parquet · Excel (.xlsx)
      </div>
      <input
        ref={input}
        type="file"
        accept={ACCEPT}
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) onFile(f);
          e.target.value = "";
        }}
      />
    </div>
  );
}
