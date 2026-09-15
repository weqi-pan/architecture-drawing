from __future__ import annotations
from src.architecture.model import ArchitectureModel

def select_architecture_type(model: ArchitectureModel | dict) -> str:
    m = model if isinstance(model, ArchitectureModel) else ArchitectureModel.from_dict(model)
    types={n.type for n in m.nodes}; rels=len(m.relations)
    if any(t in types for t in ("algorithm",)) and rels >= 2: return "PIPELINE"
    if len(m.external_systems) >= 2 or any(n.type == "external_system" for n in m.nodes) and rels >= 2: return "HUB_SPOKE"
    domains={n.domain for n in m.nodes if n.domain}
    if len(domains) >= 3: return "DOMAIN_MATRIX"
    if rels and len(m.nodes) >= 4: return "HYBRID"
    return "LAYERED"

def apply_type(model: ArchitectureModel | dict) -> ArchitectureModel:
    m=model if isinstance(model, ArchitectureModel) else ArchitectureModel.from_dict(model)
    m.architecture_type=select_architecture_type(m)
    return m
