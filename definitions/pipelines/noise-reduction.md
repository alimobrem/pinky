---
name: noise-reduction
kind: pipeline
version: 1.0.0
trigger: pre_policy
---
# Noise Reduction Pipeline

Runs before the policy engine to filter out known-noisy signals and prevent
them from consuming policy evaluation and investigation resources.

## Steps

1. **Dedup window** — if the same fingerprint was seen within the current
   scan interval, collapse to the latest observation (don't create duplicate)
2. **Flap detection** — if an issue has toggled open/resolved >3 times in
   24 hours, mark as flapping and suppress for 1 hour
3. **Burst suppression** — if a single scanner emits >20 observations for
   the same cluster in one scan cycle, batch into a single "burst" issue
   rather than creating 20 individual issues
4. **Scanner quality gate** — if a scanner's false-positive rate (from
   analytics) exceeds 50% over the last 7 days, demote its severity by one
   level before policy evaluation
5. **Emit metrics** — log suppression/dedup/burst counts to analytics_events
   for scanner quality dashboards
