from __future__ import annotations

from .calculation import (
    build_irl_matrix,
    build_translation_boundaries,
    build_translation_model,
    build_trl_vector,
    compute_component_srls,
    compute_composite_srl,
    normalize_matrix,
    normalize_vector,
    translate_composite_srl,
)
from .models import ComponentResult, ProjectData, SRLResult
from .validation import validate_project


def calculate_srl(project: ProjectData) -> SRLResult:
    validate_project(project)

    component_ids, trl_vector = build_trl_vector(project)
    irl_matrix = build_irl_matrix(project, component_ids)

    normalized_trl = normalize_vector(trl_vector)
    normalized_irl = normalize_matrix(irl_matrix)

    raw_srl, integrations_count, component_srl = compute_component_srls(
        normalized_irl, normalized_trl
    )
    composite_srl = compute_composite_srl(component_srl)

    translation_model = build_translation_model(project)
    translation_boundaries = build_translation_boundaries(translation_model)
    srl_level = translate_composite_srl(composite_srl, translation_model)

    component_results = [
        ComponentResult(
            component_id=component_id,
            raw_srl=raw,
            integrations_count=mi,
            component_srl=comp_srl,
        )
        for component_id, raw, mi, comp_srl in zip(
            component_ids, raw_srl, integrations_count, component_srl
        )
    ]

    return SRLResult(
        component_results=component_results,
        composite_srl=composite_srl,
        srl_level=srl_level,
        translation_model=translation_model,
        translation_boundaries=translation_boundaries,
    )

