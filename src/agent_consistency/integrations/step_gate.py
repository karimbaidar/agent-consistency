from collections.abc import Callable, Mapping
from typing import Any, Optional, Tuple, TypeVar

from ..detect import RiskReport, detect_risks
from ..run import AgentStep, WorkflowRun
from ..store import ReceiptStore

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


def detect_workflow(
    workflow: Callable[[WorkflowRun], Any],
    *,
    run_id: Optional[str] = None,
    store: Optional[ReceiptStore] = None,
    source: str = "workflow",
) -> RiskReport:
    """Run an existing workflow in report mode and return a false-success risk report."""
    _, report = run_detected_workflow(
        workflow,
        run_id=run_id,
        store=store,
        source=source,
    )
    return report


def run_detected_workflow(
    workflow: Callable[[WorkflowRun], T],
    *,
    run_id: Optional[str] = None,
    store: Optional[ReceiptStore] = None,
    source: str = "workflow",
) -> Tuple[T, RiskReport]:
    """Run an existing workflow in report mode and return its result plus risk report."""
    run = WorkflowRun.detect(run_id, store=store)
    result = workflow(run)
    return result, detect_risks(run.receipts(), source=source)
