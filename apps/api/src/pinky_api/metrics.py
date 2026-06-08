"""Prometheus metrics for Pinky API."""

from prometheus_client import Counter, Gauge, Histogram, Info

REQUEST_COUNT = Counter(
    "pinky_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "pinky_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

ACTIVE_SSE_CONNECTIONS = Gauge(
    "pinky_sse_active_connections",
    "Active SSE connections",
)

OBSERVATIONS_TOTAL = Counter(
    "pinky_observations_total",
    "Total observations recorded",
    ["scanner", "severity"],
)

INVESTIGATIONS_TOTAL = Counter(
    "pinky_investigations_total",
    "Total investigations",
    ["status"],
)

LLM_CALLS_TOTAL = Counter(
    "pinky_llm_calls_total",
    "Total LLM API calls",
    ["model_tier", "provider"],
)

LLM_TOKENS_TOTAL = Counter(
    "pinky_llm_tokens_total",
    "Total LLM tokens used",
    ["direction"],
)

CACHE_HIT_TOTAL = Counter(
    "pinky_cache_hits_total",
    "Investigation cache hits",
)

CACHE_MISS_TOTAL = Counter(
    "pinky_cache_misses_total",
    "Investigation cache misses",
)

BUILD_INFO = Info(
    "pinky_build",
    "Build information",
)
