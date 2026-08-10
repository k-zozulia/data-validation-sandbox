import { useState } from "react";
import * as api from "./api/client";
import type { DatasetProfile, Violation } from "./api/client";
import RulesPanel from "./components/RulesPanel";
import ViolationsTable from "./components/ViolationsTable";
import { ProfileChart, ViolationsChart } from "./components/StatsDashboard";

export default function App() {
  const [file, setFile] = useState<File | null>(null);
  const [rules, setRules] = useState("");
  const [profile, setProfile] = useState<DatasetProfile | null>(null);
  const [violations, setViolations] = useState<Violation[] | null>(null);
  const [summary, setSummary] = useState("");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);

  function requireFile(): boolean {
    if (!file) {
      setStatus("Choose a file first.");
      return false;
    }
    return true;
  }

  async function onProfile() {
    if (!requireFile()) return;
    setBusy(true);
    setStatus("Profiling…");
    setViolations(null);
    setJobId(null);
    try {
      const r = await api.profile(file!);
      setProfile(r.profile);
      setRules(r.starter_rules_yaml);
      setStatus(
        `Profiled ${r.profile.row_count} rows, ${r.profile.column_count} columns. ` +
          "Edit the rules below, then validate.",
      );
    } catch (e: any) {
      setStatus("Error: " + e.message);
    } finally {
      setBusy(false);
    }
  }

  async function onSample() {
    if (!requireFile()) return;
    setBusy(true);
    setStatus("Validating sample…");
    setJobId(null);
    try {
      const r = await api.validateSample(file!, rules);
      setViolations(r.violations);
      setSummary(
        `Sample of ${r.sample_rows} rows — ${r.summary.total_violations} violation(s)`,
      );
      setStatus("Sample check done.");
    } catch (e: any) {
      setStatus("Error: " + e.message);
    } finally {
      setBusy(false);
    }
  }

  async function onFull() {
    if (!requireFile()) return;
    setBusy(true);
    setStatus("Queuing full run…");
    setViolations(null);
    setJobId(null);
    try {
      const { job_id } = await api.createJob(file!, rules);
      pollJob(job_id);
    } catch (e: any) {
      setStatus("Error: " + e.message);
      setBusy(false);
    }
  }

  function pollJob(id: string) {
    setStatus("Running full validation…");
    const tick = async () => {
      try {
        const s = await api.getJob(id);
        if (s.status === "done") {
          setViolations(s.result.violations);
          setSummary(
            `Full run of ${s.result.row_count} rows — ${s.result.total_violations} violation(s); ` +
              `${s.result.clean_rows} clean / ${s.result.quarantine_rows} quarantined`,
          );
          setJobId(id);
          setStatus("Full run done.");
          setBusy(false);
        } else if (s.status === "error") {
          setStatus(
            "Job error: " + (s.error?.detail ?? s.error?.error ?? "unknown"),
          );
          setBusy(false);
        } else {
          setStatus(`Full run: ${s.status}…`);
          setTimeout(tick, 1500);
        }
      } catch (e: any) {
        setStatus("Error: " + e.message);
        setBusy(false);
      }
    };
    tick();
  }

  return (
    <div className="app">
      <header>
        <h1>Data Validation Sandbox</h1>
      </header>

      <section className="card">
        <div className="file-picker">
          <label htmlFor="file-input" className="btn">
            Choose file
          </label>
          <input
            id="file-input"
            type="file"
            accept=".csv,.json,.parquet"
            onChange={(e) => {
              setFile(e.target.files?.[0] ?? null);
              setProfile(null);
              setViolations(null);
              setJobId(null);
              setStatus("");
            }}
          />
          <span className="file-name">
            {file ? file.name : "No file chosen"}
          </span>
        </div>
        <div className="buttons">
          <button onClick={onProfile} disabled={busy}>
            1. Profile &amp; generate rules
          </button>
          <button onClick={onSample} disabled={busy || !rules}>
            2. Validate sample
          </button>
          <button onClick={onFull} disabled={busy || !rules}>
            3. Run full
          </button>
        </div>
        {status && <p className="status">{status}</p>}
      </section>

      {profile && (
        <section className="card">
          <ProfileChart profile={profile} />
        </section>
      )}

      {(profile || rules) && (
        <section className="card">
          <h3>Rules</h3>
          <RulesPanel
            columns={
              profile
                ? Object.entries(profile.columns).map(([name, c]) => ({
                    name,
                    isArray: c.is_array,
                  }))
                : []
            }
            rulesYaml={rules}
            onChange={setRules}
          />
        </section>
      )}

      {violations && (
        <section className="card">
          {summary && <p className="summary">{summary}</p>}
          {jobId && (
            <div className="buttons">
              <a className="btn" href={api.exportUrl(jobId, "clean")}>
                Download clean.csv
              </a>
              <a className="btn" href={api.exportUrl(jobId, "quarantine")}>
                Download quarantine.csv
              </a>
            </div>
          )}
          <ViolationsChart violations={violations} />
          <ViolationsTable violations={violations} />
        </section>
      )}
    </div>
  );
}
