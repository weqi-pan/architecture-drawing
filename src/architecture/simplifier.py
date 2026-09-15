from __future__ import annotations
from src.architecture.model import ArchitectureModel

def simplify(model: ArchitectureModel | dict, *, detail_level: str = "standard", max_nodes: int = 40, max_relations: int = 60) -> ArchitectureModel:
    m=model if isinstance(model, ArchitectureModel) else ArchitectureModel.from_dict(model)
    ordered=sorted(m.nodes, key=lambda n: (n.level != "L1", n.priority != "primary", n.id))
    if detail_level == "overview": ordered=[n for n in ordered if n.level == "L1" or n.priority == "primary"]
    keep={n.id for n in ordered[:max_nodes]}; m.nodes=ordered[:max_nodes]
    m.relations=[r for r in m.relations if r.source in keep and r.target in keep][:max_relations]
    return m
