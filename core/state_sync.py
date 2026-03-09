from __future__ import annotations

from .models import Component, Interface


def propagate_component_rename(
    interfaces: list[Interface], old_id: str, new_id: str
) -> tuple[list[Interface], int, int]:
    if old_id == new_id:
        return list(interfaces), 0, 0

    updated: list[Interface] = []
    updated_count = 0
    for interface in interfaces:
        a = new_id if interface.component_a_id == old_id else interface.component_a_id
        b = new_id if interface.component_b_id == old_id else interface.component_b_id
        if a != interface.component_a_id or b != interface.component_b_id:
            updated_count += 1
        updated.append(
            Interface(
                component_a_id=a,
                component_b_id=b,
                planned=interface.planned,
                irl=int(interface.irl),
                note=interface.note,
            )
        )

    deduped: list[Interface] = []
    seen_pairs: set[tuple[str, str]] = set()
    removed_conflicts = 0
    for interface in updated:
        pair = tuple(sorted((interface.component_a_id, interface.component_b_id)))
        if pair[0] == pair[1] or pair in seen_pairs:
            removed_conflicts += 1
            continue
        seen_pairs.add(pair)
        deduped.append(interface)

    return deduped, updated_count, removed_conflicts


def remove_component_and_related_interfaces(
    interfaces: list[Interface], component_id: str
) -> tuple[list[Interface], int]:
    kept = [
        interface
        for interface in interfaces
        if component_id not in {interface.component_a_id, interface.component_b_id}
    ]
    return kept, len(interfaces) - len(kept)


def prune_stale_interfaces(
    interfaces: list[Interface], component_ids: set[str]
) -> tuple[list[Interface], int]:
    kept = [
        interface
        for interface in interfaces
        if interface.component_a_id in component_ids and interface.component_b_id in component_ids
    ]
    return kept, len(interfaces) - len(kept)


def build_irl_matrix(
    components: list[Component], interfaces: list[Interface]
) -> tuple[list[str], list[dict[str, int | str]]]:
    component_ids = [component.id for component in components]
    component_set = set(component_ids)
    matrix = {row: {col: 0 for col in component_ids} for row in component_ids}
    for component_id in component_ids:
        matrix[component_id][component_id] = 9

    for interface in interfaces:
        a, b = tuple(sorted((interface.component_a_id, interface.component_b_id)))
        if a in component_set and b in component_set:
            matrix[a][b] = int(interface.irl)
            matrix[b][a] = int(interface.irl)

    rows: list[dict[str, int | str]] = []
    for row_id in component_ids:
        row: dict[str, int | str] = {"Component": row_id}
        for col_id in component_ids:
            row[col_id] = matrix[row_id][col_id]
        rows.append(row)
    return component_ids, rows


def build_graph_data(
    components: list[Component], interfaces: list[Interface]
) -> tuple[list[str], list[tuple[str, str, int]]]:
    component_ids = [component.id for component in components]
    component_set = set(component_ids)
    edges: list[tuple[str, str, int]] = []
    for interface in interfaces:
        a, b = tuple(sorted((interface.component_a_id, interface.component_b_id)))
        if a in component_set and b in component_set and a != b:
            edges.append((a, b, int(interface.irl)))
    return component_ids, edges
