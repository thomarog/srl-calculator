from __future__ import annotations

from .models import ProjectData


def build_trl_vector(project: ProjectData) -> tuple[list[str], list[float]]:
    component_ids = [component.id for component in project.components]
    trl_vector = [float(component.trl) for component in project.components]
    return component_ids, trl_vector


def normalize_vector(values: list[float], divisor: float = 9.0) -> list[float]:
    return [value / divisor for value in values]


def build_irl_matrix(project: ProjectData, component_ids: list[str]) -> list[list[float]]:
    index = {component_id: i for i, component_id in enumerate(component_ids)}
    size = len(component_ids)
    matrix = [[0.0 for _ in range(size)] for _ in range(size)]

    # The SRA approach in the paper assumes self-integration IRLii = 9.
    for i in range(size):
        matrix[i][i] = 9.0

    for interface in project.interfaces:
        i = index[interface.component_a_id]
        j = index[interface.component_b_id]
        value = float(interface.irl)
        matrix[i][j] = value
        matrix[j][i] = value

    return matrix


def normalize_matrix(matrix: list[list[float]], divisor: float = 9.0) -> list[list[float]]:
    return [[value / divisor for value in row] for row in matrix]


def matrix_vector_product(matrix: list[list[float]], vector: list[float]) -> list[float]:
    result: list[float] = []
    for row in matrix:
        result.append(sum(cell * value for cell, value in zip(row, vector)))
    return result


def compute_component_srls(
    normalized_irl: list[list[float]], normalized_trl: list[float]
) -> tuple[list[float], list[int], list[float]]:
    raw_srl = matrix_vector_product(normalized_irl, normalized_trl)
    integrations_count: list[int] = []
    component_srl: list[float] = []

    for i, row in enumerate(normalized_irl):
        mi = sum(1 for value in row if value > 0.0)
        integrations_count.append(mi)
        component_srl.append(raw_srl[i] / mi)

    return raw_srl, integrations_count, component_srl


def compute_composite_srl(component_srl: list[float]) -> float:
    if not component_srl:
        raise ValueError("Component SRL list cannot be empty.")
    return sum(component_srl) / len(component_srl)


def build_translation_model(project: ProjectData) -> dict[int, float]:
    component_ids, _ = build_trl_vector(project)
    irl = build_irl_matrix(project, component_ids)
    normalized_irl_base = normalize_matrix(irl)

    model: dict[int, float] = {}
    for level in range(1, 10):
        uniform_trl = [float(level)] * len(component_ids)
        normalized_trl = normalize_vector(uniform_trl)

        # Planned links are set to the current level; unplanned remain 0.
        irl_level = [row[:] for row in irl]
        for i in range(len(component_ids)):
            for j in range(len(component_ids)):
                if i == j:
                    irl_level[i][j] = 9.0
                elif normalized_irl_base[i][j] > 0:
                    irl_level[i][j] = float(level)
                else:
                    irl_level[i][j] = 0.0

        normalized_irl = normalize_matrix(irl_level)
        _, _, component_srl = compute_component_srls(normalized_irl, normalized_trl)
        model[level] = compute_composite_srl(component_srl)

    return model


def build_translation_boundaries(
    translation_model: dict[int, float]
) -> dict[int, tuple[float, float]]:
    levels = sorted(translation_model.keys())
    values = [translation_model[level] for level in levels]
    boundaries: dict[int, tuple[float, float]] = {}

    for idx, level in enumerate(levels):
        if idx == 0:
            lower = float("-inf")
        else:
            lower = (values[idx - 1] + values[idx]) / 2.0

        if idx == len(levels) - 1:
            upper = float("inf")
        else:
            upper = (values[idx] + values[idx + 1]) / 2.0

        boundaries[level] = (lower, upper)

    return boundaries


def translate_composite_srl(
    composite_srl: float,
    translation_model: dict[int, float],
) -> int:
    boundaries = build_translation_boundaries(translation_model)
    for level in sorted(boundaries.keys()):
        lower, upper = boundaries[level]
        if lower <= composite_srl < upper:
            return level

    return 9
