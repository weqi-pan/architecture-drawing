"""Renderer-independent architecture semantic model.

This module intentionally contains no Draw.io, PowerPoint, or coordinate concepts.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable
import json


@dataclass
class EvidenceRef:
    source: str = ""
    page: int | None = None
    section: str = ""
    paragraph: str = ""
    quote: str = ""
    locator: str = ""

    @classmethod
    def from_value(cls, value: Any) -> "EvidenceRef":
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            return cls(quote=value)
        if not isinstance(value, dict):
            return cls()
        return cls(source=str(value.get("source", value.get("source_file", ""))),
                   page=value.get("page"), section=str(value.get("section", "")),
                   paragraph=str(value.get("paragraph", "")), quote=str(value.get("quote", value.get("text", ""))),
                   locator=str(value.get("locator", value.get("id", ""))))

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v not in (None, "")}


@dataclass
class ArchitectureNode:
    id: str
    title: str
    subtitle: str = ""
    description: str = ""
    type: str = "component"
    domain: str = ""
    layer: str = ""
    level: str = "L2"
    priority: str = "secondary"
    status: str = "current"
    source_evidence: list[EvidenceRef] = field(default_factory=list)
    children: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict[str, Any], *, default_id: str = "node") -> "ArchitectureNode":
        label = str(raw.get("title", raw.get("label", raw.get("name", default_id))))
        return cls(id=str(raw.get("id", default_id)), title=label,
                   subtitle=str(raw.get("subtitle", raw.get("sub_title", ""))),
                   description=str(raw.get("description", raw.get("details", ""))),
                   type=str(raw.get("type", raw.get("role", raw.get("category", "component")))),
                   domain=str(raw.get("domain", raw.get("group", ""))),
                   layer=str(raw.get("layer", raw.get("level_name", ""))),
                   level=str(raw.get("level", "L2")), priority=str(raw.get("priority", raw.get("importance", "secondary"))),
                   status=str(raw.get("status", "current")),
                   source_evidence=[EvidenceRef.from_value(x) for x in raw.get("source_evidence", raw.get("evidence", raw.get("source_refs", [])))],
                   children=[str(x) for x in raw.get("children", [])], metadata=dict(raw.get("metadata", {})))

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["source_evidence"] = [x.to_dict() for x in self.source_evidence]
        return result


@dataclass
class ArchitectureRelation:
    id: str
    source: str
    target: str
    relation_type: str = "association"
    label: str = ""
    confidence: float = 1.0
    explicit: bool = True
    priority: str = "secondary"
    source_evidence: list[EvidenceRef] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict[str, Any], *, default_id: str = "relation") -> "ArchitectureRelation":
        return cls(id=str(raw.get("id", default_id)), source=str(raw.get("source", raw.get("from", ""))),
                   target=str(raw.get("target", raw.get("to", ""))),
                   relation_type=str(raw.get("relation_type", raw.get("type", "association"))),
                   label=str(raw.get("label", "")), confidence=float(raw.get("confidence", 1.0) or 0),
                   explicit=bool(raw.get("explicit", True)), priority=str(raw.get("priority", raw.get("importance", "secondary"))),
                   source_evidence=[EvidenceRef.from_value(x) for x in raw.get("source_evidence", raw.get("evidence", raw.get("source_refs", [])))],
                   metadata=dict(raw.get("metadata", {})))

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["source_evidence"] = [x.to_dict() for x in self.source_evidence]
        return result


@dataclass
class ArchitectureModel:
    project: str = ""
    title: str = "Architecture"
    architecture_type: str = "LAYERED"
    goals: list[str] = field(default_factory=list)
    actors: list[str] = field(default_factory=list)
    layers: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    nodes: list[ArchitectureNode] = field(default_factory=list)
    relations: list[ArchitectureRelation] = field(default_factory=list)
    external_systems: list[str] = field(default_factory=list)
    strategic_messages: list[str] = field(default_factory=list)
    source_evidence: list[EvidenceRef] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    diagnostics: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ArchitectureModel":
        # Accept the existing ArchitectureModel 2.0 contract without making it a new parser.
        nodes: list[ArchitectureNode] = []
        def visit(items: Iterable[dict[str, Any]], parent: str = "") -> None:
            for item in items or []:
                node = ArchitectureNode.from_dict(item, default_id=f"node-{len(nodes)+1}")
                if parent and not node.domain:
                    node.domain = parent
                node.children = [str(x.get("id", x)) if isinstance(x, dict) else str(x) for x in item.get("children", [])]
                nodes.append(node)
                visit([x for x in item.get("children", []) if isinstance(x, dict)], node.id)
        if raw.get("elements"):
            visit(raw.get("elements", []))
        else:
            nodes = [ArchitectureNode.from_dict(x, default_id=f"node-{i+1}") for i, x in enumerate(raw.get("nodes", []))]
        relations = [ArchitectureRelation.from_dict(x, default_id=f"rel-{i+1}") for i, x in enumerate(raw.get("relations", raw.get("edges", [])))]
        return cls(project=str(raw.get("project", raw.get("industry", ""))), title=str(raw.get("title", "Architecture")),
                   architecture_type=str(raw.get("architecture_type", raw.get("type", raw.get("view_type", "LAYERED")))).upper(),
                   goals=[str(x) for x in raw.get("goals", [])], actors=[str(x) for x in raw.get("actors", [])],
                   layers=[str(x) for x in raw.get("layers", [])], domains=[str(x) for x in raw.get("domains", [])], nodes=nodes,
                   relations=relations, external_systems=[str(x) for x in raw.get("external_systems", [])],
                   strategic_messages=[str(x) for x in raw.get("strategic_messages", [])],
                   source_evidence=[EvidenceRef.from_value(x) for x in raw.get("source_evidence", [])], metadata=dict(raw.get("metadata", {})),
                   diagnostics=[dict(x) for x in raw.get("diagnostics", []) if isinstance(x, dict)])

    def validate(self) -> list[str]:
        errors: list[str] = []
        ids = [n.id for n in self.nodes]
        if len(ids) != len(set(ids)): errors.append("node ids must be unique")
        rel_ids = [r.id for r in self.relations]
        if len(rel_ids) != len(set(rel_ids)): errors.append("relation ids must be unique")
        known = set(ids)
        for rel in self.relations:
            if rel.source not in known: errors.append(f"unknown relation source: {rel.source}")
            if rel.target not in known: errors.append(f"unknown relation target: {rel.target}")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return {"project": self.project, "title": self.title, "architecture_type": self.architecture_type,
                "goals": self.goals, "actors": self.actors, "layers": self.layers, "domains": self.domains,
                "nodes": [n.to_dict() for n in self.nodes], "relations": [r.to_dict() for r in self.relations],
                "external_systems": self.external_systems, "strategic_messages": self.strategic_messages,
                "source_evidence": [x.to_dict() for x in self.source_evidence], "metadata": self.metadata, "diagnostics": self.diagnostics}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
