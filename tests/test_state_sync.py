from core.models import Component, Interface
from core.state_sync import (
    build_graph_data,
    build_irl_matrix,
    propagate_component_rename,
    prune_stale_interfaces,
    remove_component_and_related_interfaces,
)


def test_rename_component_updates_multiple_interfaces() -> None:
    interfaces = [
        Interface(component_a_id="C1", component_b_id="C2", irl=3, planned=True),
        Interface(component_a_id="C3", component_b_id="C1", irl=4, planned=True),
    ]

    updated, updated_count, removed_conflicts = propagate_component_rename(
        interfaces, old_id="C1", new_id="C5"
    )

    assert updated_count == 2
    assert removed_conflicts == 0
    pairs = {tuple(sorted((i.component_a_id, i.component_b_id))) for i in updated}
    assert pairs == {("C2", "C5"), ("C3", "C5")}


def test_delete_component_removes_multiple_interfaces() -> None:
    interfaces = [
        Interface(component_a_id="C1", component_b_id="C2", irl=3, planned=True),
        Interface(component_a_id="C3", component_b_id="C1", irl=4, planned=True),
        Interface(component_a_id="C2", component_b_id="C3", irl=5, planned=True),
    ]

    kept, removed_count = remove_component_and_related_interfaces(interfaces, component_id="C1")

    assert removed_count == 2
    assert len(kept) == 1
    assert {tuple(sorted((i.component_a_id, i.component_b_id))) for i in kept} == {("C2", "C3")}


def test_prune_stale_interfaces_cleans_missing_component_references() -> None:
    interfaces = [
        Interface(component_a_id="C1", component_b_id="C2", irl=3, planned=True),
        Interface(component_a_id="C1", component_b_id="C9", irl=3, planned=True),
    ]

    kept, removed_count = prune_stale_interfaces(interfaces, component_ids={"C1", "C2"})

    assert removed_count == 1
    assert len(kept) == 1
    assert kept[0].component_a_id == "C1"
    assert kept[0].component_b_id == "C2"


def test_matrix_generation_contains_only_current_components() -> None:
    components = [
        Component(id="C1", name="A", trl=3),
        Component(id="C2", name="B", trl=4),
    ]
    interfaces = [
        Interface(component_a_id="C1", component_b_id="C2", irl=6, planned=True),
        Interface(component_a_id="C1", component_b_id="C9", irl=7, planned=True),
    ]

    component_ids, rows = build_irl_matrix(components, interfaces)

    assert component_ids == ["C1", "C2"]
    row_lookup = {row["Component"]: row for row in rows}
    assert row_lookup["C1"]["C2"] == 6
    assert row_lookup["C2"]["C1"] == 6
    assert "C9" not in row_lookup["C1"]


def test_graph_generation_contains_only_current_components() -> None:
    components = [
        Component(id="C1", name="A", trl=3),
        Component(id="C2", name="B", trl=4),
    ]
    interfaces = [
        Interface(component_a_id="C1", component_b_id="C2", irl=6, planned=True),
        Interface(component_a_id="C1", component_b_id="C9", irl=7, planned=True),
    ]

    nodes, edges = build_graph_data(components, interfaces)

    assert nodes == ["C1", "C2"]
    assert edges == [("C1", "C2", 6)]
