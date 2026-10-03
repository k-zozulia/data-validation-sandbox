import { countChecks, parseModel, serializeModel } from "./rulesModel";

describe("rules model", () => {
  it("round-trips YAML through the builder model", () => {
    const yaml = [
      "version: 2",
      "columns:",
      "  age:",
      "    not_null: {}",
      "    range: { min: 0, max: 120, severity: warning }",
      "dataset:",
      "  row_count: { min: 1 }",
    ].join("\n");
    const model = parseModel(yaml)!;
    expect(model.columns.age.range).toEqual({ min: 0, max: 120, severity: "warning" });
    expect(countChecks(model)).toBe(3);
    expect(parseModel(serializeModel(model))).toEqual(model);
    expect(serializeModel(model)).toContain("version: 2");
  });

  it("normalises null/true params and drops disabled checks", () => {
    const model = parseModel("columns:\n  a:\n    unique:\n    not_null: false\n")!;
    expect(model.columns.a).toEqual({ unique: {} });
  });

  it("drops empty params on serialize", () => {
    const text = serializeModel({
      extra: {},
      columns: { a: { range: { min: 1, max: undefined, message: "" } } },
      dataset: {},
    });
    expect(parseModel(text)!.columns.a.range).toEqual({ min: 1 });
  });

  it("returns null for broken YAML or wrong shape", () => {
    expect(parseModel("columns: [oops")).toBeNull();
    expect(parseModel("- a\n- b")).toBeNull();
    expect(parseModel("columns: [a, b]")).toBeNull();
  });
});
