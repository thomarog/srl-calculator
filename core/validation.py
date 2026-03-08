from __future__ import annotations

from .models import ProjectData

TRL_MIN = 1
TRL_MAX = 9
IRL_MIN = 0
IRL_MAX = 9


def validate_project(project: ProjectData) -> None:
    if not project.components:
        raise ValueError("Project must contain at least one component.")

    component_ids = [component.id for component in project.components]
    if len(component_ids) != len(set(component_ids)):
        raise ValueError("Component IDs must be unique.")

    for component in project.components:
        if not (TRL_MIN <= component.trl <= TRL_MAX):
            raise ValueError(
                f"Component '{component.id}' TRL must be in range "
                f"[{TRL_MIN}, {TRL_MAX}], got {component.trl}."
            )

    known_ids = set(component_ids)
    seen_pairs: set[tuple[str, str]] = set()
    for interface in project.interfaces:
        if interface.component_a_id == interface.component_b_id:
            raise ValueError("Interface endpoints must be different components.")

        if interface.component_a_id not in known_ids or interface.component_b_id not in known_ids:
            raise ValueError(
                "Interface references unknown component ID: "
                f"{interface.component_a_id} <-> {interface.component_b_id}."
            )

        if not (IRL_MIN <= interface.irl <= IRL_MAX):
            raise ValueError(
                f"Interface {interface.component_a_id} <-> {interface.component_b_id} IRL "
                f"must be in range [{IRL_MIN}, {IRL_MAX}], got {interface.irl}."
            )

        if interface.planned and interface.irl == 0:
            raise ValueError(
                f"Planned interface {interface.component_a_id} <-> {interface.component_b_id} "
                "must have IRL in [1, 9]."
            )

        if not interface.planned and interface.irl != 0:
            raise ValueError(
                f"Unplanned interface {interface.component_a_id} <-> {interface.component_b_id} "
                "must have IRL=0."
            )

        pair = tuple(sorted((interface.component_a_id, interface.component_b_id)))
        if pair in seen_pairs:
            raise ValueError(
                f"Duplicate interface detected for pair {pair[0]} <-> {pair[1]}."
            )
        seen_pairs.add(pair)

