import type { Violation } from "../api/client";

export default function ViolationsTable({
  violations,
}: {
  violations: Violation[];
}) {
  if (violations.length === 0)
    return <p className="ok">No violations found.</p>;
  return (
    <table className="violations">
      <thead>
        <tr>
          <th>Column</th>
          <th>Rule</th>
          <th>Message</th>
          <th>Failed rows</th>
        </tr>
      </thead>
      <tbody>
        {violations.map((v, i) => (
          <tr key={i}>
            <td>{v.column}</td>
            <td>
              <code>{v.rule}</code>
            </td>
            <td>{v.message}</td>
            <td>
              {v.failed_rows.slice(0, 20).join(", ")}
              {v.failed_rows.length > 20 ? " …" : ""}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
