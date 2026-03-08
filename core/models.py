from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Component:
    id: str
    name: str
    trl: int
    description: str | None = None


@dataclass(frozen=True)
class Interface:
    component_a_id: str
    component_b_id: str
    irl: int
    planned: bool = True
    note: str | None = None


@dataclass(frozen=True)
class ProjectData:
    name: str
    components: list[Component]
    interfaces: list[Interface] = field(default_factory=list)
    revision: str = ""
    project_date: str = ""
    notes: str = ""
    evidence: list[dict[str, Any]] = field(default_factory=list)
    visualization_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ComponentResult:
    component_id: str
    raw_srl: float
    integrations_count: int
    component_srl: float


@dataclass(frozen=True)
class SRLResult:
    component_results: list[ComponentResult]
    composite_srl: float
    srl_level: int
    translation_model: dict[int, float]
    translation_boundaries: dict[int, tuple[float, float]]
