from .api import GateDecision, ReliabilityGate, reliability_gate, verified_step
from .causality import CausalityGraph, build_causality_graph, trace_causality
from .contracts import HandoffContract
from .detect import (
    RiskFinding,
    RiskReport,
    detect_receipt_file,
    detect_risks,
    render_risk_report,
)
from .diff import DiffItem, RunDiff, diff_runs
from .errors import (
    ConsistencyError,
    DuplicateReceiptError,
    HandoffValidationError,
    OutcomeVerificationError,
    StaleStateError,
)
from .handoff import HandoffPacket
from .integrations.microsoft_agent_framework import (
    MicrosoftAgentFrameworkConsistencyAdapter,
    MicrosoftAgentFrameworkNativeIntegration,
)
from .models import (
    ConsistencyIssue,
    ConsistencyReceipt,
    OutcomeResult,
    ProofArtifact,
    StateDelta,
    StateSnapshot,
)
from .outcome import (
    OutcomeVerifier,
    OutcomeVerifierProtocol,
    RefundSettlementVerifier,
    verify_outcome,
)
from .policy import FailurePolicy, PolicyDecision
from .receipt_verification import (
    ReceiptVerificationReport,
    VerificationIssue,
    render_verify_report,
    verify_receipt_file,
)
from .reporting import (
    load_receipt_report,
    render_text_summary,
    summarize_report,
    write_html_summary,
)
from .run import AgentStep, WorkflowRun
from .scanner import (
    ScanFinding,
    ScanReport,
    render_scan_markdown,
    render_scan_text,
    scan_report_to_json,
    scan_target,
)
from .store import (
    BufferedReceiptStore,
    InMemoryReceiptStore,
    JsonlReceiptStore,
    OtelReceiptExporter,
    PostgresReceiptStore,
    ReceiptStore,
    load_receipts,
)
from .verifier import (
    VerificationContext,
    VerifierRegistry,
    all_of,
    any_of,
    choose_verifier,
)

__version__ = "0.3.3"

__all__ = [
    "AgentStep",
    "BufferedReceiptStore",
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
    "load_receipt_report",
    "MicrosoftAgentFrameworkConsistencyAdapter",
    "MicrosoftAgentFrameworkNativeIntegration",
    "OutcomeResult",
    "OutcomeVerificationError",
    "OutcomeVerifier",
    "OutcomeVerifierProtocol",
    "FailurePolicy",
    "GateDecision",
    "OtelReceiptExporter",
    "ProofArtifact",
    "PolicyDecision",
    "PostgresReceiptStore",
    "ReliabilityGate",
    "ReceiptStore",
    "ReceiptVerificationReport",
    "RiskFinding",
    "RiskReport",
    "ScanFinding",
    "ScanReport",
    "RefundSettlementVerifier",
    "detect_receipt_file",
    "detect_risks",
    "render_text_summary",
    "render_risk_report",
    "render_scan_markdown",
    "render_scan_text",
    "render_verify_report",
    "RunDiff",
    "StaleStateError",
    "StateDelta",
    "StateSnapshot",
    "VerificationContext",
    "VerificationIssue",
    "VerifierRegistry",
    "WorkflowRun",
    "all_of",
    "any_of",
    "build_causality_graph",
    "choose_verifier",
    "diff_runs",
    "load_receipts",
    "reliability_gate",
    "scan_report_to_json",
    "scan_target",
    "summarize_report",
    "trace_causality",
    "verify_receipt_file",
    "verify_outcome",
    "verified_step",
    "write_html_summary",
]
