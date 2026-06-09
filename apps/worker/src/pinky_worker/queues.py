from datetime import timedelta

INVESTIGATION_QUEUE = "investigation"
REMEDIATION_QUEUE = "remediation"
OBSERVATION_QUEUE = "observation"
PROJECTION_QUEUE = "projection"

ALL_QUEUES = [
    INVESTIGATION_QUEUE,
    REMEDIATION_QUEUE,
    OBSERVATION_QUEUE,
    PROJECTION_QUEUE,
]

INVESTIGATION_TIMEOUT = timedelta(minutes=30)
REMEDIATION_TIMEOUT = timedelta(hours=5)
VERIFICATION_TIMEOUT = timedelta(minutes=10)
