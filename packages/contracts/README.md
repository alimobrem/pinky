# @pinky/contracts

Shared TypeScript domain types used by the web frontend and design system. Single source of truth for API response shapes, execution states, and event types.

## Usage

```typescript
import type { WorkItem, Execution, ExecutionEventType } from "@pinky/contracts";
```

## Key Types

- `WorkItem` — Task with status, priority, owner, artifact refs
- `Issue` — Correlated operational problem with severity, lifecycle
- `Execution` — Workflow run (investigation or remediation)
- `ExecutionEvent` — Timeline entry (started, progress, completed, failed, etc.)
- `ExecutionEventType` — Union of all event type strings
- `ClusterBinding` — Per-user cluster authentication binding
- `Definition` — Scanner/tool/skill/policy markdown definition

## Adding Types

1. Add the type to the appropriate file in `src/`
2. Export from `src/index.ts`
3. Run `pnpm test` to verify

## Testing

```bash
pnpm --filter @pinky/contracts test   # 22 tests (Vitest)
```
