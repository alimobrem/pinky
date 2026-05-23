#!/usr/bin/env bash
set -euo pipefail

DB_URL="${PINKY_DB_URL:-postgresql://pinky:pinky@localhost:5432/pinky}"
ANALYTICS_RETENTION_DAYS="${PINKY_ANALYTICS_RETENTION_DAYS:-90}"
EVENTS_RETENTION_DAYS="${PINKY_EVENTS_RETENTION_DAYS:-180}"

echo "Deleting analytics_events older than ${ANALYTICS_RETENTION_DAYS} days..."
psql "${DB_URL}" -c "DELETE FROM analytics_events WHERE occurred_at < now() - interval '${ANALYTICS_RETENTION_DAYS} days';"

echo "Deleting execution_events older than ${EVENTS_RETENTION_DAYS} days..."
psql "${DB_URL}" -c "DELETE FROM execution_events WHERE occurred_at < now() - interval '${EVENTS_RETENTION_DAYS} days';"

echo "Data retention complete."
