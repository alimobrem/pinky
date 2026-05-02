from pinky_worker.llm.budget import ExecutionBudget


def test_budget_starts_empty() -> None:
    b = ExecutionBudget()
    assert b.check() is None
    assert b.total_tokens == 0


def test_budget_tracks_usage() -> None:
    b = ExecutionBudget()
    b.record_call(1000, 500)
    assert b.used_input_tokens == 1000
    assert b.used_output_tokens == 500
    assert b.used_calls == 1
    assert b.total_tokens == 1500


def test_budget_exceeds_input() -> None:
    b = ExecutionBudget(max_input_tokens=1000)
    b.record_call(1000, 0)
    err = b.check()
    assert err is not None
    assert "Input token budget" in err


def test_budget_exceeds_output() -> None:
    b = ExecutionBudget(max_output_tokens=500)
    b.record_call(0, 500)
    err = b.check()
    assert err is not None
    assert "Output token budget" in err


def test_budget_exceeds_calls() -> None:
    b = ExecutionBudget(max_calls=2)
    b.record_call(10, 10)
    b.record_call(10, 10)
    err = b.check()
    assert err is not None
    assert "Call budget" in err


def test_remaining_tokens() -> None:
    b = ExecutionBudget(max_input_tokens=5000, max_output_tokens=2000)
    b.record_call(1000, 500)
    assert b.remaining_input_tokens == 4000
    assert b.remaining_output_tokens == 1500
