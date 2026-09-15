"""Post-process Agent-produced architecture semantics.

Semantic interpretation belongs to the Agent.  This module deliberately does not
infer architecture concepts from keywords or regular expressions.  It accepts an
Agent ArchitectureModel contract and performs only normalization, compatibility
mapping, evidence preservation, and deterministic fallback for already-structured
content.
"""
from __future__ import annotations

from typing import Any
import re

from src.architecture.model import ArchitectureModel, ArchitectureNode, ArchitectureRelation, EvidenceRef


def _safe_id(value: str, index: int) -> str:
    candidate = re.sub(r"[^A-Za-z0-9._:-]+", "-", value.strip()).strip("-._:")
    return candidate[:80] or f"evidence-{index}"


def _as_evidence(value: Any, *, source: str = "") -> EvidenceRef:
    if isinstance(value, EvidenceRef):
        return value
    if isinstance(value, dict):
        payload = dict(value)
        if source and not payload.get("source"):
            payload["source"] = source
        return EvidenceRef.from_value(payload)
    return EvidenceRef(source=source, quote=str(value or ""))


def _agent_model(raw: dict[str, Any]) -> dict[str, Any] | None:
    value = raw.get("architecture_model")
    return value if isinstance(value, dict) else None


def _normalize_agent_contract(raw: dict[str, Any]) -> dict[str, Any]:
    """Return a model-shaped mapping without interpreting prose."""
    model = _agent_model(raw)
    if model is not None:
        return model
    if "elements" in raw or "nodes" in raw:
        return raw
    return {}


def _structured_fallback(raw: dict[str, Any]) -> ArchitectureModel:
    """Compatibility path for parser output when no Agent model was supplied.

    It preserves explicit headings, entities, tables, and relationships as
    evidence-bearing candidates. It never classifies prose by keyword and never
    invents relationships.
    """
    title = str(raw.get("document_title", raw.get("title", "Architecture")))
    nodes: list[ArchitectureNode] = []
    source_evidence: list[EvidenceRef] = []
    explicit = list(raw.get("entities", [])) + list(raw.get("nodes", []))
    for index, item in enumerate(explicit, 1):
        if not isinstance(item, dict):
            continue
        node = ArchitectureNode.from_dict(item, default_id=f"node-{index}")
        nodes.append(node)
        source_evidence.extend(node.source_evidence)

    # Keep parser-provided structured blocks available for review, but label them
    # as unclassified evidence instead of pretending that they are semantic nodes.
    if not nodes:
        structured = raw.get("structured_text", []) or raw.get("sections", []) or raw.get("paragraphs", [])
        for index, item in enumerate(structured, 1):
            if isinstance(item, dict):
                text = str(item.get("text", item.get("content", item.get("title", "")))).strip()
                locator = str(item.get("source_ref", item.get("id", "")))
            else:
                text, locator = str(item).strip(), ""
            if not text:
                continue
            evidence = EvidenceRef(source=str(raw.get("source_file", "")), locator=locator, quote=text)
            node = ArchitectureNode(
                id=_safe_id(text, index), title=text[:100], description=text,
                type="unclassified_evidence", level="L2", priority="secondary",
                source_evidence=[evidence], metadata={"semantic_source": "fallback_unclassified"},
            )
            nodes.append(node); source_evidence.append(evidence)

    relations: list[ArchitectureRelation] = []
    for index, item in enumerate(raw.get("relations", raw.get("relationships", raw.get("edges", []))) or [], 1):
        if isinstance(item, dict):
            relations.append(ArchitectureRelation.from_dict(item, default_id=f"rel-{index}"))

    return ArchitectureModel(
        project=str(raw.get("project", raw.get("metadata", {}).get("source_format", ""))),
        title=title, nodes=nodes, relations=relations,
        source_evidence=source_evidence,
        metadata={"semantic_source": "structured_fallback", "requires_agent_review": True},
        diagnostics=[{"code": "AGENT_MODEL_MISSING", "severity": "warning", "message": "No Agent-produced ArchitectureModel was supplied; structured evidence was preserved without semantic inference."}],
    )


class ArchitectureAnalyzer:
    def analyze(self, parsed_document: dict[str, Any]) -> ArchitectureModel:
        raw = dict(parsed_document or {})
        contract = _normalize_agent_contract(raw)
        if contract:
            model = ArchitectureModel.from_dict(contract)
            model.metadata = {**model.metadata, "semantic_source": "agent", "agent_contract": True}
            if not model.source_evidence:
                model.source_evidence = [_as_evidence(item) for item in contract.get("source_evidence", [])]
            return model
        return _structured_fallback(raw)


def analyze(parsed_document: dict[str, Any]) -> ArchitectureModel:
    return ArchitectureAnalyzer().analyze(parsed_document)
