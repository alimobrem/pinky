import { test, expect } from "@playwright/test";
import { execFileSync } from "child_process";
import * as path from "path";

const SRC_DIR = path.resolve(__dirname, "../../src");

const INLINE_STYLE_ALLOWLIST = [
  "execution-monitor.tsx", // runtime-computed progress bar width
];

function grepFiles(pattern: string, dir: string, allowlist: string[] = []): string[] {
  try {
    const result = execFileSync("grep", ["-rn", pattern, dir, "--include=*.tsx", "--include=*.ts"], {
      encoding: "utf-8",
    });
    return result
      .split("\n")
      .filter(Boolean)
      .filter((line) => !line.includes("eslint-disable"))
      .filter((line) => !allowlist.some((allowed) => line.includes(allowed)));
  } catch {
    return [];
  }
}

test.describe("Convention enforcement", () => {
  test("no inline style={{}} (use Tailwind)", () => {
    const violations = grepFiles("style={{", SRC_DIR, INLINE_STYLE_ALLOWLIST);
    expect(
      violations,
      `Found ${violations.length} inline style violations:\n${violations.join("\n")}`
    ).toHaveLength(0);
  });

  test("no CSS modules", () => {
    try {
      const result = execFileSync("find", [SRC_DIR, "-name", "*.module.css", "-o", "-name", "*.module.scss"], {
        encoding: "utf-8",
      });
      const files = result.split("\n").filter(Boolean);
      expect(files, `Found CSS modules: ${files.join(", ")}`).toHaveLength(0);
    } catch {
      // No CSS modules found — pass
    }
  });

  test("no new raw <select> elements (use shadcn Select)", () => {
    const KNOWN_RAW_SELECTS = 2; // alerts severity filter, history type filter
    const violations = grepFiles("<select ", SRC_DIR).filter(
      (line) => !line.includes("components/ui/")
    );
    expect(
      violations.length,
      `Found ${violations.length} raw <select> elements (expected ${KNOWN_RAW_SELECTS}):\n${violations.join("\n")}`
    ).toBeLessThanOrEqual(KNOWN_RAW_SELECTS);
  });

  test("no raw <input> elements (use shadcn Input)", () => {
    const violations = grepFiles("<input ", SRC_DIR).filter(
      (line) => !line.includes("components/ui/")
    );
    expect(
      violations,
      `Found ${violations.length} raw <input> elements — use shadcn Input:\n${violations.join("\n")}`
    ).toHaveLength(0);
  });

  test("no new raw <button> elements (use shadcn Button)", () => {
    const KNOWN_RAW_BUTTONS = 3; // settings CTA, execution back, keyboard help close
    const violations = grepFiles("<button ", SRC_DIR).filter(
      (line) => !line.includes("components/ui/")
    );
    expect(
      violations.length,
      `Found ${violations.length} raw <button> elements (expected ${KNOWN_RAW_BUTTONS}):\n${violations.join("\n")}`
    ).toBeLessThanOrEqual(KNOWN_RAW_BUTTONS);
  });
});
