import { useState } from "react";

const API = "http://localhost:8000";

type Violation = {
  column: string;
  rule: string;
  message: string;
  failed_count: number;
  failed_rows: number[];
};

export default function App() {
  const [file, setFile] = useState<File | null>(null);
  const [rules, setRules] = useState("");
  const [violations, setViolations] = useState<Violation[] | null>(null);
  const [summary, setSummary] = useState("");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);

  function form(extra?: Record<string, string>) {
    const fd = new FormData();
    if (file) fd.append("file", file);
    if (extra) for (const [k, v] of Object.entries(extra)) fd.append(k, v);
    return fd;
  }

  async function onProfile() {
    if (!file) return alert("Choose a CSV file first");
    setBusy(true); setStatus("Profiling…"); setViolations(null);
    try {
      const r = await fetch(`${API}/datasets/profile`, { method: "POST", body: form() });
      const b = await r.json();
      if (!r.ok) throw new Error(b.detail || b.error);
      setRules(b.starter_rules_yaml);
      setStatus(`Profiled ${b.profile.row_count} rows, ${b.profile.column_count} columns — edit the rules and validate.`);
    } catch (e: any) { setStatus("Error: " + e.message); }
    finally { setBusy(false); }
  }

  async function onValidateSample() {
    if (!file) return alert("Choose a CSV file first");
    setBusy(true); setStatus("Validating sample…");
    try {
      const r = await fetch(`${API}/datasets/validate-sample`, { method: "POST", body: form({ rules_yaml: rules }) });
      const b = await r.json();
      if (!r.ok) throw new Error(b.detail || b.error);
      setViolations(b.violations);
      setSummary(`Sample (${b.sample_rows} rows): ${b.summary.total_violations} violation(s)`);
      setStatus("Sample check done.");
    } catch (e: any) { setStatus("Error: " + e.message); }
    finally { setBusy(false); }
  }

  async function onRunFull() {
    if (!file) return alert("Choose a CSV file first");
    setBusy(true); setStatus("Queuing full run…"); setViolations(null);
    try {
      const r = await fetch(`${API}/jobs`, { method: "POST", body: form({ rules_yaml: rules }) });
      const b = await r.json();
      if (!r.ok) throw new Error(b.detail || b.error);
      poll(b.job_id);
    } catch (e: any) { setStatus("Error: " + e.message); setBusy(false); }
  }

  function poll(jobId: string) {
    setStatus("Running full validation…");
    const tick = async () => {
      const r = await fetch(`${API}/jobs/${jobId}`);
      const b = await r.json();
      if (b.status === "done") {
        setViolations(b.result.violations);
        setSummary(`Full run (${b.result.row_count} rows): ${b.result.total_violations} violation(s)`);
        setStatus("Full run done."); setBusy(false);
      } else if (b.status === "error") {
        setStatus("Job error: " + (b.error?.detail || b.error?.error)); setBusy(false);
      } else {
        setStatus(`Full run: ${b.status}…`);
        setTimeout(tick, 1500);
      }
    };
    tick();
  }

  return (
    <div style={{ maxWidth: 900, margin: "2rem auto", fontFamily: "system-ui, sans-serif", padding: "0 1rem" }}>
      <h1>Data Validation Sandbox</h1>

      <input type="file" accept=".csv,.json,.parquet" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />

      <div style={{ margin: "1rem 0", display: "flex", gap: 8 }}>
        <button onClick={onProfile} disabled={busy}>1. Profile &amp; generate rules</button>
        <button onClick={onValidateSample} disabled={busy || !rules}>2. Validate sample</button>
        <button onClick={onRunFull} disabled={busy || !rules}>3. Run full</button>
      </div>

      <textarea
        value={rules}
        onChange={(e) => setRules(e.target.value)}
        placeholder="Rules YAML appears here after profiling — edit before validating."
        rows={14}
        style={{ width: "100%", fontFamily: "monospace", fontSize: 13 }}
      />

      {status && <p style={{ color: "#555" }}>{status}</p>}
      {summary && <p><strong>{summary}</strong></p>}

      {violations && violations.length > 0 && (
        <table border={1} cellPadding={6} style={{ borderCollapse: "collapse", width: "100%", fontSize: 14 }}>
          <thead>
            <tr><th>Column</th><th>Rule</th><th>Message</th><th>Failed rows</th></tr>
          </thead>
          <tbody>
            {violations.map((v, i) => (
              <tr key={i}>
                <td>{v.column}</td>
                <td>{v.rule}</td>
                <td>{v.message}</td>
                <td>{v.failed_rows.slice(0, 20).join(", ")}{v.failed_rows.length > 20 ? "…" : ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {violations && violations.length === 0 && <p>✅ No violations.</p>}
    </div>
  );
}