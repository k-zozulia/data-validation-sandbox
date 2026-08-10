import {
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
  ResponsiveContainer,
} from "recharts";
import type { DatasetProfile, Violation } from "../api/client";

// Shared palette: a rule keeps the same colour across both charts.
const PALETTE = [
  "#4f86c6",
  "#d9694f",
  "#6aa84f",
  "#c9a227",
  "#8e6cae",
  "#3aa6a6",
  "#c0587e",
];

export function ProfileChart({ profile }: { profile: DatasetProfile }) {
  const data = Object.entries(profile.columns).map(([name, c]) => ({
    name,
    nullPct: c.null_pct,
  }));
  return (
    <div>
      <h3>Null % by column</h3>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="name" />
          <YAxis />
          <Tooltip />
          <Bar dataKey="nullPct" name="null %" fill="#4f86c6" />
        </BarChart>
      </ResponsiveContainer>
      <div className="col-types">
        {Object.entries(profile.columns).map(([name, c]) => (
          <span className="col-type" key={name}>
            {name}
            {c.is_array ? (
              <span className="badge">array</span>
            ) : (
              <span className="badge muted">{c.dtype}</span>
            )}
          </span>
        ))}
      </div>
    </div>
  );
}

export function ViolationsChart({ violations }: { violations: Violation[] }) {
  if (violations.length === 0) return null;

  // Stable, sorted rule list -> stable colour assignment shared by both charts.
  const rules = Array.from(new Set(violations.map((v) => v.rule))).sort();
  const colorOf: Record<string, string> = {};
  rules.forEach((rule, i) => {
    colorOf[rule] = PALETTE[i % PALETTE.length];
  });

  // By rule: one bar per rule, coloured by rule.
  const ruleCounts: Record<string, number> = {};
  for (const v of violations)
    ruleCounts[v.rule] = (ruleCounts[v.rule] ?? 0) + v.failed_count;
  const byRule = rules.map((rule) => ({ rule, count: ruleCounts[rule] }));

  // By column: one bar per column, stacked by rule (same rule colours).
  const colMap: Record<string, Record<string, number>> = {};
  for (const v of violations) {
    (colMap[v.column] ??= {})[v.rule] =
      (colMap[v.column][v.rule] ?? 0) + v.failed_count;
  }
  const byColumn = Object.entries(colMap).map(([column, counts]) => ({
    column,
    ...counts,
  }));

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
      <div>
        <h3>Violations by rule</h3>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={byRule}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="rule" />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Bar dataKey="count" name="failed">
              {byRule.map((d) => (
                <Cell key={d.rule} fill={colorOf[d.rule]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div>
        <h3>Violations by column</h3>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={byColumn}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="column" />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Legend />
            {rules.map((rule) => (
              <Bar key={rule} dataKey={rule} stackId="v" fill={colorOf[rule]} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
