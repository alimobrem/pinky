---
name: default-triage
kind: pipeline
version: 1.0.0
trigger: new_observation
---
# Default Triage Pipeline

Standard signal processing pipeline for all observations.

## Steps

1. **Normalize** — convert raw observation to standard fingerprint using cluster_id + resource_kind + resource_namespace + resource_name + scanner + check_id
2. **Correlate** — group into existing issue by correlation key, or create new issue. If correlation key matches a recently resolved issue (< 1 hour), reopen instead of creating new.
3. **Evaluate policy** — run through policy rules ordered by priority. First matching rule wins.
4. **Gate** — based on policy result:
   - `suppress`: log to history, skip further processing
   - `observe`: add to Watch, wait for recurrence threshold (2+ consecutive scan cycles)
   - `investigate`: dispatch to The Brain with the matching skill
   - `auto_resolve`: execute known-safe remediation skill (requires prior verified outcomes)
   - `create_task`: generate work item with Brain-prepared plan
5. **Emit event** — publish domain event for webhook delivery and analytics
