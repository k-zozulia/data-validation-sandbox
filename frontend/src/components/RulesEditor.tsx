import { yaml } from "@codemirror/lang-yaml";
import { linter, lintGutter, type Diagnostic } from "@codemirror/lint";
import CodeMirror from "@uiw/react-codemirror";
import { useEffect, useMemo, useRef } from "react";
import { api, type LintResult } from "../api/client";
import { useIsDark } from "../utils/theme";

/** YAML editor with live server-side linting (unknown rules, bad params, missing columns). */
export default function RulesEditor({
  value,
  onChange,
  datasetId,
  onLint,
  height,
  readOnly,
}: {
  value: string;
  onChange?: (v: string) => void;
  datasetId?: string;
  onLint?: (r: LintResult | null) => void;
  height?: string;
  readOnly?: boolean;
}) {
  const dark = useIsDark();
  // Mutable holder so the (memoized) lint source always reports to the latest callback.
  const listenerRef = useRef(onLint);
  useEffect(() => {
    listenerRef.current = onLint;
  }, [onLint]);

  const extensions = useMemo(() => {
    const exts = [yaml()];
    if (readOnly) return exts;
    const source = async (view: import("@codemirror/view").EditorView): Promise<Diagnostic[]> => {
      const text = view.state.doc.toString();
      let result: LintResult;
      try {
        result = await api.lintRules(text, datasetId);
      } catch {
        listenerRef.current?.(null);
        return [];
      }
      listenerRef.current?.(result);
      const doc = view.state.doc;
      return result.issues.map((issue) => {
        const line = doc.line(Math.min(Math.max(issue.line ?? 1, 1), doc.lines));
        const indent = line.text.length - line.text.trimStart().length;
        return {
          from: line.from + indent,
          to: Math.max(line.to, line.from + indent + 1),
          severity: issue.severity,
          message: issue.message,
        };
      });
    };
    // `source` only reads listenerRef inside the async lint callback, never during render.
    // eslint-disable-next-line react-hooks/refs
    return [...exts, lintGutter(), linter(source, { delay: 400 })];
  }, [datasetId, readOnly]);

  return (
    <div className="cm-theme overflow-hidden rounded-lg ring-1 ring-zinc-200 dark:ring-zinc-800">
      <CodeMirror
        value={value}
        height={height}
        minHeight={height ? undefined : "420px"}
        maxHeight={height ? undefined : "70vh"}
        theme={dark ? "dark" : "light"}
        extensions={extensions}
        editable={!readOnly}
        basicSetup={{ foldGutter: true, highlightActiveLine: !readOnly }}
        onChange={(v) => onChange?.(v)}
      />
    </div>
  );
}
