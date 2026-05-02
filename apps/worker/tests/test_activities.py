from pinky_worker.execution.activities import compute_evidence_hash, EvidenceBundle


def test_evidence_hash_deterministic() -> None:
    sections = {"status": "running", "events": "none"}
    h1 = compute_evidence_hash(sections)
    h2 = compute_evidence_hash(sections)
    assert h1 == h2


def test_evidence_hash_differs_on_content() -> None:
    h1 = compute_evidence_hash({"status": "running"})
    h2 = compute_evidence_hash({"status": "failed"})
    assert h1 != h2


def test_evidence_hash_order_independent() -> None:
    h1 = compute_evidence_hash({"a": "1", "b": "2"})
    h2 = compute_evidence_hash({"b": "2", "a": "1"})
    assert h1 == h2


def test_evidence_bundle_construction() -> None:
    bundle = EvidenceBundle(
        issue_id="i1",
        cluster_id="c1",
        fingerprint="fp1",
        evidence_hash="eh1",
        sections={"status": "running"},
    )
    assert bundle.issue_id == "i1"
    assert not bundle.truncated
