import time
from dataclasses import dataclass, field


class BudgetExceeded(Exception):
    pass


@dataclass
class RunBudget:
    max_steps: int = 8
    max_calls: int = 5
    max_seconds: float = 30
    max_tokens: int = 4000
    max_cost_usd: float = 0
    started: float = field(default_factory=time.monotonic)
    steps: int = 0
    calls: int = 0
    tokens: int = 0
    cost_usd: float = 0

    def consume(self, *, calls: int = 0, tokens: int = 0, cost_usd: float = 0) -> None:
        if calls < 0 or tokens < 0 or cost_usd < 0:
            raise ValueError("Budget consumption cannot be negative")
        if (
            self.steps + 1 > self.max_steps
            or self.calls + calls > self.max_calls
            or self.tokens + tokens > self.max_tokens
            or self.cost_usd + cost_usd > self.max_cost_usd
            or time.monotonic() - self.started >= self.max_seconds
        ):
            raise BudgetExceeded("Run budget exhausted before the next operation")
        self.steps += 1
        self.calls += calls
        self.tokens += tokens
        self.cost_usd += cost_usd
