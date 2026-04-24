from .causality import CausalityGraph, build_causality_graph, trace_causality
from .contracts import HandoffContract
from .diff import DiffItem, RunDiff, diff_runs
from .errors import (
    ConsistencyError,
    DuplicateReceiptError,
    HandoffValidationError,
    OutcomeVerificationError,
    StaleStateError,
)
from .handoff import HandoffPacket
from .models import (
    ConsistencyIssue,
    ConsistencyReceipt,
    OutcomeResult,
    ProofArtifact,
    StateDelta,
    StateSnapshot,
)
from .outcome import OutcomeVerifier, verify_outcome
from .run import AgentStep, WorkflowRun
from .store import InMemoryReceiptStore, JsonlReceiptStore, ReceiptStore, load_receipts
from .verifier import (
    VerificationContext,
    VerifierRegistry,
    all_of,
    any_of,
    choose_verifier,
)

__version__ = "0.2.0"

__all__ = [
    "AgentStep",
    "CausalityGraph",
    "ConsistencyError",
    "ConsistencyIssue",
    "ConsistencyReceipt",
    "DiffItem",
    "DuplicateReceiptError",
    "HandoffContract",
    "HandoffPacket",
    "HandoffValidationError",
    "InMemoryReceiptStore",
    "JsonlReceiptStore",
    "OutcomeResult",
    "OutcomeVerificationError",
    "OutcomeVerifier",
    "ProofArtifact",
    "ReceiptStore",
    "RunDiff",
    "StaleStateError",
    "StateDelta",
    "StateSnapshot",
    "VerificationContext",
    "VerifierRegistry",
    "WorkflowRun",
    "all_of",
    "any_of",
    "build_causality_graph",
    "choose_verifier",
    "diff_runs",
    "load_receipts",
    "trace_causality",
    "verify_outcome",
]
