import { describe, it, expect } from "vitest";

/**
 * Tests for the proxy route's stream detection logic.
 * We replicate isStreamRequest here since it's not exported from the route file.
 */
function isStreamRequest(request: Request): boolean {
  const accept = request.headers.get("accept") ?? "";
  if (accept.includes("text/event-stream")) return true;
  const url = new URL(request.url);
  return url.pathname.includes("/streams/");
}

describe("isStreamRequest", () => {
  it("detects text/event-stream accept header", () => {
    const req = new Request("http://localhost:3000/api/v1/work-items", {
      headers: { accept: "text/event-stream" },
    });
    expect(isStreamRequest(req)).toBe(true);
  });

  it("detects /streams/ in URL path", () => {
    const req = new Request(
      "http://localhost:3000/api/v1/streams/events",
    );
    expect(isStreamRequest(req)).toBe(true);
  });

  it("detects execution stream path", () => {
    const req = new Request(
      "http://localhost:3000/api/v1/streams/executions/abc-123",
    );
    expect(isStreamRequest(req)).toBe(true);
  });

  it("returns false for regular API requests", () => {
    const req = new Request("http://localhost:3000/api/v1/work-items");
    expect(isStreamRequest(req)).toBe(false);
  });

  it("returns false for JSON accept header", () => {
    const req = new Request("http://localhost:3000/api/v1/issues", {
      headers: { accept: "application/json" },
    });
    expect(isStreamRequest(req)).toBe(false);
  });

  it("returns false for POST to non-stream endpoint", () => {
    const req = new Request("http://localhost:3000/api/v1/executions", {
      method: "POST",
      headers: { "content-type": "application/json" },
    });
    expect(isStreamRequest(req)).toBe(false);
  });
});

/**
 * Tests for buildTargetUrl logic.
 * Replicated since the route file doesn't export it.
 */
function buildTargetUrl(requestUrl: string, proxyTarget = "http://localhost:8000"): URL {
  const incoming = new URL(requestUrl);
  const target = new URL(proxyTarget);
  const proxiedPath = incoming.pathname.replace(/^\/api\/?/, "");
  const basePath = target.pathname.replace(/\/$/, "");
  target.pathname = `${basePath}/api/${proxiedPath}`.replace(/\/+/g, "/");
  target.search = incoming.search;
  return target;
}

describe("buildTargetUrl", () => {
  it("rewrites /api/v1/issues to proxy target", () => {
    const url = buildTargetUrl("http://localhost:3000/api/v1/issues");
    expect(url.toString()).toBe("http://localhost:8000/api/v1/issues");
  });

  it("preserves query params", () => {
    const url = buildTargetUrl(
      "http://localhost:3000/api/v1/issues?status=open&limit=50",
    );
    expect(url.searchParams.get("status")).toBe("open");
    expect(url.searchParams.get("limit")).toBe("50");
  });

  it("handles stream paths", () => {
    const url = buildTargetUrl(
      "http://localhost:3000/api/v1/streams/events",
    );
    expect(url.pathname).toBe("/api/v1/streams/events");
  });
});
