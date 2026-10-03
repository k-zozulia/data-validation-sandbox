// Two-way mapping between the rules YAML and a plain object model used by the
// visual builder. Keys the builder doesn't know about (comments aside) survive
// a round trip, so switching between YAML and builder never loses data.
import { parse, stringify } from "yaml";

export type Params = Record<string, unknown>;
export type ChecksMap = Record<string, Params>;
export type RulesModel = {
  extra: Record<string, unknown>;
  columns: Record<string, ChecksMap>;
  dataset: ChecksMap;
};

export function emptyModel(): RulesModel {
  return { extra: {}, columns: {}, dataset: {} };
}

function asChecks(value: unknown): ChecksMap {
  if (!value || typeof value !== "object" || Array.isArray(value)) return {};
  const out: ChecksMap = {};
  for (const [name, params] of Object.entries(value as Record<string, unknown>)) {
    if (params === false) continue;
    out[name] =
      params && typeof params === "object" && !Array.isArray(params)
        ? { ...(params as Params) }
        : {};
  }
  return out;
}

/** Returns null when the YAML can't be represented (syntax error / wrong shape). */
export function parseModel(text: string): RulesModel | null {
  let data: unknown;
  try {
    data = parse(text || "") ?? {};
  } catch {
    return null;
  }
  if (typeof data !== "object" || Array.isArray(data) || data === null) return null;
  const { columns, dataset, ...extra } = data as Record<string, unknown>;
  const model: RulesModel = { extra, columns: {}, dataset: asChecks(dataset) };
  if (columns && typeof columns === "object" && !Array.isArray(columns)) {
    for (const [col, checks] of Object.entries(columns as Record<string, unknown>)) {
      model.columns[col] = asChecks(checks);
    }
  } else if (columns !== undefined && columns !== null) {
    return null;
  }
  return model;
}

/** Drop empty/undefined params so the YAML stays minimal. */
function clean(params: Params): Params {
  const out: Params = {};
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    if (Array.isArray(v) && v.length === 0) continue;
    out[k] = v;
  }
  return out;
}

export function serializeModel(model: RulesModel): string {
  const doc: Record<string, unknown> = { ...model.extra };
  const columns: Record<string, ChecksMap> = {};
  for (const [col, checks] of Object.entries(model.columns)) {
    columns[col] = Object.fromEntries(Object.entries(checks).map(([n, p]) => [n, clean(p)]));
  }
  doc.columns = columns;
  if (Object.keys(model.dataset).length) {
    doc.dataset = Object.fromEntries(Object.entries(model.dataset).map(([n, p]) => [n, clean(p)]));
  }
  return stringify(doc, { lineWidth: 100 });
}

export function countChecks(model: RulesModel): number {
  return (
    Object.values(model.columns).reduce((n, c) => n + Object.keys(c).length, 0) +
    Object.keys(model.dataset).length
  );
}
