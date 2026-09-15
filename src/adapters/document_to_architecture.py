"""Adapter from existing parser-shaped results to architecture semantic input."""
from __future__ import annotations
from typing import Any
from src.architecture.model import ArchitectureModel

def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict): return value
    if hasattr(value, "to_dict"): return value.to_dict()
    if hasattr(value, "__dict__"): return dict(value.__dict__)
    raise TypeError("parsed document must be a mapping or expose to_dict()")

def document_to_architecture_input(parsed_document: Any) -> dict[str, Any]:
    raw = _as_dict(parsed_document)
    sections = raw.get("sections", raw.get("headings", [])) or []
    paragraphs = raw.get("paragraphs", raw.get("blocks", raw.get("text", []))) or []
    tables = raw.get("tables", []) or []
    images = raw.get("images", raw.get("attachments", [])) or []
    title = raw.get("document_title", raw.get("title", raw.get("name", "")))
    def text_of(x: Any) -> str:
        if isinstance(x, str): return x
        if isinstance(x, dict): return str(x.get("text", x.get("content", x.get("title", x.get("label", "")))))
        return str(x)
    structured = [{"kind":"section", "text":text_of(x), "source_ref":x.get("source_ref", x.get("id", "")) if isinstance(x,dict) else ""} for x in sections]
    structured += [{"kind":"paragraph", "text":text_of(x), "source_ref":x.get("source_ref", x.get("id", "")) if isinstance(x,dict) else ""} for x in paragraphs]
    result = {"document_title":str(title), "sections":sections, "structured_text":structured, "paragraphs":paragraphs, "tables":tables, "images":images, "source_refs":raw.get("source_refs", raw.get("evidence", [])), "relations":raw.get("relations", raw.get("relationships", raw.get("edges", []))), "goals":raw.get("goals", []), "actors":raw.get("actors", []), "metadata":{"source_format":raw.get("source_format", raw.get("format", "unknown")), **dict(raw.get("metadata", {}))}}
    # Preserve an Agent-produced contract instead of flattening it into document text.
    agent_model = raw.get("architecture_model")
    if not isinstance(agent_model, dict) and ("nodes" in raw or "elements" in raw):
        agent_model = raw
    if agent_model is not None:
        result["architecture_model"] = agent_model
    return result

def architecture_model_to_input(model: ArchitectureModel | dict[str, Any]) -> dict[str, Any]:
    value = model if isinstance(model, ArchitectureModel) else ArchitectureModel.from_dict(model)
    return {"document_title":value.title, "sections":[], "structured_text":[], "paragraphs":[], "tables":[], "images":[], "source_refs":[x.to_dict() for x in value.source_evidence], "architecture_model":value.to_dict()}
