import { useState } from "react";
import RuleBuilder from "./RuleBuilder";
import RulesEditor from "./RulesEditor";
import type { ColumnInfo } from "../api/client";

type Props = {
  columns: ColumnInfo[];
  rulesYaml: string;
  onChange: (yaml: string) => void;
};

export default function RulesPanel({ columns, rulesYaml, onChange }: Props) {
  const [tab, setTab] = useState<"builder" | "yaml">("builder");
  return (
    <div>
      <div className="tabs">
        <button
          className={tab === "builder" ? "tab active" : "tab"}
          onClick={() => setTab("builder")}
        >
          Builder
        </button>
        <button
          className={tab === "yaml" ? "tab active" : "tab"}
          onClick={() => setTab("yaml")}
        >
          YAML
        </button>
      </div>

      {tab === "builder" ? (
        columns.length > 0 ? (
          <RuleBuilder
            columns={columns}
            rulesYaml={rulesYaml}
            onChange={onChange}
          />
        ) : (
          <p className="status">Profile a file first to use the builder.</p>
        )
      ) : (
        <RulesEditor value={rulesYaml} onChange={onChange} />
      )}
    </div>
  );
}
