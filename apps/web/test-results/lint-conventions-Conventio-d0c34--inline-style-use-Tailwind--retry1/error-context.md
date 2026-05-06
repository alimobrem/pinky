# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: lint-conventions.spec.ts >> Convention enforcement >> no inline style={{}} (use Tailwind)
- Location: tests/e2e/lint-conventions.spec.ts:27:7

# Error details

```
Error: Found 3 inline style violations:
/Users/amobrem/ali/pinky/apps/web/src/app/(product)/settings/_components/analytics-tab.tsx:128:                            style={{ width: `${pct}%` }}
/Users/amobrem/ali/pinky/apps/web/src/app/(product)/tasks/[id]/_components/task-detail-view.tsx:583:            style={{ width: `${Math.min(95, (elapsed / 35) * 100)}%` }}
/Users/amobrem/ali/pinky/apps/web/src/components/ui/progress.tsx:23:        style={{ transform: `translateX(-${100 - (value || 0)}%)` }}

expect(received).toHaveLength(expected)

Expected length: 0
Received length: 3
Received array:  ["/Users/amobrem/ali/pinky/apps/web/src/app/(product)/settings/_components/analytics-tab.tsx:128:                            style={{ width: `${pct}%` }}", "/Users/amobrem/ali/pinky/apps/web/src/app/(product)/tasks/[id]/_components/task-detail-view.tsx:583:            style={{ width: `${Math.min(95, (elapsed / 35) * 100)}%` }}", "/Users/amobrem/ali/pinky/apps/web/src/components/ui/progress.tsx:23:        style={{ transform: `translateX(-${100 - (value || 0)}%)` }}"]
```

# Test source

```ts
  1  | import { test, expect } from "@playwright/test";
  2  | import { execFileSync } from "child_process";
  3  | import * as path from "path";
  4  | 
  5  | const SRC_DIR = path.resolve(__dirname, "../../src");
  6  | 
  7  | const INLINE_STYLE_ALLOWLIST = [
  8  |   "execution-monitor.tsx", // runtime-computed progress bar width
  9  | ];
  10 | 
  11 | function grepFiles(pattern: string, dir: string, allowlist: string[] = []): string[] {
  12 |   try {
  13 |     const result = execFileSync("grep", ["-rn", pattern, dir, "--include=*.tsx", "--include=*.ts"], {
  14 |       encoding: "utf-8",
  15 |     });
  16 |     return result
  17 |       .split("\n")
  18 |       .filter(Boolean)
  19 |       .filter((line) => !line.includes("eslint-disable"))
  20 |       .filter((line) => !allowlist.some((allowed) => line.includes(allowed)));
  21 |   } catch {
  22 |     return [];
  23 |   }
  24 | }
  25 | 
  26 | test.describe("Convention enforcement", () => {
  27 |   test("no inline style={{}} (use Tailwind)", () => {
  28 |     const violations = grepFiles("style={{", SRC_DIR, INLINE_STYLE_ALLOWLIST);
  29 |     expect(
  30 |       violations,
  31 |       `Found ${violations.length} inline style violations:\n${violations.join("\n")}`
> 32 |     ).toHaveLength(0);
     |       ^ Error: Found 3 inline style violations:
  33 |   });
  34 | 
  35 |   test("no CSS modules", () => {
  36 |     try {
  37 |       const result = execFileSync("find", [SRC_DIR, "-name", "*.module.css", "-o", "-name", "*.module.scss"], {
  38 |         encoding: "utf-8",
  39 |       });
  40 |       const files = result.split("\n").filter(Boolean);
  41 |       expect(files, `Found CSS modules: ${files.join(", ")}`).toHaveLength(0);
  42 |     } catch {
  43 |       // No CSS modules found — pass
  44 |     }
  45 |   });
  46 | 
  47 |   test("no raw <select> elements (use shadcn Select)", () => {
  48 |     const violations = grepFiles("<select ", SRC_DIR).filter(
  49 |       (line) => !line.includes("components/ui/")
  50 |     );
  51 |     expect(
  52 |       violations,
  53 |       `Found ${violations.length} raw <select> elements — use shadcn Select:\n${violations.join("\n")}`
  54 |     ).toHaveLength(0);
  55 |   });
  56 | 
  57 |   test("no raw <input> elements (use shadcn Input)", () => {
  58 |     const violations = grepFiles("<input ", SRC_DIR).filter(
  59 |       (line) => !line.includes("components/ui/")
  60 |     );
  61 |     expect(
  62 |       violations,
  63 |       `Found ${violations.length} raw <input> elements — use shadcn Input:\n${violations.join("\n")}`
  64 |     ).toHaveLength(0);
  65 |   });
  66 | 
  67 |   test("no raw <button> elements (use shadcn Button)", () => {
  68 |     const violations = grepFiles("<button ", SRC_DIR).filter(
  69 |       (line) => !line.includes("components/ui/")
  70 |     );
  71 |     expect(
  72 |       violations,
  73 |       `Found ${violations.length} raw <button> elements — use shadcn Button:\n${violations.join("\n")}`
  74 |     ).toHaveLength(0);
  75 |   });
  76 | });
  77 | 
```