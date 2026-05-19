# Pinky Web

Next.js 15 frontend for the Pinky platform. React 19, TypeScript, Tailwind CSS v4, shadcn/ui components.

## Running

```bash
make dev-web   # Next.js on :3000
```

## Pages

| Route | Page | Description |
|-------|------|-------------|
| `/dashboard` | Dashboard | Cluster health overview, recent activity, ROI metrics |
| `/tasks` | Tasks | Prioritized task inbox with investigation results, approval gate, execution log |
| `/tasks/[id]` | Task Detail | Full investigation, recommended actions, Brain chat, execution timeline |
| `/watch` | Watch | Live observations and executions across all clusters |
| `/history` | History | Audit trail with timeline, filtering, CSV export |
| `/clusters` | Clusters | Cluster registry, binding status, resource explorer |
| `/settings` | Settings | API tokens, webhook subscriptions, definitions management |
| `/login` | Login | OpenShift OAuth login |

## Directory Structure

```
src/
  app/
    (product)/              Authenticated layout (sidebar + header)
      dashboard/            Dashboard page + components
      tasks/                Task list + detail + execution views
      watch/                Live observation feed
      history/              Audit timeline
      clusters/             Cluster management
      settings/             Configuration pages
    login/                  OAuth login page
  components/
    shared/                 Cross-page components
      approval-gate.tsx     Approval UI with countdown, digest, dry-run
      execution-monitor.tsx Execution event stream
      data-table.tsx        Paginated table with cursor-based loading
    ui/                     shadcn/ui primitives (28 components)
  lib/
    api.ts                  Typed HTTP client
    utils.ts                cn() utility
    hooks/                  useSSE, useEventBus, usePaginatedData
```

## Patterns

- **Data fetching:** TanStack Query with co-located `queries.ts` per page
- **Real-time:** Singleton `EventBusProvider` — one EventSource per session, components subscribe via `useEventBus(id, handler)`
- **Forms:** react-hook-form + Zod schemas
- **Styling:** Tailwind v4 utility classes only. All custom CSS in `@layer base`. Use `text-caption` (11px) and `text-body-sm` (13px)
- **Types:** Import from `@pinky/contracts` — never redeclare locally
- **Icons:** lucide-react
- **Animation:** Motion v12 (FadeIn, StaggerList, AnimatePresence)

## Testing

```bash
cd apps/web
npx playwright test          # E2E tests
pnpm typecheck               # TypeScript check
```
