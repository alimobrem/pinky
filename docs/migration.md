# Pinky Migration Strategy

## Coexistence with Legacy Pulse

Pinky and pulse-agent are separate deployments. They can observe the same clusters simultaneously via independent observer identities. No shared database, no shared state.

- Pinky uses its own Postgres, Redis, and Temporal instances
- Pinky observer SA is separate from pulse-agent's SA
- Both can be deployed to the same OpenShift cluster without conflict
- Users can use both UIs during transition

## Data Import Strategy

### Import
- Scanner configurations: translate to Pinky scanner definitions (MD files)
- Suppression rules: translate to Pinky policy definitions (MD files)
- PromQL recipes: translate to tool definitions
- Runbooks: port as skill definitions

### Do Not Import
- Raw incident history: different schema, different semantics
- Chat transcripts: not relevant to task-first model
- Tool usage logs: pulse-agent-specific patterns
- Memory/learning data: tied to pulse-agent's prompt structure

## Rollback Plan

If Pinky is removed:
- Cluster observer SAs created by Pinky Helm chart are removed
- User cluster bindings are revoked
- Historical data remains in Pinky's Postgres until explicitly deleted
- pulse-agent continues operating independently

## ROI Comparison

To measure Pinky vs legacy Pulse on the same fleet:
1. Run both in parallel for 2-4 weeks
2. Compare: MTTR, false positive rate, operator override rate, LLM cost per resolution
3. Use Pinky's analytics/ROI dashboard for Pinky metrics
4. Use pulse-agent's eval system for pulse metrics
5. Same clusters, same timeframe, different observers
