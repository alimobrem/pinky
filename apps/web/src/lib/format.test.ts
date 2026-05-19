import { describe, it, expect } from "vitest";
import {
  relativeTime,
  shortTime,
  fullDateTime,
  compactNumber,
  percentLabel,
} from "./format";

describe("relativeTime", () => {
  it("returns relative string for recent dates", () => {
    const fiveMinAgo = new Date(Date.now() - 5 * 60 * 1000).toISOString();
    expect(relativeTime(fiveMinAgo)).toContain("ago");
  });

  it("returns formatted date for dates older than 24h", () => {
    const twoDaysAgo = new Date(Date.now() - 48 * 60 * 60 * 1000).toISOString();
    const result = relativeTime(twoDaysAgo);
    expect(result).toMatch(/\d{4}/);
  });

  it("returns raw string for invalid dates", () => {
    expect(relativeTime("not-a-date")).toBe("not-a-date");
  });
});

describe("shortTime", () => {
  it("returns HH:mm:ss format", () => {
    expect(shortTime("2026-01-15T14:30:45Z")).toMatch(/\d{2}:\d{2}:\d{2}/);
  });

  it("returns raw string for invalid date", () => {
    expect(shortTime("nope")).toBe("nope");
  });
});

describe("fullDateTime", () => {
  it("returns full formatted date with year and time", () => {
    const result = fullDateTime("2026-01-15T14:30:45Z");
    expect(result).toContain("2026");
    expect(result).toContain("at");
  });

  it("returns raw string for invalid date", () => {
    expect(fullDateTime("bad")).toBe("bad");
  });
});

describe("compactNumber", () => {
  it("returns k suffix for thousands", () => {
    expect(compactNumber(1500)).toBe("1.5k");
  });

  it("returns raw number below 1000", () => {
    expect(compactNumber(999)).toBe("999");
  });

  it("handles exactly 1000", () => {
    expect(compactNumber(1000)).toBe("1.0k");
  });

  it("handles zero", () => {
    expect(compactNumber(0)).toBe("0");
  });
});

describe("percentLabel", () => {
  it("converts fraction to percent string", () => {
    expect(percentLabel(0.85)).toBe("85%");
  });

  it("rounds to nearest integer", () => {
    expect(percentLabel(0.333)).toBe("33%");
  });

  it("handles 0 and 1", () => {
    expect(percentLabel(0)).toBe("0%");
    expect(percentLabel(1)).toBe("100%");
  });
});
