"""Webhook delivery worker — polls domain_events and delivers to subscribers.

Runs as a persistent async loop alongside Temporal workers and observer.
Matches events against subscription patterns, formats payloads, POSTs
to subscriber URLs with retry and exponential backoff.
"""

from __future__ import annotations

import asyncio
import fnmatch
import json
import logging
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx

from pinky_worker.db import get_pool
from pinky_worker.webhooks.formatters import format_event

logger = logging.getLogger(__name__)

POLL_INTERVAL = 5
MAX_RETRIES = 5
BACKOFF_BASE = 1
BACKOFF_CAP = 30


def _matches_pattern(event_type: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(event_type, p) for p in patterns)


async def _deliver_one(url: str, payload: dict, timeout: float = 10) -> tuple[int, str]:
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, timeout=timeout)
        return response.status_code, response.text[:200]


async def run_delivery_loop() -> None:
    logger.info("webhook delivery worker started")
    last_processed = datetime.now(UTC) - timedelta(minutes=5)

    while True:
        try:
            pool = await get_pool()

            events = await pool.fetch(
                """SELECT id, event_type, aggregate_type, aggregate_id, cluster_id,
                          principal_id, payload, occurred_at
                   FROM domain_events
                   WHERE occurred_at > $1
                   ORDER BY occurred_at ASC
                   LIMIT 100""",
                last_processed,
            )

            if events:
                subs = await pool.fetch(
                    """SELECT id, name, url, event_patterns, formatter, channel_config
                       FROM webhook_subscriptions
                       WHERE enabled = true""",
                )

                for event in events:
                    event_type = event["event_type"]
                    event_dict = dict(event)
                    event_dict["payload"] = json.loads(event_dict["payload"]) if isinstance(event_dict["payload"], str) else event_dict["payload"]
                    event_dict["aggregate_id"] = str(event_dict["aggregate_id"])

                    for sub in subs:
                        patterns = list(sub["event_patterns"])
                        if not _matches_pattern(event_type, patterns):
                            continue

                        formatted = format_event(event_dict, sub["formatter"])
                        delivery_id = uuid4()

                        await pool.execute(
                            """INSERT INTO webhook_deliveries (id, subscription_id, domain_event_id, status, attempts, created_at)
                               VALUES ($1, $2, $3, 'pending', 0, $4)""",
                            delivery_id, sub["id"], event["id"], datetime.now(UTC),
                        )

                        for attempt in range(MAX_RETRIES):
                            try:
                                status_code, body = await _deliver_one(sub["url"], formatted)
                                if 200 <= status_code < 300:
                                    await pool.execute(
                                        """UPDATE webhook_deliveries SET status = 'delivered', attempts = $2,
                                           last_attempt_at = $3, last_response_code = $4 WHERE id = $1""",
                                        delivery_id, attempt + 1, datetime.now(UTC), status_code,
                                    )
                                    logger.info(
                                        "webhook delivered for subscription %s event %s status %s",
                                        sub["name"],
                                        event_type,
                                        status_code,
                                    )
                                    break
                                else:
                                    logger.warning(
                                        "webhook delivery failed for subscription %s status %s attempt %s",
                                        sub["name"],
                                        status_code,
                                        attempt + 1,
                                    )
                            except Exception:
                                logger.warning(
                                    "webhook delivery error for subscription %s attempt %s",
                                    sub["name"],
                                    attempt + 1,
                                )

                            backoff = min(BACKOFF_BASE * (2 ** attempt), BACKOFF_CAP)
                            await asyncio.sleep(backoff)
                        else:
                            await pool.execute(
                                """UPDATE webhook_deliveries SET status = 'exhausted', attempts = $2,
                                   last_attempt_at = $3 WHERE id = $1""",
                                delivery_id, MAX_RETRIES, datetime.now(UTC),
                            )
                            logger.error(
                                "webhook delivery exhausted for subscription %s event %s",
                                sub["name"],
                                event_type,
                            )

                    last_processed = event["occurred_at"]

        except Exception:
            logger.exception("webhook delivery loop error")

        await asyncio.sleep(POLL_INTERVAL)
