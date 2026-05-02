# Pinky UI Design

## Design Intent

`Pinky` should feel playful in brand and serious in operation. The UI should never feel like a dashboard dumping ground or a hidden-chat experiment. It should feel like an operations workspace with a clear center of gravity: tasks.

`The Brain` is present throughout the product, but the UI is not chat-first. It is task-first.

## Core Navigation

Top-level product navigation:

- `Tasks`
- `Watch`
- `History`
- `Alerts`
- `Settings`

Secondary controls:
- cluster selector
- principal/session status
- cluster binding status
- global search / command bar (Cmd+K)

The cluster selector uses hybrid semantics:
- overview pages may show multi-cluster summaries
- detailed task/workspace/execution views are cluster-scoped

## Overall Layout

```
┌──────────────────────────────────────────────────────────┐
│ TopBar: [Pinky logo] [Cluster selector] [Search] [User] │
├────────┬─────────────────────────────────┬───────────────┤
│ NavRail│      MainView                   │ ContextPanel  │
│ Tasks  │                                 │ (optional)    │
│ Watch  │                                 │               │
│ History│                                 │               │
│ Alerts │                                 │               │
│ Settings│                                │               │
├────────┴─────────────────────────────────┴───────────────┤
```

### Layout behavior
- Left navigation rail for top-level sections (200px desktop, 56px icon-only tablet, bottom bar mobile)
- Top bar for cluster context, principal/session state, and global actions
- Main content area for the current page
- Optional right-side context panel (400px) for task summary or execution state on desktop; drawer on tablet; full-page on mobile

## Design System Tokens

### Colors
| Token | Purpose |
|---|---|
| `--bg-primary` | Page background |
| `--bg-surface` | Card/panel background |
| `--bg-elevated` | Elevated surface (dialogs, dropdowns) |
| `--text-primary` | Primary text |
| `--text-secondary` | Secondary/muted text |
| `--accent-brand` | Pinky brand accent |
| `--accent-brain` | Brain presence (purple) |
| `--status-ready` | Blue — task ready |
| `--status-in-progress` | Amber — in progress |
| `--status-blocked` | Red — blocked |
| `--status-approval` | Orange — waiting for approval |
| `--status-done` | Green — completed |
| `--border-default` | Default borders |
| `--border-focus` | Focus ring (2px) |

### Typography
| Scale | Size | Weight | Use |
|---|---|---|---|
| `--type-heading` | 20px | 600 | Page/section headings |
| `--type-subheading` | 16px | 600 | Card headings |
| `--type-body` | 14px | 400 | Body text (minimum readable) |
| `--type-caption` | 12px | 400 | Timestamps, metadata |

### Spacing
4px base grid. Tokens: `--space-1` (4px), `--space-2` (8px), `--space-3` (12px), `--space-4` (16px), `--space-6` (24px), `--space-8` (32px).

### Components
Primitives: Button, Badge, Chip, Card, Skeleton, Spinner, Dialog, Tooltip, Toast, IconButton, Stack, Grid, Divider, DataTable, FilterBar, EmptyState, ErrorState, LoadingState, StatusChip.

## Task Lifecycle State Machine

```
         ┌─────────────────────────────────┐
         │                                 │
ready ──Accept──► accepted ──Start──► in_progress ──Complete──► done ──► History
                                       │    │
                                       │    └──Request Approval──► waiting_for_approval
                                       │                              │
                                       └──Mark Blocked──► blocked     │
                                                                      │
                                       ◄──approve─────────────────────┘
                                       ◄──reject (revision needed)────┘

Any active state ──Reassign──► changes owner, may return to team queue
Binding loss ──► auto-reassign to team queue
```

## Tasks Page

The default landing page.

### Main regions
- Summary strip: `Ready`, `In Progress`, `Blocked`, `Needs Approval` with count badges
- Main list groups: `My Tasks`, `Team Queue`
- Filter bar: owner, priority, cluster, namespace/workload, approval-needed, risk

### Task row
Each row shows: title, one-line summary, recommended next step, priority badge, owner, scope chip, confidence badge, approval badge.

Completed work does not live as a done queue. Brief "recently completed" toast may appear. Canonical surface for done work is History.

## Task Detail

The detail view answers, in order:
1. What happened
2. Why it matters
3. What The Brain recommends
4. What the operator should do now
5. What already happened before

### Sections
- `Summary` — issue context, why_now, severity
- `Plan` — Brain-generated plan with steps, risk level, confidence
- `Evidence` — investigation artifacts, topology/blast-radius views, resource state
- `Execution` — timeline of Brain + human actions
- `History` — previous occurrences, related tasks

### Hydrated workspace
Task detail is a hydrated workspace backed by stored investigation/plan artifacts, refreshed on open with bounded live hydration:
- Loading: skeleton sections with "Hydrating workspace..." indicator
- Stale: "Data may be outdated — cluster last observed 5m ago" warning
- Binding expired: "Cluster access expired — reconnect to see live data" with reconnect button, historical artifacts still shown
- Cluster removed: "This cluster was removed from Pinky. Showing historical data only."
- Hydration timeout (10s): fall back to cached artifact with staleness indicator

### Action buttons

#### Accept
- **Visible when:** state is `ready`
- **On click:** no confirmation dialog, immediate transition
- **Result:** state -> `accepted`, owner set to current user

#### Start
- **Visible when:** state is `accepted`
- **On click:** immediate transition
- **Result:** state -> `in_progress`

#### Mark Blocked
- **Visible when:** state is `in_progress`
- **On click:** dialog with required "Reason for block" text field, Cancel/Confirm
- **Result:** state -> `blocked` with recorded reason

#### Request Approval
- **Visible when:** state is `in_progress` and a plan with change-set exists
- **On click:** opens approval dialog showing change-set summary, affected resources, risk level, Brain recommendation
- **Result:** state -> `waiting_for_approval`, creates Approval object

#### Complete
- **Visible when:** state is `in_progress`, `accepted`, or `blocked`
- **On click:** confirmation: "Mark complete? It will move to History." Cancel/Complete.
- **Result:** state -> `done`, task moves to History, "Completed" toast shown

#### Reassign
- **Visible when:** any active state
- **On click:** dialog with searchable user list, Cancel/Reassign

All actions use optimistic UI: update locally on click, revert on server error with toast.

## Watch Page

The operator's window into what The Brain is doing now.

### Update cadence
SSE-driven with sub-10-second latency. Header shows: "Live — updated 3s ago" with green dot, or "Connection lost — retrying..." with red dot.

### Categories (collapsible sections with count badges)

```
┌──────────────────────────────────────────────────────────┐
│ Watch                                  Live ● updated 3s │
├──────────────────────────────────────────────────────────┤
│ ▼ Signals Under Analysis (4)                             │
│   [● pulsing] Analyzing: Pod restart loop in ns/payments │
│     cluster-prod-east — 12s ago                          │
│                                                          │
│ ▼ Auto-Remediations In Progress (1)                      │
│   [● spinner] Scaling deployment/api-gateway 2→4         │
│     cluster-staging — started 45s ago  [View execution]  │
│                                                          │
│ ▼ Grouped Issues (2)                                     │
│   5 OOMKilled observations → Issue #142                  │
│     cluster-prod-east — correlated 1m ago                │
│                                                          │
│ ▼ Suppressions / Dedup (7)                               │
│   Suppressed: CrashLoopBackOff on test-runner (flaky)    │
│     cluster-staging — 2m ago                             │
│                                                          │
│ ▼ Candidate Task Creation (1)                            │
│   [Brain] Preparing: Certificate expiry in 7d            │
│     cluster-prod-east — confidence: 0.85                 │
│                                                          │
│ ▼ Active Executions & Approvals (2)                      │
│   Awaiting approval: rollback deployment/checkout-v2     │
│     cluster-prod-west — 3m ago  [View details]           │
└──────────────────────────────────────────────────────────┘
```

### Real-time animation
- New items: 300ms slide-down + subtle blue highlight fading over 2s
- Status changes: changed field flashes 500ms yellow highlight
- Removed items: 300ms fade-out + height collapse
- Category count badges: brief scale pulse on change

## Approval Flow — User Journey

### Step 1: Arrival
Via: task in `waiting_for_approval` state, Watch "Active Executions", toast notification, or direct link.

### Step 2: Approval Detail

```
┌─── Approval Required ─────────────────────────────────┐
│ Change-Set Summary                                     │
│ ┌───────────────────────────────────────────────────┐ │
│ │ Action: Scale deployment/api-gateway 2 → 4        │ │
│ │ Cluster: cluster-prod-east                        │ │
│ │ Namespace: payments                               │ │
│ │ Change-set digest: sha256:a1b2c3...               │ │
│ └───────────────────────────────────────────────────┘ │
│ Affected Resources                                     │
│  • Deployment/api-gateway (payments)                   │
│  • HPA/api-gateway (payments) — will be paused         │
│                                                        │
│ Risk Level: [HIGH]                                     │
│                                                        │
│ The Brain recommends:                                  │
│ "Scaling is safest for current OOM pattern."           │
│ [▸ View full reasoning]                                │
│                                                        │
│ Reauth: [✓ Session fresh] or [⚠ Fresh login needed]   │
│                                                        │
│                        [Reject]  [Approve]             │
└────────────────────────────────────────────────────────┘
```

### Step 3: Approve or Reject
- **Approve:** If fresh session: confirmation dialog. If reauth needed: reauth modal first. On confirm: toast "Approval recorded. Execution starting."
- **Reject:** Dialog with required "Reason for rejection" text field. On confirm: toast "Approval rejected." Task returns to `in_progress`.

### Step 4: Drift Invalidation
If issue/resources/changeset changes before execution: banner "Approval is no longer valid. Resources changed." with [View updated plan] and [Request new approval].

## The Brain — Ambient Presence

### Inline Attribution Blocks
```
┌─ 🧠 The Brain recommends ──────────────────────────────┐
│ Scale deployment/api-gateway to 4 replicas.             │
│ [▸ View reasoning]                                      │
│   - evidence considered                                 │
│   - tools used                                          │
│   - alternatives evaluated                              │
│   - confidence: 0.92                                    │
└─────────────────────────────────────────────────────────┘
```

### Activity indicators
- Watch: pulsing purple dot (`--accent-brain`) + action description when active, static dot when idle
- Execution timeline: Brain avatar for Brain-initiated events, user avatar for human events
- Collapsible reasoning sections: default collapsed, persists open/closed per session

## History Page

### Shows
Completed tasks, suppressions, approvals (granted/rejected), remediations, verification outcomes, rollbacks, postmortems.

### Interactions
Filter by cluster, issue/task state, date range. Inspect execution details. Jump to related issue/task.

## Alerts Page

Raw observability surface. Shows: unprocessed alerts/signals, severity, source, related issue/task linkage.

Rule: alerts never appear as task rows unless the pipeline explicitly converts them.

## Settings Page

### Sections
- **Cluster Registry** (admin): table of clusters, add/remove, onboarding state, observer health
- **User Cluster Bindings**: binding status per cluster, bind/reconnect/unbind
- **Service Bindings** (admin): external service connections (Prometheus, Datadog, etc.), health status, add/remove
- **Definitions** (admin): browse/search/create/edit scanners, tools, skills, pipelines, policies, redaction rules, approval policies as markdown. Syntax-highlighted editor with frontmatter validation.
- **Webhook Subscriptions** (admin): outbound webhook management, event pattern configuration, delivery status, formatter selection
- **Policy Rules** (admin): declarative policy rules, priority ordering, dry-run testing
- **Brain Usage / Telemetry**: token spend, cache hit rate, model tier breakdown, most expensive issues
- **Analytics / ROI**: ROI dashboard, scanner quality, eval scores (see implementation plan Task 8.5)
- **API Tokens**: create/revoke long-lived tokens for CLI and CI automation
- **User Profile**: display name, linked providers, active sessions

## Real-Time Update Rendering Model

### New items
New rows animate in from top with 300ms slide-down + subtle highlight fading over 2s.

### Status changes
Changed field flashes: brief scale-up (1.1x, 200ms) + 500ms highlight.

### Batch updates
If >5 items update within 2s: suppress individual animations, show "N new items" sticky banner (auto-dismiss 10s or scroll-to-top).

### Optimistic UI
Accept/Start/Complete/Reassign update local state immediately. Loading state during round-trip. Revert + error toast on server rejection.

### Connection loss
SSE drop: "Connection lost — retrying..." banner with spinner. Reconnect with refetch. After 30s: "Connection lost. [Retry now]".

## Keyboard Navigation

| Key | Action |
|---|---|
| `Cmd+K` / `Ctrl+K` | Open command bar |
| `Escape` | Close command bar / dialog / panel / go back |
| `?` | Show keyboard shortcuts |
| `j` / `k` | Next / previous item in list |
| `Enter` | Open focused item in detail |
| `Space` | Open in context panel (desktop) |
| `Tab` / `Shift+Tab` | Navigate between page regions |
| `a` | Accept task (when valid) |
| `s` | Start task (when valid) |
| `c` | Complete task (when valid) |

Dialogs: focus trapped, Tab cycles controls, Escape dismisses, Enter activates focused button.

## Notification / Toast Pattern

- Bottom-right, 360px wide
- Left border colored by severity: blue (info), green (success), yellow (warning), red (error)
- Auto-dismiss: 5s (info/success), 10s (warning/error)
- Manually dismissible, stacks max 3, oldest dismissed for overflow

## Cluster Selector

- Dropdown with search
- Multi-select for overview pages, single-select for detail views
- Binding status indicator per cluster (green dot = valid, yellow = expiring, red = expired, gray = missing)
- Switching cluster refetches scoped data with loading state

## Command Bar

Opens with Cmd+K. Searches tasks, clusters, history. Results grouped by type. Supports quick navigation.

## Auth and Session UI

### Login
Provider choice (OpenShift / external OIDC). Server-managed flow. Same-origin redirect on success. Auto-link on verified email match.

### Session surfaces
- Session status in top bar
- Cluster binding state per cluster in selector
- Reauth prompts on expiry (not generic failure banners)
- Session UX states: signed in + binding valid, binding missing, binding expired, approval blocked by freshness, in-flight execution with expired binding

## Error Recovery Flows

### Per-section retry
Each section loads independently. Failed section shows: "[Section] failed to load. [Retry]". Working sections remain interactive.

### Partial failure
"Some clusters could not be reached. Showing available data. [Retry failed clusters]"

### Full page error
Centered: icon + "Something went wrong" + actionable text + [Retry]. Auth errors redirect to reauth.

## Empty / Loading / Error States

| Surface | Empty | Loading | Binding expired | Cluster removed |
|---|---|---|---|---|
| Tasks | "No tasks need human attention right now." | Skeleton rows + summary placeholders | Tasks removed from queue, reconnect prompt | Tasks archived, no longer actionable |
| Watch | "The Brain is not actively escalating anything right now." | Skeleton cards per category | Live drill-down unavailable, summary remains | Cleared from live views |
| History | "No operational history yet." | Skeleton rows | Visible, but sensitive evidence refresh disabled | Read-only historical records |
| Alerts | "No active alerts." | Skeleton rows | Sensitive drill-down requires user identity | N/A |

## Responsiveness

| Breakpoint | Range | NavRail | Context Panel | Detail |
|---|---|---|---|---|
| Desktop | ≥1280px | Full rail (200px) | Right panel (400px) | Inline or panel |
| Tablet | 768–1279px | Collapsible (56px icons) | Full-width drawer | Full-page |
| Mobile | <768px | Bottom tab bar (56px) | N/A | Full-page |

## Accessibility

- Keyboard-accessible navigation and lists
- Focus trapping in dialogs
- No hover-only critical state
- Color never sole meaning channel — all statuses have text labels and/or icons
- Minimum 14px body text
- ARIA landmarks for page regions
- ARIA live regions for toasts and real-time banners
- WCAG AA contrast (4.5:1 body, 3:1 large text)

## Visual Design Principles

- Modern, operational, deliberate
- No glassy/noisy "AI dashboard" aesthetics
- Strong hierarchy, calm surfaces
- Agent state via motion sparingly (pulsing dots, highlight fades)
- Dense but readable task rows
- Brain presence uses `--accent-brain` consistently but subtly

## UI Tone

Brand can be playful. Product language stays clear. "The Brain recommends..." is fine. Core nouns (task, approval, alert, history) stay plain and operational. Don't turn them into jokes.

## Future Extension Points

The UI architecture preserves the ability to add extensions later without restructuring:

1. **Data-driven NavRail.** Navigation items rendered from a config array, not hardcoded JSX:
   ```typescript
   interface NavItem {
     id: string;
     label: string;
     icon: ComponentType;
     path: string;
     badge?: number;
     section: 'primary' | 'secondary' | 'plugin';  // 'plugin' reserved
   }
   ```

2. **Composable Settings sections.** Each Settings section is a self-contained component. Adding a plugin settings section requires registering a component, not modifying the page.

3. **Composable Task Detail sections.** The hydrated workspace renders sections from a list. Future plugins could inject sections.

4. **File-based routing.** Next.js App Router allows adding route segments without restructuring. A `plugins/` route namespace is reserved.

5. **Design system package.** Extensions import `@pinky/design-system` for visual consistency.

No runtime module federation, iframe embedding, or dynamic import system in v1. The design system and data-driven components are the preparation layer.

## Cross-References

- PRD: `./2026-05-01-pinky-prd.md`
- SDS: `./2026-05-01-pinky-sds.md`
- Architecture Decisions: `./2026-05-01-pinky-architecture-decisions.md`
- Implementation Plan: `../plans/2026-05-01-pinky-platform.md`
