from collections.abc import Callable, Mapping
from typing import Any, Optional, TypeVar

from ..run import AgentStep, WorkflowRun

T = TypeVar("T")


def gated_step(
    run: WorkflowRun,
    agent: str,
    action: str,
    *,
    step_id: Optional[str] = None,
    metadata: Optional[Mapping[str, Any]] = None,
) -> AgentStep:
    """Return a receipt-backed step for a custom orchestrator node."""
    return run.step(agent, action, step_id=step_id, metadata=metadata)


def run_gated_step(
    run: WorkflowRun,
    agent: str,
    action: str,
    handler: Callable[[AgentStep], T],
    *,
    step_id: Optional[str] = None,
    metadata: Optional[Mapping[str, Any]] = None,
    outcome_name: Optional[str] = None,
    outcome_check: Optional[Callable[[T], bool]] = None,
) -> T:
    """Run a workflow handler inside a receipt gate and optionally verify its result."""
    with gated_step(run, agent, action, step_id=step_id, metadata=metadata) as step:
        result = handler(step)
        if outcome_name and outcome_check:
            step.verify_outcome(outcome_name, lambda: outcome_check(result))
        return result
