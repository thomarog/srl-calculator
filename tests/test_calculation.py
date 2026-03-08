from pathlib import Path

from core.calculation import (
    build_irl_matrix,
    build_translation_model,
    build_trl_vector,
    compute_component_srls,
    compute_composite_srl,
    normalize_matrix,
    normalize_vector,
    translate_composite_srl,
)
from core.engine import calculate_srl
from core.io import load_project_data


def _load_sample_project():
    data_path = Path(__file__).resolve().parents[1] / "data" / "sample_project.json"
    return load_project_data(data_path)


def test_paper_example_composite_srl_is_reproduced() -> None:
    project = _load_sample_project()
    result = calculate_srl(project)
    assert abs(result.composite_srl - 0.222) < 1e-3


def test_paper_example_component_6_srl_is_reproduced() -> None:
    project = _load_sample_project()
    component_ids, trl = build_trl_vector(project)
    irl = build_irl_matrix(project, component_ids)
    raw, m_i, component = compute_component_srls(
        normalize_matrix(irl), normalize_vector(trl)
    )

    c6_index = component_ids.index("C6")
    assert abs(raw[c6_index] - 0.815) < 1e-3
    assert m_i[c6_index] == 5
    assert abs(component[c6_index] - 0.163) < 1e-3


def test_translation_model_maps_example_to_level_3() -> None:
    project = _load_sample_project()
    result = calculate_srl(project)
    assert result.srl_level == 3


def test_translation_model_is_monotonic() -> None:
    project = _load_sample_project()
    model = build_translation_model(project)
    values = [model[level] for level in range(1, 10)]
    assert values == sorted(values)


def test_translate_composite_srl_returns_valid_level_range() -> None:
    project = _load_sample_project()
    model = build_translation_model(project)
    for value in [0.0, 0.1, 0.2, 0.5, 1.0]:
        level = translate_composite_srl(value, model)
        assert 1 <= level <= 9

