from core.calculation import build_irl_matrix
from core.interface_store import pair_key, save_interface
from core.models import Component, Interface, ProjectData


def test_save_interface_preserves_existing_pair_when_adding_second_shared_component_pair() -> None:
    components = [
        Component(id="A", name="A", trl=5),
        Component(id="B", name="B", trl=5),
        Component(id="C", name="C", trl=5),
    ]

    first = Interface(component_a_id="A", component_b_id="B", irl=9, planned=True)
    interfaces_after_first = save_interface([], first, original_pair=None)

    second = Interface(component_a_id="B", component_b_id="C", irl=3, planned=True)
    interfaces_after_second = save_interface(
        interfaces_after_first,
        second,
        original_pair=pair_key("A", "B"),
    )

    saved_pairs = {
        pair_key(interface.component_a_id, interface.component_b_id): interface.irl
        for interface in interfaces_after_second
    }

    assert saved_pairs == {("A", "B"): 9, ("B", "C"): 3}

    project = ProjectData(name="test", components=components, interfaces=interfaces_after_second)
    matrix = build_irl_matrix(project, [component.id for component in components])

    assert matrix[0][1] == 9
    assert matrix[1][0] == 9
    assert matrix[1][2] == 3
    assert matrix[2][1] == 3
