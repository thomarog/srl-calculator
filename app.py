from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any
from datetime import date

import streamlit as st

from custom_components.draggable_agraph import (
    Config as AConfig,
    Edge as AEdge,
    Node as ANode,
    agraph_draggable,
)
from core.engine import calculate_srl
from core.interface_store import pair_key, save_interface
from core.io import load_project_data, load_project_data_from_json_text
from core.models import Component, Interface, ProjectData


DEFAULT_PROJECT = Path("data/sample_project.json")
IRL_LEVEL_NOTES = {
    0: "No integration planned.",
    1: "Integration concept identified.",
    2: "Interface requirements partly known / documented.",
    3: "Detailed interface design defined.",
    4: "Functions validated in lab/synthetic environment.",
    5: "Functions validated in relevant environment.",
    6: "End-to-end integration validated in relevant environment.",
    7: "Prototype integration demonstrated in operational/high-fidelity environment.",
    8: "Integration completed and qualified in operational environment.",
    9: "Integration proven in successful operation.",
}


def _load_default_project() -> ProjectData:
    return load_project_data(DEFAULT_PROJECT)


def _empty_project() -> ProjectData:
    return ProjectData(
        name="New SRL Project",
        components=[],
        interfaces=[],
        revision="1",
        project_date=date.today().isoformat(),
        notes="",
        evidence=[],
        visualization_metadata={"node_positions": {}},
    )


def _two_blank_components_project() -> ProjectData:
    return ProjectData(
        name="New SRL Project (2 Components)",
        components=[
            Component(id="C1", name="Component 1", trl=1, description=""),
            Component(id="C2", name="Component 2", trl=1, description=""),
        ],
        interfaces=[],
        revision="1",
        project_date=date.today().isoformat(),
        notes="",
        evidence=[],
        visualization_metadata={"node_positions": {}},
    )


def _load_uploaded_project(uploaded_file) -> tuple[ProjectData | None, str | None]:
    try:
        raw_text = uploaded_file.getvalue().decode("utf-8")
        project = load_project_data_from_json_text(raw_text)
        return project, None
    except UnicodeDecodeError:
        return None, "Invalid file encoding. Please upload a UTF-8 JSON file."
    except json.JSONDecodeError as exc:
        return None, f"Invalid JSON: {exc}"
    except (KeyError, TypeError, ValueError) as exc:
        return None, f"Invalid project data: {exc}"


def _empty_component_row() -> dict[str, object]:
    return {"id": "", "name": "", "description": "", "trl": 1}


def _component_to_row(component: Component) -> dict[str, object]:
    return {
        "id": component.id,
        "name": component.name,
        "description": component.description or "",
        "trl": int(component.trl),
    }


def _build_components_from_rows(
    rows: list[dict[str, object]],
) -> tuple[list[Component], list[str]]:
    errors: list[str] = []
    components: list[Component] = []
    seen_ids: set[str] = set()

    for idx, row in enumerate(rows, start=1):
        component_id = str(row.get("id", "")).strip()
        name = str(row.get("name", "")).strip()
        description = str(row.get("description", "")).strip() or None
        raw_trl = row.get("trl")

        if not component_id:
            errors.append(f"Row {idx}: component ID is required.")
        if not name:
            errors.append(f"Row {idx}: component name is required.")

        try:
            trl = int(raw_trl)
            if isinstance(raw_trl, float) and not raw_trl.is_integer():
                raise ValueError
        except (TypeError, ValueError):
            errors.append(f"Row {idx}: TRL must be an integer in range 1..9.")
            trl = -1

        if trl != -1 and not (1 <= trl <= 9):
            errors.append(f"Row {idx}: TRL must be in range 1..9.")

        if component_id:
            if component_id in seen_ids:
                errors.append(f"Row {idx}: duplicate component ID '{component_id}'.")
            seen_ids.add(component_id)

        if component_id and name and 1 <= trl <= 9:
            components.append(
                Component(
                    id=component_id,
                    name=name,
                    description=description,
                    trl=trl,
                )
            )

    if not rows:
        errors.append("At least one component is required.")

    return components, errors


def _pair_key(component_a_id: str, component_b_id: str) -> tuple[str, str]:
    return pair_key(component_a_id, component_b_id)


def _interface_label(interface: Interface) -> str:
    a, b = _pair_key(interface.component_a_id, interface.component_b_id)
    return f"{a} <-> {b}"


def _interface_to_row(interface: Interface, valid_component_ids: set[str]) -> dict[str, object]:
    a, b = _pair_key(interface.component_a_id, interface.component_b_id)
    endpoints_exist = a in valid_component_ids and b in valid_component_ids
    return {
        "Component A": a,
        "Component B": b,
        "Planned": interface.planned,
        "IRL": interface.irl,
        "Notes": interface.note or "",
        "Endpoints Valid": "Yes" if endpoints_exist else "No",
    }


def _validate_interfaces(
    interfaces: list[Interface], valid_component_ids: set[str]
) -> list[str]:
    errors: list[str] = []
    seen_pairs: set[tuple[str, str]] = set()

    for interface in interfaces:
        a, b = _pair_key(interface.component_a_id, interface.component_b_id)
        if a == b:
            errors.append(f"Invalid self-interface: {a} <-> {b}.")
            continue

        if a not in valid_component_ids or b not in valid_component_ids:
            errors.append(f"Interface endpoints missing: {a} <-> {b}.")

        pair = (a, b)
        if pair in seen_pairs:
            errors.append(f"Duplicate interface pair: {a} <-> {b}.")
        seen_pairs.add(pair)

        if interface.planned and not (1 <= int(interface.irl) <= 9):
            errors.append(f"Planned interface {a} <-> {b} must have IRL in 1..9.")
        if not interface.planned and int(interface.irl) != 0:
            errors.append(f"Not-planned interface {a} <-> {b} must have IRL = 0.")
        if int(interface.irl) < 0 or int(interface.irl) > 9:
            errors.append(f"Interface {a} <-> {b} IRL must be in 0..9.")

    return errors


def _find_inconsistent_interfaces(
    interfaces: list[Interface], component_ids: set[str]
) -> list[str]:
    issues: list[str] = []
    for interface in interfaces:
        if (
            interface.component_a_id not in component_ids
            or interface.component_b_id not in component_ids
        ):
            issues.append(
                f"{interface.component_a_id} <-> {interface.component_b_id} "
                "(references missing component)"
            )
    return issues


def _interface_neighbors(
    interfaces: list[Interface], component_ids: set[str]
) -> dict[str, set[str]]:
    neighbors = {component_id: set() for component_id in component_ids}
    for interface in interfaces:
        a = interface.component_a_id
        b = interface.component_b_id
        if a in component_ids and b in component_ids:
            neighbors[a].add(b)
            neighbors[b].add(a)
    return neighbors


def _interface_pairs(interfaces: list[Interface]) -> set[tuple[str, str]]:
    return {_pair_key(interface.component_a_id, interface.component_b_id) for interface in interfaces}


def _build_consistency_report(
    components: list[Component],
    interfaces: list[Interface],
    original_component_ids: set[str],
    baseline_neighbor_counts: dict[str, int],
) -> tuple[str, list[str], bool]:
    component_ids = {component.id for component in components}
    inconsistencies = _find_inconsistent_interfaces(interfaces, component_ids)
    neighbors = _interface_neighbors(interfaces, component_ids)

    orphan_ids = sorted(
        component_id for component_id in component_ids if len(neighbors[component_id]) == 0
    )
    new_component_ids = sorted(component_ids - original_component_ids)
    new_orphan_ids = sorted(set(orphan_ids) & set(new_component_ids))
    lost_interface_components = sorted(
        component_id
        for component_id in (component_ids & set(baseline_neighbor_counts.keys()))
        if baseline_neighbor_counts.get(component_id, 0) > 0 and len(neighbors[component_id]) == 0
    )

    messages: list[str] = []
    if inconsistencies:
        messages.append("Invalid interface endpoints detected:")
        for issue in inconsistencies[:10]:
            pair_text = issue.replace(" (references missing component)", "")
            messages.append(f"- Interface {pair_text} references missing component(s).")
    if orphan_ids:
        for component_id in orphan_ids:
            messages.append(f"- Component {component_id} has no interfaces to other components.")
    if lost_interface_components:
        for component_id in lost_interface_components:
            messages.append(f"- Component {component_id} became orphaned after interface changes.")
    if new_component_ids:
        messages.append(f"New components since load: {', '.join(new_component_ids)}.")
    if new_orphan_ids:
        for component_id in new_orphan_ids:
            messages.append(f"- Newly added component {component_id} has no interfaces yet.")

    if inconsistencies:
        status = "Interface Consistency / Completeness (Current Architecture): INVALID"
        can_recalculate = False
    elif orphan_ids:
        status = "Interface Consistency / Completeness (Current Architecture): INCOMPLETE"
        can_recalculate = False
    else:
        status = "Interface Consistency / Completeness (Current Architecture): VALID"
        can_recalculate = True

    if not can_recalculate:
        messages.append(
            "Action: Add at least one planned interface (IRL 1..9) for each component "
            "that should participate in SRL, and ensure all interface endpoints exist."
        )

    return status, messages, can_recalculate


def _build_baseline_diff_messages(
    components: list[Component],
    interfaces: list[Interface],
    baseline_interface_pairs: set[tuple[str, str]],
) -> list[str]:
    component_ids = {component.id for component in components}
    current_pairs = _interface_pairs(interfaces)
    comparable_baseline_pairs = {
        pair
        for pair in baseline_interface_pairs
        if pair[0] in component_ids and pair[1] in component_ids
    }

    removed_pairs = sorted(comparable_baseline_pairs - current_pairs)
    added_pairs = sorted(current_pairs - comparable_baseline_pairs)

    messages: list[str] = []
    for a, b in removed_pairs:
        messages.append(f"- Removed interface: {a} <-> {b}")
    for a, b in added_pairs:
        messages.append(f"- Added interface: {a} <-> {b}")

    if not messages:
        messages.append("No interface-pair differences from the loaded baseline.")

    return messages


def _evidence_text_to_items(text: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            items.append({"text": stripped})
    return items


def _evidence_items_to_text(items: list[dict[str, Any]]) -> str:
    texts: list[str] = []
    for item in items:
        if isinstance(item, dict):
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                texts.append(text.strip())
    return "\n".join(texts)


def _project_health_status(
    consistency_status: str,
    component_errors: list[str],
    interface_errors: list[str],
) -> str:
    if component_errors or interface_errors or consistency_status.endswith("INVALID"):
        return "INVALID"
    if consistency_status.endswith("INCOMPLETE"):
        return "INCOMPLETE"
    return "VALID"


def _component_map(components: list[Component]) -> dict[str, Component]:
    return {component.id: component for component in components}


def _build_irl_matrix_view(
    components: list[Component], interfaces: list[Interface]
) -> tuple[list[str], list[dict[str, Any]]]:
    component_ids = [component.id for component in components]
    component_set = set(component_ids)
    matrix: dict[str, dict[str, int]] = {
        row_id: {col_id: 0 for col_id in component_ids} for row_id in component_ids
    }
    for component_id in component_ids:
        matrix[component_id][component_id] = 9

    for interface in interfaces:
        a, b = _pair_key(interface.component_a_id, interface.component_b_id)
        if a in component_set and b in component_set:
            matrix[a][b] = int(interface.irl)
            matrix[b][a] = int(interface.irl)

    rows: list[dict[str, Any]] = []
    for row_id in component_ids:
        row: dict[str, Any] = {"Component": row_id}
        for col_id in component_ids:
            row[col_id] = matrix[row_id][col_id]
        rows.append(row)

    return component_ids, rows


def _normalize_node_positions(
    node_positions: dict[str, dict[str, float]],
    component_ids: set[str],
    target_width: float = 10.0,
    target_height: float = 5.0,
) -> dict[str, tuple[float, float]]:
    raw_points: dict[str, tuple[float, float]] = {}
    for component_id in component_ids:
        pos = node_positions.get(component_id)
        if not isinstance(pos, dict):
            continue
        x = pos.get("x")
        y = pos.get("y")
        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
            raw_points[component_id] = (float(x), float(y))

    if not raw_points:
        return {}

    xs = [point[0] for point in raw_points.values()]
    ys = [point[1] for point in raw_points.values()]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = max(max_x - min_x, 1e-9)
    span_y = max(max_y - min_y, 1e-9)

    normalized: dict[str, tuple[float, float]] = {}
    for component_id, (x, y) in raw_points.items():
        nx = ((x - min_x) / span_x) * target_width
        ny = ((y - min_y) / span_y) * target_height
        normalized[component_id] = (nx, ny)

    return normalized


def _connected_component_groups(
    component_ids: list[str], interfaces: list[Interface]
) -> list[list[str]]:
    component_set = set(component_ids)
    adjacency: dict[str, set[str]] = {component_id: set() for component_id in component_ids}
    for interface in interfaces:
        a, b = _pair_key(interface.component_a_id, interface.component_b_id)
        if a in component_set and b in component_set and a != b:
            adjacency[a].add(b)
            adjacency[b].add(a)

    visited: set[str] = set()
    groups: list[list[str]] = []
    for component_id in component_ids:
        if component_id in visited:
            continue
        stack = [component_id]
        group: list[str] = []
        visited.add(component_id)
        while stack:
            current = stack.pop()
            group.append(current)
            for neighbor in sorted(adjacency[current]):
                if neighbor not in visited:
                    visited.add(neighbor)
                    stack.append(neighbor)
        groups.append(sorted(group))
    return groups


def _auto_layout_positions(
    component_ids: list[str], interfaces: list[Interface]
) -> dict[str, tuple[float, float]]:
    groups = _connected_component_groups(component_ids, interfaces)
    if not groups:
        return {}

    # Place each disconnected group into a compact grid cell.
    group_count = len(groups)
    cols = max(1, int(group_count ** 0.5))
    if cols * cols < group_count:
        cols += 1
    cell_w = 4.0
    cell_h = 3.2

    positioned: dict[str, tuple[float, float]] = {}
    for idx, group in enumerate(groups):
        col = idx % cols
        row = idx // cols
        base_x = col * cell_w
        base_y = -row * cell_h

        n = len(group)
        if n == 1:
            positioned[group[0]] = (base_x, base_y)
            continue
        if n == 2:
            positioned[group[0]] = (base_x - 0.7, base_y)
            positioned[group[1]] = (base_x + 0.7, base_y)
            continue

        radius = max(0.8, 0.28 * n)
        for i, component_id in enumerate(group):
            angle = (2.0 * 3.141592653589793 * i) / n
            x = base_x + radius * math.cos(angle)
            y = base_y + radius * math.sin(angle)
            positioned[component_id] = (x, y)

    return positioned


def _normalize_tuple_positions(
    positions: dict[str, tuple[float, float]],
    target_width: float = 10.0,
    target_height: float = 5.0,
) -> dict[str, tuple[float, float]]:
    if not positions:
        return {}
    xs = [point[0] for point in positions.values()]
    ys = [point[1] for point in positions.values()]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = max(max_x - min_x, 1e-9)
    span_y = max(max_y - min_y, 1e-9)

    normalized: dict[str, tuple[float, float]] = {}
    for component_id, (x, y) in positions.items():
        nx = ((x - min_x) / span_x) * target_width
        ny = ((y - min_y) / span_y) * target_height
        normalized[component_id] = (nx, ny)
    return normalized


def _extract_saved_positions(
    node_positions: dict[str, dict[str, float]] | None,
    component_ids: set[str],
) -> dict[str, tuple[float, float]]:
    if not node_positions:
        return {}
    extracted: dict[str, tuple[float, float]] = {}
    for component_id in component_ids:
        pos = node_positions.get(component_id)
        if not isinstance(pos, dict):
            continue
        x = pos.get("x")
        y = pos.get("y")
        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
            extracted[component_id] = (float(x), float(y))
    return extracted


def _upsert_node_position(component_id: str, x: float, y: float) -> None:
    visualization = st.session_state.get("visualization_metadata", {})
    if not isinstance(visualization, dict):
        visualization = {}
    node_positions = visualization.get("node_positions", {})
    if not isinstance(node_positions, dict):
        node_positions = {}
    node_positions[component_id] = {"x": float(x), "y": float(y)}
    visualization["node_positions"] = node_positions
    st.session_state.visualization_metadata = visualization


def _reset_node_positions() -> None:
    visualization = st.session_state.get("visualization_metadata", {})
    if not isinstance(visualization, dict):
        visualization = {}
    visualization["node_positions"] = {}
    st.session_state.visualization_metadata = visualization
    st.session_state.last_drag_signature = None


def _apply_pending_drag_event(component_ids: set[str]) -> bool:
    pending = st.session_state.get("architecture_drag_graph")
    if not isinstance(pending, dict) or pending.get("type") != "dragEnd":
        return False

    positions = pending.get("positions")
    if not isinstance(positions, dict):
        return False

    signature = json.dumps(positions, sort_keys=True)
    if signature == st.session_state.get("last_drag_signature"):
        return False

    updated_any = False
    for component_id, pos in positions.items():
        if component_id not in component_ids or not isinstance(pos, dict):
            continue
        x = pos.get("x")
        y = pos.get("y")
        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
            _upsert_node_position(component_id, float(x), float(y))
            updated_any = True

    st.session_state.last_drag_signature = signature
    return updated_any


def _compute_graph_positions(
    components: list[Component],
    interfaces: list[Interface],
    node_positions: dict[str, dict[str, float]] | None = None,
) -> tuple[dict[str, tuple[float, float]], bool]:
    component_ids = {component.id for component in components}
    node_count = len(components)

    auto_positions = _auto_layout_positions(
        [component.id for component in components], interfaces
    )
    saved_positions = _extract_saved_positions(node_positions, component_ids)

    # Manual mode: if any saved positions exist, use them directly (no normalization)
    # to avoid re-scaling and node jumps after drag.
    if saved_positions:
        manual_positions = dict(saved_positions)
        for component in components:
            if component.id not in manual_positions:
                manual_positions[component.id] = auto_positions.get(component.id, (0.0, 0.0))
        return manual_positions, True

    if node_count <= 3:
        target_w, target_h = 6.0, 2.2
    elif node_count <= 15:
        target_w, target_h = 10.0, 5.5
    else:
        target_w, target_h = 12.0, 7.0

    auto_bounded = _normalize_tuple_positions(
        auto_positions, target_width=target_w, target_height=target_h
    )
    return auto_bounded, False


def _build_graphviz_dot(
    components: list[Component],
    interfaces: list[Interface],
    node_positions: dict[str, dict[str, float]] | None = None,
) -> str:
    component_ids = {component.id for component in components}
    neighbors = _interface_neighbors(interfaces, component_ids)
    orphan_ids = {component_id for component_id, linked in neighbors.items() if not linked}
    node_count = len(components)

    auto_positions = _auto_layout_positions([component.id for component in components], interfaces)
    saved_positions = _extract_saved_positions(node_positions, component_ids)
    merged_positions = dict(auto_positions)
    merged_positions.update(saved_positions)

    if node_count <= 3:
        target_w, target_h = 6.0, 2.2
    elif node_count <= 15:
        target_w, target_h = 10.0, 5.5
    else:
        target_w, target_h = 12.0, 7.0

    bounded_positions = _normalize_tuple_positions(
        merged_positions, target_width=target_w, target_height=target_h
    )
    use_positions = bool(bounded_positions)

    if node_count <= 3:
        graph_size = "8,2.4"
        ranksep = "0.4"
        nodesep = "0.35"
    elif node_count <= 15:
        graph_size = "10.5,5.8"
        ranksep = "0.75"
        nodesep = "0.45"
    else:
        graph_size = "12,7.0"
        ranksep = "1.0"
        nodesep = "0.6"

    graph_attrs = (
        f'  graph [overlap=false, splines=true, ranksep="{ranksep}", '
        f'nodesep="{nodesep}", size="{graph_size}", ratio="compress", pad="0.2"'
    )
    if use_positions:
        graph_attrs += ', layout="neato", mode="ipsep"'
    else:
        graph_attrs += ', layout="dot", rankdir="LR"'
    graph_attrs += "];"

    lines = [
        "graph Architecture {",
        graph_attrs,
        '  node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=10];',
        '  edge [fontname="Helvetica", fontsize=9];',
    ]

    for component in components:
        safe_name = component.name.replace('"', "'")
        label = (
            f"{component.id}\\n"
            f"{safe_name}\\n"
            f"TRL={component.trl}"
        )
        if component.id in orphan_ids:
            fillcolor = "#facc15"  # orphan/incomplete
        elif component.trl <= 2:
            fillcolor = "#ef4444"  # very low TRL
        else:
            fillcolor = "#22c55e"  # normal/connected
        node_extra = ""
        if use_positions and component.id in bounded_positions:
            x, y = bounded_positions[component.id]
            node_extra = f', pos="{x},{y}!", pin=true'
        lines.append(
            f'  "{component.id}" [label="{label}", fillcolor="{fillcolor}"{node_extra}];'
        )

    seen_pairs: set[tuple[str, str]] = set()
    for interface in interfaces:
        a, b = _pair_key(interface.component_a_id, interface.component_b_id)
        if a not in component_ids or b not in component_ids:
            continue
        pair = (a, b)
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)

        irl = int(interface.irl)
        planned = bool(interface.planned)
        if not planned or irl == 0:
            color = "#9ca3af"
            style = "dashed"
        elif irl <= 2:
            color = "#ef4444"  # very low IRL cue
            style = "solid"
        else:
            color = "#16a34a"
            style = "solid"

        edge_label = f"IRL={irl}"
        lines.append(
            f'  "{a}" -- "{b}" [label="{edge_label}", color="{color}", style="{style}"];'
        )

    lines.append("}")
    return "\n".join(lines)


def _render_architecture_view(
    components: list[Component], interfaces: list[Interface]
) -> None:
    component_ids = {component.id for component in components}
    _apply_pending_drag_event(component_ids)

    st.header("Architecture View")
    st.caption("Read-only visualization of the current architecture in session state.")

    st.subheader("Interface Matrix (IRL)")
    _, matrix_rows = _build_irl_matrix_view(components, interfaces)
    st.dataframe(matrix_rows, use_container_width=True, hide_index=True)
    st.caption(
        "Diagonal self-cells are fixed to 9. Non-diagonal missing interfaces are shown as 0."
    )

    st.subheader("Network View")
    visualization_metadata = st.session_state.get("visualization_metadata", {})
    node_positions = visualization_metadata.get("node_positions", {})
    graph_positions, manual_layout_mode = _compute_graph_positions(
        components, interfaces, node_positions
    )
    neighbors = _interface_neighbors(interfaces, component_ids)
    orphan_ids = {component_id for component_id, linked in neighbors.items() if not linked}

    nodes: list[ANode] = []
    for component in components:
        x, y = graph_positions.get(component.id, (0.0, 0.0))
        if manual_layout_mode:
            render_x = x
            render_y = y
        else:
            render_x = x * 100
            render_y = y * 100
        if component.id in orphan_ids:
            node_color = {
                "background": "#a16207",
                "border": "#fbbf24",
                "highlight": {"background": "#b45309", "border": "#fde68a"},
                "hover": {"background": "#b45309", "border": "#fde68a"},
            }
        elif component.trl <= 2:
            node_color = {
                "background": "#991b1b",
                "border": "#ef4444",
                "highlight": {"background": "#b91c1c", "border": "#f87171"},
                "hover": {"background": "#b91c1c", "border": "#f87171"},
            }
        else:
            node_color = {
                "background": "#166534",
                "border": "#22c55e",
                "highlight": {"background": "#15803d", "border": "#4ade80"},
                "hover": {"background": "#15803d", "border": "#4ade80"},
            }
        nodes.append(
            ANode(
                id=component.id,
                label=f"{component.id}\n{component.name}\nTRL={component.trl}",
                shape="box",
                color=node_color,
                x=render_x,
                y=render_y,
                physics=False,
                fixed=False,
                borderWidth=2,
                borderWidthSelected=3,
                font={"size": 14, "color": "#f8fafc", "face": "Inter"},
            )
        )

    seen_pairs: set[tuple[str, str]] = set()
    edges: list[AEdge] = []
    for interface in interfaces:
        a, b = _pair_key(interface.component_a_id, interface.component_b_id)
        if a not in component_ids or b not in component_ids:
            continue
        if (a, b) in seen_pairs:
            continue
        seen_pairs.add((a, b))
        irl = int(interface.irl)
        planned = bool(interface.planned)
        if not planned or irl == 0:
            color = "#9ca3af"
            dashes = True
        elif irl <= 2:
            color = "#ef4444"
            dashes = False
        else:
            color = "#16a34a"
            dashes = False
        edges.append(
            AEdge(
                source=a,
                target=b,
                label=f"IRL={irl}",
                color=color,
                dashes=dashes,
                width=2,
                font={
                    "color": "#f8fafc",
                    "size": 13,
                    "strokeWidth": 3,
                    "strokeColor": "#111827",
                    "background": "rgba(15, 23, 42, 0.75)",
                },
            )
        )

    graph_config = AConfig(
        width=1100,
        height=520,
        directed=False,
        physics=False,
        hierarchical=False,
        fit=True,
        stabilization=False,
        layout={"improvedLayout": False},
        interaction={
            "dragNodes": True,
            "dragView": True,
            "zoomView": True,
            "selectConnectedEdges": False,
        },
    )
    graph_container = st.container()
    with graph_container:
        _ = agraph_draggable(
            nodes=nodes,
            edges=edges,
            config=graph_config,
            key="architecture_drag_graph",
        )
    st.caption(
        "Color key: green=normal/connected, yellow=orphan/incomplete, "
        "red=very low readiness (TRL<=2 or IRL<=2), gray dashed=not planned (IRL 0)."
    )
    if manual_layout_mode:
        st.caption("Layout mode: manual (saved node positions; auto-layout disabled).")
    else:
        st.caption("Layout mode: automatic (no saved node positions yet).")

    st.subheader("Layout Editor")
    st.caption(
        "Drag nodes directly in the network view to position them. Layout is saved under "
        "`visualization.node_positions`."
    )
    if st.button("Reset Layout", type="secondary"):
        _reset_node_positions()
        st.session_state.action_notice = "Layout reset to automatic positioning."
        st.rerun()

    saved_positions = _extract_saved_positions(
        st.session_state.get("visualization_metadata", {}).get("node_positions", {}),
        {component.id for component in components},
    )
    saved_rows = [
        {"Component": component_id, "x": round(pos[0], 2), "y": round(pos[1], 2)}
        for component_id, pos in sorted(saved_positions.items())
    ]
    st.caption("Saved manual positions")
    if saved_rows:
        st.dataframe(saved_rows, use_container_width=True, hide_index=True)
    else:
        st.caption("No manual positions saved. Auto-layout is active.")


def _suggest_irl_from_answers(answers: dict[str, bool]) -> tuple[int, str, str]:
    if not answers["intended"]:
        return (
            0,
            "No interface is intended between these components.",
            "If integration becomes intended, document a high-level integration concept (IRL 1).",
        )

    if answers["proven_operation"]:
        level = 9
    elif answers["qualified_operational"]:
        level = 8
    elif answers["operational_demo"]:
        level = 7
    elif answers["e2e_validated"]:
        level = 6
    elif answers["relevant_tested"]:
        level = 5
    elif answers["lab_tested"]:
        level = 4
    elif answers["detailed_design"]:
        level = 3
    elif answers["interface_points"] and answers["io_documented"]:
        level = 2
    elif answers["concept_identified"]:
        level = 1
    else:
        level = 0

    explanation = IRL_LEVEL_NOTES[level]
    if level < 9:
        next_hint = f"Typical next step for IRL {level + 1}: {IRL_LEVEL_NOTES[level + 1]}"
    else:
        next_hint = "Highest IRL reached for this interface."
    return level, explanation, next_hint


def _project_json_text(
    name: str,
    revision: str,
    project_date: str,
    notes: str,
    components: list[Component],
    interfaces: list[Interface],
    evidence: list[dict[str, Any]],
    visualization_metadata: dict[str, Any],
) -> str:
    payload = {
        "name": name,
        "metadata": {
            "name": name,
            "revision": revision,
            "date": project_date,
            "notes": notes,
        },
        "components": [
            {
                "id": component.id,
                "name": component.name,
                "description": component.description,
                "trl": component.trl,
            }
            for component in components
        ],
        "interfaces": [
            {
                "component_a_id": interface.component_a_id,
                "component_b_id": interface.component_b_id,
                "irl": interface.irl,
                "planned": interface.planned,
                "note": interface.note,
            }
            for interface in interfaces
        ],
        "evidence": evidence,
        "visualization": visualization_metadata or {"node_positions": {}},
    }
    return json.dumps(payload, indent=2)


def _set_project_state(project: ProjectData, source_label: str) -> None:
    st.session_state.project_name = project.name
    st.session_state.project_revision = project.revision or "1"
    st.session_state.project_date = project.project_date or date.today().isoformat()
    st.session_state.project_notes = project.notes or ""
    st.session_state.project_evidence = project.evidence or []
    st.session_state.component_rows = [_component_to_row(c) for c in project.components]
    st.session_state.interfaces = project.interfaces
    st.session_state.original_component_ids = {component.id for component in project.components}
    baseline_neighbors = _interface_neighbors(
        project.interfaces, {component.id for component in project.components}
    )
    st.session_state.baseline_neighbor_counts = {
        component_id: len(neighbors) for component_id, neighbors in baseline_neighbors.items()
    }
    st.session_state.baseline_interface_pairs = _interface_pairs(project.interfaces)
    st.session_state.visualization_metadata = project.visualization_metadata or {
        "node_positions": {}
    }
    st.session_state.selected_component_id = (
        project.components[0].id if project.components else None
    )
    st.session_state.selected_interface_label = "(new interface)"
    st.session_state.source_label = source_label
    st.session_state.last_result = None
    st.session_state.last_drag_signature = None
    st.session_state.project_loaded = True


def _render_components_editor() -> tuple[list[Component], list[str]]:
    st.header("Components Editor")
    st.caption("Components are editable here.")

    current_rows: list[dict[str, object]] = st.session_state.get("component_rows", [])

    st.subheader("Current Components")
    st.dataframe(current_rows, use_container_width=True, hide_index=True)

    add_col, edit_col = st.columns(2)

    with add_col:
        st.markdown("**Add Component**")
        with st.form("add_component_form", clear_on_submit=True):
            new_id = st.text_input("ID")
            new_name = st.text_input("Name")
            new_description = st.text_input("Description")
            new_trl = st.number_input("TRL", min_value=1, max_value=9, value=1, step=1)
            add_submitted = st.form_submit_button("Add Component")

        if add_submitted:
            new_row = {
                "id": new_id.strip(),
                "name": new_name.strip(),
                "description": new_description.strip(),
                "trl": int(new_trl),
            }
            st.session_state.component_rows = current_rows + [new_row]
            if new_row["id"]:
                st.session_state.selected_component_id = new_row["id"]
            st.session_state.last_result = None
            st.rerun()

    with edit_col:
        st.markdown("**Edit / Delete Component**")
        row_ids = [str(row.get("id", "")).strip() for row in current_rows if str(row.get("id", "")).strip()]
        if not row_ids:
            st.info("No components available yet.")
        else:
            selected = st.selectbox(
                "Select component",
                options=row_ids,
                index=row_ids.index(st.session_state.selected_component_id)
                if st.session_state.get("selected_component_id") in row_ids
                else 0,
            )
            st.session_state.selected_component_id = selected
            selected_idx = row_ids.index(selected)
            selected_row = current_rows[selected_idx]

            with st.form("edit_component_form"):
                edit_id = st.text_input("ID", value=str(selected_row.get("id", "")))
                edit_name = st.text_input("Name", value=str(selected_row.get("name", "")))
                edit_description = st.text_input(
                    "Description", value=str(selected_row.get("description", ""))
                )
                current_trl = selected_row.get("trl", 1)
                try:
                    current_trl_int = int(current_trl)
                except (TypeError, ValueError):
                    current_trl_int = 1
                edit_trl = st.number_input(
                    "TRL", min_value=1, max_value=9, value=current_trl_int, step=1
                )
                save_submitted = st.form_submit_button("Save Component")

            if save_submitted:
                updated_row = {
                    "id": edit_id.strip(),
                    "name": edit_name.strip(),
                    "description": edit_description.strip(),
                    "trl": int(edit_trl),
                }
                rows_copy = list(current_rows)
                rows_copy[selected_idx] = updated_row
                st.session_state.component_rows = rows_copy
                st.session_state.selected_component_id = updated_row["id"] or None
                st.session_state.last_result = None
                st.rerun()

            if st.button("Delete Selected Component", type="secondary"):
                rows_copy = list(current_rows)
                deleted_id = rows_copy[selected_idx].get("id")
                del rows_copy[selected_idx]
                st.session_state.component_rows = rows_copy
                remaining_ids = [str(row.get("id", "")).strip() for row in rows_copy if str(row.get("id", "")).strip()]
                st.session_state.selected_component_id = remaining_ids[0] if remaining_ids else None
                st.session_state.last_result = None
                st.session_state.action_notice = f"Deleted component: {deleted_id}"
                st.rerun()

    components, component_errors = _build_components_from_rows(
        st.session_state.get("component_rows", [])
    )
    return components, component_errors


def _render_interfaces_editor(valid_component_ids: list[str]) -> list[str]:
    st.header("Interfaces Editor")
    st.caption("Define undirected interfaces and IRL values between components.")

    interfaces: list[Interface] = st.session_state.get("interfaces", [])
    component_id_set = set(valid_component_ids)
    interface_rows = [_interface_to_row(interface, component_id_set) for interface in interfaces]

    st.subheader("Current Interfaces")
    st.dataframe(interface_rows, use_container_width=True, hide_index=True)

    if len(valid_component_ids) < 2:
        st.info("At least two valid components are required before editing interfaces.")
        return _validate_interfaces(interfaces, component_id_set)

    labels = [_interface_label(interface) for interface in interfaces]
    selection_options = ["(new interface)"] + labels
    stored_label = st.session_state.get("selected_interface_label", "(new interface)")
    selection_index = (
        selection_options.index(stored_label) if stored_label in selection_options else 0
    )
    selected_label = st.selectbox(
        "Select interface to edit",
        options=selection_options,
        index=selection_index,
    )
    st.session_state.selected_interface_label = selected_label

    selected_interface: Interface | None = None
    if selected_label != "(new interface)":
        for interface in interfaces:
            if _interface_label(interface) == selected_label:
                selected_interface = interface
                break

    default_a = valid_component_ids[0]
    default_b = valid_component_ids[1]
    default_planned = True
    default_irl = 1
    default_note = ""
    if selected_interface is not None:
        sel_a, sel_b = _pair_key(selected_interface.component_a_id, selected_interface.component_b_id)
        default_a = sel_a if sel_a in valid_component_ids else valid_component_ids[0]
        default_b = sel_b if sel_b in valid_component_ids else valid_component_ids[1]
        default_planned = selected_interface.planned
        default_irl = int(selected_interface.irl)
        default_note = selected_interface.note or ""

    with st.form("interface_form"):
        st.markdown("**Add / Edit Interface**")
        component_a = st.selectbox(
            "Component A",
            options=valid_component_ids,
            index=valid_component_ids.index(default_a),
        )
        component_b = st.selectbox(
            "Component B",
            options=valid_component_ids,
            index=valid_component_ids.index(default_b),
        )
        planned = st.checkbox("Planned", value=default_planned)
        irl = st.number_input("IRL", min_value=0, max_value=9, value=default_irl, step=1)
        note = st.text_area("Notes / Evidence", value=default_note)
        save_interface_clicked = st.form_submit_button("Save Interface")

    with st.expander("IRL Guidance Assistant (optional)", expanded=False):
        st.caption(
            f"Guidance for interface: {component_a} <-> {component_b}. "
            "This is advisory only; you can still set IRL manually."
        )
        st.markdown(
            "IRL quick reference: "
            + " | ".join([f"{level}: {text}" for level, text in IRL_LEVEL_NOTES.items()])
        )

        key_suffix = f"{component_a}_{component_b}_{selected_label}".replace(" ", "_")
        answers = {
            "intended": st.checkbox(
                "Is an interface actually intended between these components?",
                value=(default_planned or selected_interface is not None),
                key=f"guide_intended_{key_suffix}",
            ),
            "concept_identified": st.checkbox(
                "Is an integration concept identified?",
                key=f"guide_concept_{key_suffix}",
            ),
            "interface_points": st.checkbox(
                "Are interface points defined?",
                key=f"guide_points_{key_suffix}",
            ),
            "io_documented": st.checkbox(
                "Are inputs/outputs documented?",
                key=f"guide_io_{key_suffix}",
            ),
            "detailed_design": st.checkbox(
                "Is detailed interface design complete?",
                key=f"guide_design_{key_suffix}",
            ),
            "lab_tested": st.checkbox(
                "Has integration been tested in lab/synthetic environment?",
                key=f"guide_lab_{key_suffix}",
            ),
            "relevant_tested": st.checkbox(
                "Has integration been tested in relevant environment?",
                key=f"guide_relevant_{key_suffix}",
            ),
            "e2e_validated": st.checkbox(
                "Has end-to-end integration been validated?",
                key=f"guide_e2e_{key_suffix}",
            ),
            "operational_demo": st.checkbox(
                "Has integration been demonstrated in operational/high-fidelity conditions?",
                key=f"guide_demo_{key_suffix}",
            ),
            "qualified_operational": st.checkbox(
                "Has integration been qualified in operational use?",
                key=f"guide_qualified_{key_suffix}",
            ),
            "proven_operation": st.checkbox(
                "Has integration been proven in successful operation?",
                key=f"guide_proven_{key_suffix}",
            ),
        }

        suggested_irl, explanation, next_hint = _suggest_irl_from_answers(answers)
        st.info(f"Suggested IRL: {suggested_irl}")
        st.write(f"Why: {explanation}")
        st.write(next_hint)

    if save_interface_clicked:
        a, b = _pair_key(component_a, component_b)
        validation_errors: list[str] = []
        if a == b:
            validation_errors.append("Component A and Component B cannot be the same.")
        if planned and not (1 <= int(irl) <= 9):
            validation_errors.append("Planned interface requires IRL in 1..9.")
        if not planned and int(irl) != 0:
            validation_errors.append("Not-planned interface requires IRL = 0.")

        old_pair = _pair_key(selected_interface.component_a_id, selected_interface.component_b_id) if selected_interface else None
        existing_pairs = {_pair_key(interface.component_a_id, interface.component_b_id) for interface in interfaces}
        if (a, b) in existing_pairs and (old_pair is None or (a, b) != old_pair):
            validation_errors.append(f"Duplicate interface pair not allowed: {a} <-> {b}.")

        if validation_errors:
            for message in validation_errors:
                st.error(message)
        else:
            updated_interface = Interface(
                component_a_id=a,
                component_b_id=b,
                planned=planned,
                irl=int(irl),
                note=note.strip() or None,
            )
            new_interfaces = save_interface(
                interfaces=interfaces,
                updated_interface=updated_interface,
                original_pair=old_pair,
            )

            st.session_state.interfaces = new_interfaces
            st.session_state.selected_interface_label = _interface_label(updated_interface)
            st.session_state.last_result = None
            st.rerun()

    if selected_interface is not None and st.button("Delete Selected Interface", type="secondary"):
        selected_pair = _pair_key(selected_interface.component_a_id, selected_interface.component_b_id)
        kept = [
            interface
            for interface in interfaces
            if _pair_key(interface.component_a_id, interface.component_b_id) != selected_pair
        ]
        st.session_state.interfaces = kept
        st.session_state.selected_interface_label = "(new interface)"
        st.session_state.last_result = None
        st.session_state.action_notice = f"Deleted interface: {selected_label}"
        st.rerun()

    return _validate_interfaces(st.session_state.get("interfaces", []), component_id_set)


def main() -> None:
    st.set_page_config(page_title="SRL Calculator", layout="wide")
    st.title("SRL Calculator")
    st.caption("Minimal SRL GUI with editable components/interfaces and architecture views.")

    if "project_loaded" not in st.session_state:
        st.session_state.project_loaded = False

    if not st.session_state.project_loaded:
        st.header("Start Project")
        st.caption("Choose how you want to begin. Sample project is optional.")
        start_col_1, start_col_2, start_col_3 = st.columns(3)
        with start_col_1:
            if st.button("Start Empty Project"):
                _set_project_state(_empty_project(), "Started empty project")
                st.rerun()
        with start_col_2:
            if st.button("Start With 2 Blank Components"):
                _set_project_state(
                    _two_blank_components_project(),
                    "Started with 2 blank components",
                )
                st.rerun()
        with start_col_3:
            if st.button("Load Sample Project"):
                try:
                    default_project = _load_default_project()
                    _set_project_state(
                        default_project, f"Loaded sample: {DEFAULT_PROJECT.as_posix()}"
                    )
                    st.rerun()
                except FileNotFoundError:
                    st.error(f"Sample project file not found: {DEFAULT_PROJECT.as_posix()}")
                except json.JSONDecodeError as exc:
                    st.error(f"Sample JSON is invalid: {exc}")
                except (KeyError, TypeError, ValueError) as exc:
                    st.error(f"Sample project data is invalid: {exc}")

        startup_upload = st.file_uploader(
            "Or upload an existing project JSON", type=["json"], key="startup_uploader"
        )
        if startup_upload is not None and st.button("Load Uploaded Project"):
            project, load_error = _load_uploaded_project(startup_upload)
            if load_error:
                st.error(load_error)
            else:
                _set_project_state(project, f"Uploaded file: {startup_upload.name}")
                st.rerun()
        st.stop()

    if st.session_state.get("action_notice"):
        st.success(st.session_state.action_notice)
        st.session_state.action_notice = None

    summary_placeholder = st.empty()

    st.header("Project Workflow")
    action_col_1, action_col_2, action_col_3, action_col_4 = st.columns(4)
    with action_col_1:
        if st.button("New Empty Project"):
            _set_project_state(_empty_project(), "Started empty project")
            st.rerun()
    with action_col_2:
        if st.button("New 2-Component Starter"):
            _set_project_state(_two_blank_components_project(), "Started with 2 blank components")
            st.rerun()
    with action_col_3:
        if st.button("Load Sample Project"):
            try:
                default_project = _load_default_project()
                _set_project_state(default_project, f"Loaded sample: {DEFAULT_PROJECT.as_posix()}")
                st.rerun()
            except FileNotFoundError:
                st.error(f"Sample project file not found: {DEFAULT_PROJECT.as_posix()}")
            except json.JSONDecodeError as exc:
                st.error(f"Sample JSON is invalid: {exc}")
            except (KeyError, TypeError, ValueError) as exc:
                st.error(f"Sample project data is invalid: {exc}")
    with action_col_4:
        uploaded_file = st.file_uploader(
            "Upload project JSON", type=["json"], key="project_upload_runtime"
        )
        if uploaded_file is not None and st.button("Load Uploaded JSON"):
            project, load_error = _load_uploaded_project(uploaded_file)
            if load_error:
                st.error(load_error)
            else:
                _set_project_state(project, f"Uploaded file: {uploaded_file.name}")
                st.rerun()

    st.info(st.session_state.get("source_label", "No project loaded."))

    st.subheader("Project Metadata")
    meta_col_1, meta_col_2, meta_col_3 = st.columns(3)
    with meta_col_1:
        st.session_state.project_name = st.text_input(
            "Project name",
            value=st.session_state.get("project_name", "SRL Project"),
        )
    with meta_col_2:
        st.session_state.project_revision = st.text_input(
            "Revision",
            value=st.session_state.get("project_revision", "1"),
        )
    with meta_col_3:
        st.session_state.project_date = st.text_input(
            "Date",
            value=st.session_state.get("project_date", date.today().isoformat()),
        )
    st.session_state.project_notes = st.text_area(
        "Project notes",
        value=st.session_state.get("project_notes", ""),
    )
    evidence_default_text = _evidence_items_to_text(st.session_state.get("project_evidence", []))
    evidence_text = st.text_area(
        "Evidence / notes entries (one line per entry)",
        value=evidence_default_text,
        help="Saved to project JSON under 'evidence'.",
    )
    st.session_state.project_evidence = _evidence_text_to_items(evidence_text)

    components, component_errors = _render_components_editor()
    valid_component_ids = [component.id for component in components]
    interface_errors = _render_interfaces_editor(valid_component_ids)

    interfaces: list[Interface] = st.session_state.get("interfaces", [])
    _render_architecture_view(components, interfaces)

    original_component_ids: set[str] = st.session_state.get("original_component_ids", set())
    baseline_neighbor_counts: dict[str, int] = st.session_state.get(
        "baseline_neighbor_counts", {}
    )
    baseline_interface_pairs: set[tuple[str, str]] = st.session_state.get(
        "baseline_interface_pairs", set()
    )
    consistency_status, consistency_messages, can_recalculate_from_interfaces = (
        _build_consistency_report(
            components,
            interfaces,
            original_component_ids,
            baseline_neighbor_counts,
        )
    )
    baseline_diff_messages = _build_baseline_diff_messages(
        components, interfaces, baseline_interface_pairs
    )
    model_status = _project_health_status(
        consistency_status, component_errors, interface_errors
    )

    with summary_placeholder.container():
        st.subheader("Current Project Summary")
        sum_col_1, sum_col_2, sum_col_3, sum_col_4 = st.columns(4)
        sum_col_1.metric("Project", st.session_state.get("project_name", ""))
        sum_col_2.metric("Components", str(len(components)))
        sum_col_3.metric("Interfaces", str(len(interfaces)))
        sum_col_4.metric("Model Status", model_status)

    if component_errors:
        st.warning("Please fix component validation issues before recalculation.")
        for message in component_errors:
            st.write(f"- {message}")
    if interface_errors:
        st.warning("Please fix interface validation issues before recalculation.")
        for message in interface_errors:
            st.write(f"- {message}")

    st.header("Interface Consistency / Completeness")
    if can_recalculate_from_interfaces:
        st.success(consistency_status)
    elif consistency_status.endswith("INCOMPLETE"):
        st.warning(consistency_status)
    else:
        st.error(consistency_status)
    for message in consistency_messages:
        st.write(message)

    with st.expander("Differences from loaded baseline (informational only)"):
        st.caption("These differences do not block recalculation by themselves.")
        for message in baseline_diff_messages:
            st.write(message)

    recalc_disabled = bool(
        component_errors or interface_errors or not can_recalculate_from_interfaces
    )
    if st.button("Recalculate SRL", disabled=recalc_disabled):
        try:
            project = ProjectData(
                name=st.session_state.get("project_name", "SRL Project"),
                components=components,
                interfaces=interfaces,
                revision=st.session_state.get("project_revision", ""),
                project_date=st.session_state.get("project_date", ""),
                notes=st.session_state.get("project_notes", ""),
                evidence=st.session_state.get("project_evidence", []),
                visualization_metadata=st.session_state.get(
                    "visualization_metadata", {"node_positions": {}}
                ),
            )
            st.session_state.last_result = calculate_srl(project)
            st.rerun()
        except ValueError as exc:
            st.error(f"Calculation failed due to invalid project data: {exc}")
        except Exception as exc:
            st.error(f"Calculation failed: {exc}")

    export_col_1, export_col_2 = st.columns(2)
    with export_col_1:
        st.header("Save / Export Project JSON")
        if component_errors:
            st.caption("Fix component validation errors to enable export.")
        else:
            export_project = ProjectData(
                name=st.session_state.get("project_name", "SRL Project"),
                components=components,
                interfaces=interfaces,
                revision=st.session_state.get("project_revision", ""),
                project_date=st.session_state.get("project_date", ""),
                notes=st.session_state.get("project_notes", ""),
                evidence=st.session_state.get("project_evidence", []),
                visualization_metadata=st.session_state.get(
                    "visualization_metadata", {"node_positions": {}}
                ),
            )
            st.download_button(
                "Download Current Project JSON",
                data=_project_json_text(
                    export_project.name,
                    export_project.revision,
                    export_project.project_date,
                    export_project.notes,
                    export_project.components,
                    export_project.interfaces,
                    export_project.evidence,
                    export_project.visualization_metadata,
                ),
                file_name="project_export.json",
                mime="application/json",
            )

    result = st.session_state.get("last_result")
    st.header("Results Summary")
    if result is None:
        st.info("Click 'Recalculate SRL' to view results.")
    else:
        metric_col_1, metric_col_2 = st.columns(2)
        metric_col_1.metric("Composite SRL", f"{result.composite_srl:.3f}")
        metric_col_2.metric("Translated SRL Level", f"{result.srl_level}")

    st.header("Component Results Table")
    if result is None:
        st.caption("No results yet.")
    else:
        table_rows = [
            {
                "Component ID": item.component_id,
                "m_i": item.integrations_count,
                "Raw SRL": round(item.raw_srl, 3),
                "Component SRL": round(item.component_srl, 3),
            }
            for item in result.component_results
        ]
        st.table(table_rows)


if __name__ == "__main__":
    main()
