from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List

from .models import ConsistencyReceipt
from .serialization import to_jsonable


@dataclass(frozen=True)
class CausalityGraph:
    nodes: List[Dict[str, Any]] = field(default_factory=list)
    edges: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": to_jsonable(self.nodes),
            "edges": to_jsonable(self.edges),
        }


def build_causality_graph(receipts: Iterable[ConsistencyReceipt]) -> CausalityGraph:
    receipt_list = list(receipts)
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    handoff_producers: Dict[str, str] = {}
    artifact_producers: Dict[str, str] = {}

    for receipt in receipt_list:
        nodes.append(
            {
                "id": receipt.key,
                "run_id": receipt.run_id,
                "step_id": receipt.step_id,
                "agent": receipt.agent,
                "action": receipt.action,
                "status": receipt.status,
            }
        )
        for handoff in receipt.handoffs:
            handoff_producers[handoff.handoff_id] = receipt.key
        for artifact in receipt.proof_artifacts:
            artifact_producers[artifact.artifact_id] = receipt.key

    for receipt in receipt_list:
        for parent in receipt.parent_receipt_keys:
            edges.append(
                {
                    "from": parent,
                    "to": receipt.key,
                    "kind": "parent_receipt",
                }
            )
        for handoff_id in receipt.consumed_handoff_ids:
            producer = handoff_producers.get(handoff_id)
            if producer:
                edges.append(
                    {
                        "from": producer,
                        "to": receipt.key,
                        "kind": "handoff",
                        "handoff_id": handoff_id,
                    }
                )
        for artifact_id in receipt.consumed_artifact_ids:
            producer = artifact_producers.get(artifact_id)
            if producer:
                edges.append(
                    {
                        "from": producer,
                        "to": receipt.key,
                        "kind": "artifact",
                        "artifact_id": artifact_id,
                    }
                )

    return CausalityGraph(nodes=nodes, edges=_dedupe_edges(edges))


def trace_causality(receipts: Iterable[ConsistencyReceipt]) -> str:
    graph = build_causality_graph(receipts)
    if not graph.edges:
        return "No causal links recorded."
    lines = []
    node_names = {
        node["id"]: f"{node['step_id']} ({node['agent']})" for node in graph.nodes
    }
    for edge in graph.edges:
        left = node_names.get(edge["from"], edge["from"])
        right = node_names.get(edge["to"], edge["to"])
        detail = edge.get("handoff_id") or edge.get("artifact_id") or edge["kind"]
        lines.append(f"{left} -> {right}: {detail}")
    return "\n".join(lines)


def _dedupe_edges(edges: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    deduped = []
    for edge in edges:
        key = tuple(sorted((name, str(value)) for name, value in edge.items()))
        if key not in seen:
            seen.add(key)
            deduped.append(edge)
    return deduped
