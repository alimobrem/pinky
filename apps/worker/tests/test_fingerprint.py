from pinky_worker.observation.fingerprint import compute_correlation_key, compute_observation_fingerprint


def test_fingerprint_deterministic() -> None:
    fp1 = compute_observation_fingerprint("c1", "pod-health", "oom-killed", "Pod", "ns1", "app-pod")
    fp2 = compute_observation_fingerprint("c1", "pod-health", "oom-killed", "Pod", "ns1", "app-pod")
    assert fp1 == fp2


def test_fingerprint_differs_by_cluster() -> None:
    fp1 = compute_observation_fingerprint("c1", "pod-health", "oom-killed", "Pod", "ns1", "app-pod")
    fp2 = compute_observation_fingerprint("c2", "pod-health", "oom-killed", "Pod", "ns1", "app-pod")
    assert fp1 != fp2


def test_fingerprint_differs_by_check() -> None:
    fp1 = compute_observation_fingerprint("c1", "pod-health", "oom-killed", "Pod", "ns1", "app-pod")
    fp2 = compute_observation_fingerprint("c1", "pod-health", "crash-loop", "Pod", "ns1", "app-pod")
    assert fp1 != fp2


def test_correlation_key_deterministic() -> None:
    ck1 = compute_correlation_key("c1", "Pod", "ns1", "app-pod", "pod-health", "oom-killed")
    ck2 = compute_correlation_key("c1", "Pod", "ns1", "app-pod", "pod-health", "oom-killed")
    assert ck1 == ck2


def test_correlation_key_differs_by_resource() -> None:
    ck1 = compute_correlation_key("c1", "Pod", "ns1", "app-pod-1", "pod-health", "oom-killed")
    ck2 = compute_correlation_key("c1", "Pod", "ns1", "app-pod-2", "pod-health", "oom-killed")
    assert ck1 != ck2
