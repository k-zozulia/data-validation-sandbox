import CodeMirror from "@uiw/react-codemirror";
import { yaml } from "@codemirror/lang-yaml";
import { linter, lintGutter, type Diagnostic } from "@codemirror/lint";
import { parse } from "yaml";

// Underline YAML syntax errors live, using the same parser family as the backend.
const yamlLinter = linter((view): Diagnostic[] => {
  const text = view.state.doc.toString();
  if (!text.trim()) return [];
  try {
    parse(text);
    return [];
  } catch (e: any) {
    const from: number = e?.pos?.[0] ?? 0;
    return [
      {
        from,
        to: Math.min(from + 1, text.length),
        severity: "error",
        message: String(e?.message ?? "Invalid YAML"),
      },
    ];
  }
});

type Props = { value: string; onChange: (v: string) => void };

export default function RulesEditor({ value, onChange }: Props) {
  return (
    <CodeMirror
      value={value}
      height="320px"
      extensions={[yaml(), lintGutter(), yamlLinter]}
      onChange={onChange}
      basicSetup={{ lineNumbers: true, foldGutter: true }}
    />
  );
}
