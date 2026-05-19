import { describe, it, expect } from "vitest";
import {
  WORK_ITEM_STATUS,
  ISSUE_STATUS,
  EXECUTION_STATUS,
  PRIORITY,
  SEVERITY,
  confidenceColor,
  confidenceLabel,
} from "./status";

describe("WORK_ITEM_STATUS", () => {
  it("covers all 5 statuses", () => {
    expect(Object.keys(WORK_ITEM_STATUS)).toEqual([
      "ready",
      "in_progress",
      "blocked",
      "waiting_for_approval",
      "done",
    ]);
  });

  it("each entry has required fields", () => {
    for (const cfg of Object.values(WORK_ITEM_STATUS)) {
      expect(cfg).toHaveProperty("label");
      expect(cfg).toHaveProperty("icon");
      expect(cfg).toHaveProperty("color");
      expect(cfg).toHaveProperty("bg");
      expect(cfg).toHaveProperty("border");
      expect(cfg).toHaveProperty("dot");
    }
  });
});

describe("ISSUE_STATUS", () => {
  it("covers all 4 statuses", () => {
    expect(Object.keys(ISSUE_STATUS)).toEqual([
      "open",
      "investigating",
      "resolved",
      "suppressed",
    ]);
  });
});

describe("EXECUTION_STATUS", () => {
  it("covers all 7 statuses", () => {
    expect(Object.keys(EXECUTION_STATUS)).toEqual([
      "pending",
      "running",
      "waiting_for_approval",
      "completed",
      "failed",
      "timed_out",
      "cancelled",
    ]);
  });
});

describe("PRIORITY", () => {
  it("critical pulses", () => {
    expect(PRIORITY.critical.pulse).toBe(true);
  });

  it("non-critical does not pulse", () => {
    expect(PRIORITY.high.pulse).toBe(false);
    expect(PRIORITY.medium.pulse).toBe(false);
    expect(PRIORITY.low.pulse).toBe(false);
  });

  it("all have labels", () => {
    expect(PRIORITY.critical.label).toBe("Critical");
    expect(PRIORITY.high.label).toBe("High");
    expect(PRIORITY.medium.label).toBe("Medium");
    expect(PRIORITY.low.label).toBe("Low");
  });
});

describe("SEVERITY", () => {
  it("includes info level beyond priority", () => {
    expect(SEVERITY.info).toBeDefined();
    expect(SEVERITY.info.label).toBe("Info");
    expect(SEVERITY.info.pulse).toBe(false);
  });

  it("shares priority values for critical-low", () => {
    expect(SEVERITY.critical).toBe(PRIORITY.critical);
    expect(SEVERITY.high).toBe(PRIORITY.high);
  });
});

describe("confidenceColor", () => {
  it("high confidence returns done color", () => {
    expect(confidenceColor(0.9)).toBe("text-status-done");
    expect(confidenceColor(0.8)).toBe("text-status-done");
  });

  it("moderate confidence returns in-progress color", () => {
    expect(confidenceColor(0.5)).toBe("text-status-in-progress");
    expect(confidenceColor(0.7)).toBe("text-status-in-progress");
  });

  it("low confidence returns blocked color", () => {
    expect(confidenceColor(0.3)).toBe("text-status-blocked");
    expect(confidenceColor(0.0)).toBe("text-status-blocked");
  });
});

describe("confidenceLabel", () => {
  it("returns High for >= 0.8", () => {
    expect(confidenceLabel(0.9)).toBe("High");
    expect(confidenceLabel(0.8)).toBe("High");
  });

  it("returns Moderate for >= 0.5", () => {
    expect(confidenceLabel(0.6)).toBe("Moderate");
    expect(confidenceLabel(0.5)).toBe("Moderate");
  });

  it("returns Low for < 0.5", () => {
    expect(confidenceLabel(0.2)).toBe("Low");
    expect(confidenceLabel(0.0)).toBe("Low");
  });
});
