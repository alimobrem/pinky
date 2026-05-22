"""Tests for ExecutionBudget and BudgetExhausted exception."""

from __future__ import annotations

import pytest


class TestExecutionBudget:
    def test_record_call_accumulates(self) -> None:
        from pinky_worker.llm.budget import ExecutionBudget

        budget = ExecutionBudget(max_input_tokens=10_000, max_output_tokens=2_000, max_calls=5)

        assert budget.used_input_tokens == 0
        assert budget.used_output_tokens == 0
        assert budget.used_calls == 0

        budget.record_call(1000, 200)
        assert budget.used_input_tokens == 1000
        assert budget.used_output_tokens == 200
        assert budget.used_calls == 1

        budget.record_call(500, 100)
        assert budget.used_input_tokens == 1500
        assert budget.used_output_tokens == 300
        assert budget.used_calls == 2

    def test_check_returns_none_within_limits(self) -> None:
        from pinky_worker.llm.budget import ExecutionBudget

        budget = ExecutionBudget(max_input_tokens=10_000, max_output_tokens=2_000, max_calls=5)
        budget.record_call(5000, 1000)

        result = budget.check()
        assert result is None

    def test_check_returns_error_when_input_tokens_exceeded(self) -> None:
        from pinky_worker.llm.budget import ExecutionBudget

        budget = ExecutionBudget(max_input_tokens=1_000, max_output_tokens=2_000, max_calls=5)
        budget.record_call(1001, 100)

        result = budget.check()
        assert result is not None
        assert "Input token budget exceeded" in result
        assert "1001/1000" in result

    def test_check_returns_error_when_output_tokens_exceeded(self) -> None:
        from pinky_worker.llm.budget import ExecutionBudget

        budget = ExecutionBudget(max_input_tokens=10_000, max_output_tokens=500, max_calls=5)
        budget.record_call(100, 501)

        result = budget.check()
        assert result is not None
        assert "Output token budget exceeded" in result
        assert "501/500" in result

    def test_check_returns_error_when_call_limit_exceeded(self) -> None:
        from pinky_worker.llm.budget import ExecutionBudget

        budget = ExecutionBudget(max_input_tokens=10_000, max_output_tokens=2_000, max_calls=3)
        budget.record_call(100, 50)
        budget.record_call(100, 50)
        budget.record_call(100, 50)

        result = budget.check()
        assert result is not None
        assert "Call budget exceeded" in result
        assert "3/3" in result

    def test_remaining_input_tokens(self) -> None:
        from pinky_worker.llm.budget import ExecutionBudget

        budget = ExecutionBudget(max_input_tokens=10_000, max_output_tokens=2_000, max_calls=5)
        assert budget.remaining_input_tokens == 10_000

        budget.record_call(3000, 200)
        assert budget.remaining_input_tokens == 7000

        budget.record_call(8000, 100)
        assert budget.remaining_input_tokens == 0

    def test_remaining_output_tokens(self) -> None:
        from pinky_worker.llm.budget import ExecutionBudget

        budget = ExecutionBudget(max_input_tokens=10_000, max_output_tokens=2_000, max_calls=5)
        assert budget.remaining_output_tokens == 2_000

        budget.record_call(100, 500)
        assert budget.remaining_output_tokens == 1_500

        budget.record_call(100, 2000)
        assert budget.remaining_output_tokens == 0

    def test_total_tokens(self) -> None:
        from pinky_worker.llm.budget import ExecutionBudget

        budget = ExecutionBudget()
        budget.record_call(1500, 250)
        budget.record_call(800, 150)

        assert budget.total_tokens == 2700

    def test_budget_exhausted_exception_can_be_raised(self) -> None:
        from pinky_worker.llm.budget import BudgetExhausted

        with pytest.raises(BudgetExhausted):
            raise BudgetExhausted("Test budget exhausted")

    def test_budget_exhausted_exception_with_message(self) -> None:
        from pinky_worker.llm.budget import BudgetExhausted

        try:
            raise BudgetExhausted("Input token budget exceeded: 10001/10000")
        except BudgetExhausted as e:
            assert str(e) == "Input token budget exceeded: 10001/10000"
