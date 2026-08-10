import { useState } from "react";
import { parse, stringify } from "yaml";
import type { ColumnInfo } from "../api/client";

type ParamSpec = {
  key: string;
  kind: "number" | "text" | "select";
  options?: string[];
};
type RuleSpec = { label: string; params: ParamSpec[] };

const RULES: Record<string, RuleSpec> = {
  not_null: { label: "Not null", params: [] },
  unique: { label: "Unique", params: [] },
  dtype: {
    label: "Type",
    params: [
      {
        key: "expected",
        kind: "select",
        options: ["int", "float", "numeric", "bool", "str", "datetime"],
      },
    ],
  },
  range: {
    label: "Range",
    params: [
      { key: "min", kind: "number" },
      { key: "max", kind: "number" },
    ],
  },
  regex: { label: "Regex", params: [{ key: "pattern", kind: "text" }] },
  array_length: {
    label: "Array length",
    params: [
      { key: "min", kind: "number" },
      { key: "max", kind: "number" },
    ],
  },
  array_items: {
    label: "Array items",
    params: [
      {
        key: "type",
        kind: "select",
        options: ["int", "float", "numeric", "bool", "str"],
      },
      { key: "min", kind: "number" },
      { key: "max", kind: "number" },
    ],
  },
};

// Only rules that make sense for the column's type are offered.
const ARRAY_RULES = ["not_null", "array_length", "array_items"];
const SCALAR_RULES = ["not_null", "unique", "dtype", "range", "regex"];

type Model = Record<string, Record<string, any>>;

function parseModel(yamlText: string): Model {
  try {
    const data = parse(yamlText);
    if (
      data &&
      typeof data === "object" &&
      data.columns &&
      typeof data.columns === "object"
    ) {
      return data.columns as Model;
    }
  } catch {
    /* invalid YAML — treat as empty for the builder view */
  }
  return {};
}

const toYaml = (columns: Model): string => stringify({ columns });

function describe(params: Record<string, any>): string {
  const entries = Object.entries(params);
  return entries.length === 0
    ? ""
    : "(" + entries.map(([k, v]) => `${k}=${v}`).join(", ") + ")";
}

type Props = {
  columns: ColumnInfo[];
  rulesYaml: string;
  onChange: (yaml: string) => void;
};

export default function RuleBuilder({ columns, rulesYaml, onChange }: Props) {
  const model = parseModel(rulesYaml);
  const [col, setCol] = useState("");
  const [rule, setRule] = useState<string>("not_null");
  const [params, setParams] = useState<Record<string, string>>({});

  const names = columns.map((c) => c.name);
  const currentCol = names.includes(col) ? col : (names[0] ?? "");
  const isArray = columns.find((c) => c.name === currentCol)?.isArray ?? false;

  const available = isArray ? ARRAY_RULES : SCALAR_RULES;
  const activeRule = available.includes(rule) ? rule : available[0];

  function addRule() {
    if (!currentCol) return;
    const clean: Record<string, any> = {};
    for (const p of RULES[activeRule].params) {
      const raw = params[p.key];
      if (raw === undefined || raw === "") continue;
      clean[p.key] = p.kind === "number" ? Number(raw) : raw;
    }
    const next: Model = {
      ...model,
      [currentCol]: { ...(model[currentCol] ?? {}), [activeRule]: clean },
    };
    onChange(toYaml(next));
    setParams({});
  }

  function removeRule(column: string, ruleName: string) {
    const colRules = { ...(model[column] ?? {}) };
    delete colRules[ruleName];
    const next: Model = { ...model };
    if (Object.keys(colRules).length === 0) delete next[column];
    else next[column] = colRules;
    onChange(toYaml(next));
  }

  const ordered = names.filter((c) => model[c]);
  const extra = Object.keys(model).filter((c) => !names.includes(c));

  return (
    <div className="builder">
      <div className="rule-groups">
        {ordered.length === 0 && extra.length === 0 && (
          <p className="status">No rules yet — add one below.</p>
        )}
        {[...ordered, ...extra].map((column) => (
          <div className="rule-group" key={column}>
            <span className="col-name">
              {column}
              {columns.find((c) => c.name === column)?.isArray && (
                <span className="badge">array</span>
              )}
            </span>
            <div className="chips">
              {Object.entries(model[column]).map(([ruleName, p]) => (
                <span className="chip" key={ruleName}>
                  {ruleName}
                  {describe(p)}
                  <button
                    title="Remove"
                    onClick={() => removeRule(column, ruleName)}
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="builder-form">
        <select value={currentCol} onChange={(e) => setCol(e.target.value)}>
          {columns.map((c) => (
            <option key={c.name} value={c.name}>
              {c.name}
              {c.isArray ? " (array)" : ""}
            </option>
          ))}
        </select>
        <select
          value={activeRule}
          onChange={(e) => {
            setRule(e.target.value);
            setParams({});
          }}
        >
          {available.map((key) => (
            <option key={key} value={key}>
              {RULES[key].label}
            </option>
          ))}
        </select>
        {RULES[activeRule].params.map((p) =>
          p.kind === "select" ? (
            <select
              key={p.key}
              value={params[p.key] ?? ""}
              onChange={(e) =>
                setParams({ ...params, [p.key]: e.target.value })
              }
            >
              <option value="">{p.key}…</option>
              {p.options!.map((o) => (
                <option key={o} value={o}>
                  {o}
                </option>
              ))}
            </select>
          ) : (
            <input
              key={p.key}
              type={p.kind === "number" ? "number" : "text"}
              placeholder={p.key}
              value={params[p.key] ?? ""}
              onChange={(e) =>
                setParams({ ...params, [p.key]: e.target.value })
              }
            />
          ),
        )}
        <button className="add-btn" onClick={addRule}>
          Add rule
        </button>
      </div>
    </div>
  );
}
