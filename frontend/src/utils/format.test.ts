import { cellText, formatBytes, formatPct, formatStat, scoreTone, timeAgo } from "./format";

describe("format helpers", () => {
  it("formats bytes", () => {
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(1536)).toBe("1.5 KB");
    expect(formatBytes(50 * 1024 * 1024)).toBe("50 MB");
  });

  it("formats stats and percentages", () => {
    expect(formatStat(1234567)).toBe("1,234,567");
    expect(formatStat(3.14159)).toBe("3.142");
    expect(formatStat(null)).toBe("—");
    expect(formatPct(99.0)).toBe("99%");
    expect(formatPct(12.345)).toBe("12.3%");
  });

  it("maps scores to tones", () => {
    expect(scoreTone(99)).toBe("good");
    expect(scoreTone(85)).toBe("warn");
    expect(scoreTone(10)).toBe("bad");
    expect(scoreTone(null)).toBe("none");
  });

  it("renders relative time and cells", () => {
    const now = Date.parse("2026-01-01T12:00:00Z");
    expect(timeAgo("2026-01-01T11:00:00Z", now)).toBe("1 hour ago");
    expect(cellText({ a: 1 })).toBe('{"a":1}');
    expect(cellText(null)).toBe("");
  });
});
