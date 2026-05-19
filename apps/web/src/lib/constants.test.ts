import { describe, it, expect } from "vitest";
import { QUERY_KEYS, SIDEBAR_WIDTH, MOTION, BREAKPOINTS } from "./constants";

describe("QUERY_KEYS", () => {
  it("tasks factory returns consistent keys", () => {
    expect(QUERY_KEYS.tasks()).toEqual(["tasks", undefined]);
    expect(QUERY_KEYS.tasks({ status: "open" })).toEqual([
      "tasks",
      { status: "open" },
    ]);
  });

  it("task by id returns unique key", () => {
    expect(QUERY_KEYS.task("abc")).toEqual(["task", "abc"]);
  });

  it("session returns stable key", () => {
    expect(QUERY_KEYS.session()).toEqual(["session"]);
  });

  it("cluster keys are distinct", () => {
    expect(QUERY_KEYS.cluster("x")).toEqual(["cluster", "x"]);
    expect(QUERY_KEYS.clusters()).toEqual(["clusters"]);
    expect(QUERY_KEYS.clusterNodes("x")).toEqual(["cluster-nodes", "x"]);
  });

  it("definitions accepts optional kind", () => {
    expect(QUERY_KEYS.definitions()).toEqual(["definitions", undefined]);
    expect(QUERY_KEYS.definitions("scanner")).toEqual([
      "definitions",
      "scanner",
    ]);
  });
});

describe("SIDEBAR_WIDTH", () => {
  it("has expected values", () => {
    expect(SIDEBAR_WIDTH.iconRail).toBe(56);
    expect(SIDEBAR_WIDTH.detailPanel).toBe(220);
  });
});

describe("MOTION", () => {
  it("open duration is positive", () => {
    expect(MOTION.open.duration).toBeGreaterThan(0);
  });

  it("stagger has staggerChildren", () => {
    expect(MOTION.stagger.staggerChildren).toBeGreaterThan(0);
  });
});

describe("BREAKPOINTS", () => {
  it("has expected breakpoint values", () => {
    expect(BREAKPOINTS.sm).toBe(640);
    expect(BREAKPOINTS.md).toBe(768);
    expect(BREAKPOINTS.lg).toBe(1024);
    expect(BREAKPOINTS.xl).toBe(1280);
  });
});
