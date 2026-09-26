"""The coding agent the Ralph loop drives. One call = one iteration with fresh context.

Real adapter not built (docs §6, M5): recommended mini-swe-agent (LiteLLM → GMI) in a per-ticket Docker
sandbox. Progress persists in the ticket's git branch + a progress file, not in the agent's context.
"""

from typing import Protocol

from pydantic import BaseModel


class Iteration(BaseModel):
    summary: str
    diff_stat: str
    tests_passed: bool
    test_output: str
    branch: str


class CodingAgent(Protocol):
    async def run_iteration(self, issue_number: int, spec: str, iteration: int) -> Iteration: ...


class RealCodingAgent:
    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        raise NotImplementedError("Coding agent harness not built yet (docs §6, M5)")

    async def run_iteration(self, issue_number: int, spec: str, iteration: int) -> Iteration:  # pragma: no cover
        raise NotImplementedError


class FakeCodingAgent:
    """Tests pass from iteration `passes_at` onward (1-based); never passes if None."""

    def __init__(self, passes_at: int | None = 2) -> None:
        self.passes_at = passes_at

    async def run_iteration(self, issue_number: int, spec: str, iteration: int) -> Iteration:
        passed = self.passes_at is not None and iteration >= self.passes_at
        return Iteration(
            summary=f"[fake-agent] iteration {iteration}",
            diff_stat="1 file changed",
            tests_passed=passed,
            test_output="ok" if passed else "FAILED test_fix",
            branch=f"jev/issue-{issue_number}",
        )
