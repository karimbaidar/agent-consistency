from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, Dict, List

from .models import ConsistencyReceipt
from .serialization import to_jsonable


@dataclass(frozen=True)
class DiffItem:
    kind: str
    message: str
    step_id: str = ""
    left: Any = None
    right: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "step_id": self.step_id,
            "message": self.message,
            "left": to_jsonable(self.left),
            "right": to_jsonable(self.right),
        }


@dataclass(frozen=True)
class RunDiff:
    differences: List[DiffItem] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.differences

    def summary(self) -> str:
        if self.is_empty:
            return "No consistency differences found."
        return "\n".join(
            f"- [{item.kind}] {item.step_id}: {item.message}" for item in self.differences
        )

    def to_dict(self) -> Dict[str, Any]:
        return {"differences": [item.to_dict() for item in self.differences]}


def diff_runs(left: Iterable[ConsistencyReceipt], right: Iterable[ConsistencyReceipt]) -> RunDiff:
    left_by_step = {receipt.step_id: receipt for receipt in left}
    right_by_step = {receipt.step_id: receipt for receipt in right}
    differences: List[DiffItem] = []

    for missing in sorted(set(left_by_step) - set(right_by_step)):
        differences.append(
            DiffItem("step_missing", f"step '{missing}' exists only in left run", step_id=missing)
        )
    for missing in sorted(set(right_by_step) - set(left_by_step)):
        differences.append(
            DiffItem("step_added", f"step '{missing}' exists only in right run", step_id=missing)
        )

    for step_id in sorted(set(left_by_step) & set(right_by_step)):
        _compare_receipts(step_id, left_by_step[step_id], right_by_step[step_id], differences)

    return RunDiff(differences=differences)


def _compare_receipts(
    step_id: str,
    left: ConsistencyReceipt,
    right: ConsistencyReceipt,
    differences: List[DiffItem],
) -> None:
    if left.assumptions != right.assumptions:
        differences.append(
            DiffItem(
                "assumptions",
                "assumptions diverged",
                step_id=step_id,
                left=left.assumptions,
                right=right.assumptions,
            )
        )
    _compare_snapshot_list(
        step_id,
        "state_read",
        "state read diverged",
        [snapshot.to_dict() for snapshot in left.state_reads],
        [snapshot.to_dict() for snapshot in right.state_reads],
        differences,
    )
    _compare_snapshot_list(
        step_id,
        "state_delta",
        "state delta diverged",
        [delta.to_dict() for delta in left.state_deltas],
        [delta.to_dict() for delta in right.state_deltas],
        differences,
    )
    _compare_list(
        step_id,
        "handoff",
        "handoff packet diverged",
        [handoff.to_dict() for handoff in left.handoffs],
        [handoff.to_dict() for handoff in right.handoffs],
        differences,
        ignore_fields={"created_at"},
    )
    _compare_list(
        step_id,
        "proof_artifact",
        "proof artifact diverged",
        [artifact.to_dict() for artifact in left.proof_artifacts],
        [artifact.to_dict() for artifact in right.proof_artifacts],
        differences,
        ignore_fields={"created_at"},
    )
    _compare_list(
        step_id,
        "outcome",
        "outcome diverged",
        [outcome.to_dict() for outcome in left.outcomes],
        [outcome.to_dict() for outcome in right.outcomes],
        differences,
        ignore_fields={"checked_at"},
    )
    if left.consumed_handoff_ids != right.consumed_handoff_ids:
        differences.append(
            DiffItem(
                "causality",
                "consumed handoff ids diverged",
                step_id=step_id,
                left=left.consumed_handoff_ids,
                right=right.consumed_handoff_ids,
            )
        )


def _strip_fields(payload: Any, ignore_fields: set) -> Any:
    if isinstance(payload, Mapping):
        return {
            key: _strip_fields(value, ignore_fields)
            for key, value in payload.items()
            if key not in ignore_fields
        }
    if isinstance(payload, list):
        return [_strip_fields(item, ignore_fields) for item in payload]
    return payload


def _compare_snapshot_list(
    step_id: str,
    kind: str,
    message: str,
    left: List[Dict[str, Any]],
    right: List[Dict[str, Any]],
    differences: List[DiffItem],
) -> None:
    _compare_list(
        step_id,
        kind,
        message,
        left,
        right,
        differences,
        ignore_fields={"captured_at"},
    )


def _compare_list(
    step_id: str,
    kind: str,
    message: str,
    left: List[Dict[str, Any]],
    right: List[Dict[str, Any]],
    differences: List[DiffItem],
    *,
    ignore_fields: set,
) -> None:
    left_clean = _strip_fields(left, ignore_fields)
    right_clean = _strip_fields(right, ignore_fields)
    if left_clean != right_clean:
        differences.append(
            DiffItem(kind, message, step_id=step_id, left=left_clean, right=right_clean)
        )
