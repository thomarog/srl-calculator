from core.models import Component, Interface, ProjectData
from core.validation import validate_project


def test_validation_accepts_valid_project() -> None:
    project = ProjectData(
        name="ok",
        components=[
            Component(id="A", name="A", trl=4),
            Component(id="B", name="B", trl=5),
        ],
        interfaces=[Interface(component_a_id="A", component_b_id="B", irl=1, planned=True)],
    )
    validate_project(project)


def test_validation_rejects_invalid_trl() -> None:
    project = ProjectData(
        name="bad-trl",
        components=[
            Component(id="A", name="A", trl=0),
            Component(id="B", name="B", trl=5),
        ],
        interfaces=[],
    )
    try:
        validate_project(project)
        assert False, "Expected ValueError for invalid TRL."
    except ValueError as exc:
        assert "TRL" in str(exc)


def test_validation_rejects_invalid_irl_for_planned_link() -> None:
    project = ProjectData(
        name="bad-irl",
        components=[
            Component(id="A", name="A", trl=4),
            Component(id="B", name="B", trl=5),
        ],
        interfaces=[Interface(component_a_id="A", component_b_id="B", irl=0, planned=True)],
    )
    try:
        validate_project(project)
        assert False, "Expected ValueError for invalid planned IRL."
    except ValueError as exc:
        assert "Planned interface" in str(exc)


def test_validation_rejects_unknown_interface_component() -> None:
    project = ProjectData(
        name="bad-ref",
        components=[Component(id="A", name="A", trl=4)],
        interfaces=[Interface(component_a_id="A", component_b_id="B", irl=1, planned=True)],
    )
    try:
        validate_project(project)
        assert False, "Expected ValueError for unknown component reference."
    except ValueError as exc:
        assert "unknown component ID" in str(exc)

