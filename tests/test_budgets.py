import time

import pytest

from workbench.budgets import BudgetExceeded, RunBudget


@pytest.mark.parametrize(
    "budget,usage",
    [
        (RunBudget(max_steps=0), {}),
        (RunBudget(max_calls=0), {"calls": 1}),
        (RunBudget(max_tokens=10), {"tokens": 11}),
        (RunBudget(max_cost_usd=0), {"cost_usd": 0.01}),
        (RunBudget(started=time.monotonic() - 40), {}),
    ],
)
def test_budget_denies_operation_before_consumption(budget, usage):
    with pytest.raises(BudgetExceeded):
        budget.consume(**usage)
    assert budget.steps == 0


def test_budget_accumulates_and_cannot_be_refunded_by_negative_usage():
    budget = RunBudget(max_calls=2)
    budget.consume(calls=1)
    budget.consume(calls=1)
    with pytest.raises(BudgetExceeded):
        budget.consume(calls=1)
    with pytest.raises(ValueError):
        budget.consume(tokens=-1)
