# SRL Calculator v1 Planning (Paper-First)

## Context Reviewed
- Primary source: `SRL paper.pdf` (Austin & York, 2015).
- Project guidance: `AGENTS.md`.
- Existing `plan.md`: currently empty.
- Legacy reference inspected: `reference-legacy/old-srl-app/SRL/*.py`.

## 1) SRL Calculation Method (Implementation-Ready)

### Core entities
- `n` components in the system.
- `TRL_i` for each component `i`, on 1..9 scale (paper allows mapping from lower-level technologies).
- `IRL_ij` for interface from component `i` to component `j`, on 0..9 scale.

### Normalize first
- `t_i = TRL_i / 9`
- `r_ij = IRL_ij / 9`

### Matrices
- TRL vector `t` has shape `(n, 1)`.
- IRL matrix `R` has shape `(n, n)`.
- `R[i,i]` is assumed maximum readiness (IRL=9 => normalized `1.0`) in this SRA approach.

### Raw SRL vector
- `s_raw = R @ t`
- For component `i`: `s_raw_i = sum_j (r_ij * t_j)`.

### Component SRL normalization
- `m_i` = number of integrations for component `i`, including self-integration.
- `component_srl_i = s_raw_i / m_i`

### Composite SRL
- `composite_srl = mean(component_srl_i for i in 1..n)`
- Report on 0..1 scale (paper examples use 3 decimals).

### Integer SRL (1..9)
- Build architecture-specific SRL translation model:
1. For each level `k` in 1..9:
   - Set all component TRLs to `k`.
   - Set all planned integration links to IRL `k`.
   - Keep non-planned links at 0.
   - Compute `composite_srl_k`.
2. Use midpoints between adjacent `composite_srl_k` values to define bins.
3. Map actual `composite_srl` to integer SRL level 1..9.

## 2) Exact Formulas, Assumptions, Inputs, Outputs, Ambiguities

### Formulas to implement
- `t_i = TRL_i / 9`
- `r_ij = IRL_ij / 9`
- `s_raw_i = sum_j (r_ij * t_j)`
- `component_srl_i = s_raw_i / m_i`
- `composite_srl = (1/n) * sum_i component_srl_i`
- `srl_level = translate(composite_srl, architecture_translation_model)`

### Assumptions explicitly from paper
- IRL scale includes `0` (no planned integration) and `1` (planned, not established).
- Self integration is treated as max readiness (`IRL_ii = 9`).
- Integration is treated as bidirectional with equal readiness in each direction (paper sample assumption).
- Component TRL may come from technologies; recommended rule is component TRL = minimum TRL among its technologies.
- SRL is a snapshot indicator, not predictive duration/effort metric.
- SRL comparisons should be done for the same evolving system architecture.

### Required inputs (v1)
- Component list with stable IDs.
- TRL per component (1..9 integer).
- Interface list (component pairs) and IRL per interface (0..9 integer).
- Optional technology decomposition per component (if using recommended min-TRL rollup).

### Outputs (v1)
- Per-component: `s_raw_i`, `m_i`, `component_srl_i`.
- Whole-system: `composite_srl` (decimal).
- Whole-system: translated integer `srl_level` (1..9).
- Diagnostics: low/high component SRLs, missing or asymmetric interfaces, invalid ranges.

### Ambiguities to lock down before coding final production logic
- How to treat non-symmetric interface data entered by users (enforce symmetry vs allow directed matrix and warn).
- Exact representation of `m_i`:
  - count of non-zero IRL entries (including self), or
  - count of architecturally planned neighbors + self, independent of current numeric IRL.
- Translation model details for arbitrary architectures:
  - whether to treat links as undirected or directed when generating canonical `composite_srl_k` points.
  - exact boundary behavior when `composite_srl` equals a midpoint.
- Rounding policy (display-only vs stored precision).

## 3) Proposed Clean Python Project Structure

```text
srl-calculator/
  pyproject.toml
  README.md
  codex-plan.md
  src/
    srl_calculator/
      __init__.py
      domain/
        models.py
        enums.py
        validation.py
      calc/
        normalization.py
        matrix_builder.py
        component_srl.py
        composite_srl.py
        translation_model.py
        engine.py
      services/
        project_io.py
        reporting.py
      ui/
        streamlit_app.py        # if Streamlit v1
        pyside_app.py           # optional later
      adapters/
        pandas_views.py
      examples/
        sample_project.json
  tests/
    test_validation.py
    test_matrix_builder.py
    test_srl_engine.py
    test_translation_model.py
    test_project_io.py
```

## 4) UI Choice for v1: Streamlit vs PySide6

Recommendation: **Streamlit for v1**.

Why:
- Faster iteration for paper-validation-heavy phase.
- Easier tabular editing and immediate recalculation views.
- Lower UI boilerplate so effort stays on correct math/data model.
- Fits exploratory workflow while assumptions are still being finalized.

Use PySide6 later if you need:
- richer offline desktop UX,
- advanced multi-window workflows,
- stricter deployment constraints as a native app.

## 5) Proposed Data Model

### Components
- `Component`
  - `id: str`
  - `name: str`
  - `description: str | None`
  - `trl: int` (1..9)
  - `technology_ids: list[str]` (optional if decomposed)
  - `tags: list[str]`

### Interfaces
- `Interface`
  - `id: str`
  - `from_component_id: str`
  - `to_component_id: str`
  - `irl: int` (0..9)
  - `planned: bool` (derived or explicit)
  - `evidence_ids: list[str]`
  - `notes: str | None`

### Evidence / notes
- `EvidenceItem`
  - `id: str`
  - `type: Literal["document", "test", "analysis", "meeting_note", "other"]`
  - `title: str`
  - `summary: str`
  - `source_ref: str | None` (path/url/document id)
  - `applies_to: list[EntityRef]` (component/interface refs)
  - `supports_level: int | None` (TRL or IRL support claim)
  - `created_at`, `updated_at`
  - `author: str | None`

### Saved project files
- `SRLProjectFile`
  - `schema_version: str`
  - `project_id: str`
  - `name: str`
  - `created_at`, `updated_at`
  - `assumptions: AssumptionConfig`
  - `components: list[Component]`
  - `interfaces: list[Interface]`
  - `evidence: list[EvidenceItem]`
  - `results_cache: ResultSnapshot | None`

- `AssumptionConfig`
  - `enforce_symmetric_irl: bool`
  - `self_irl_mode: Literal["force_9", "user_input"]` (default force_9)
  - `component_trl_rollup: Literal["direct", "min_technology_trl"]`
  - `mi_mode: Literal["nonzero_entries", "planned_neighbors_plus_self"]`
  - `translation_boundary_mode: Literal["midpoint_floor", "midpoint_ceiling"]`

## 6) Main Modules and Responsibilities

- `domain.models`: typed dataclasses/Pydantic models for project entities.
- `domain.validation`: range checks, referential integrity, symmetry and completeness checks.
- `calc.matrix_builder`: build normalized TRL vector and IRL matrix from domain model.
- `calc.component_srl`: compute `s_raw_i`, `m_i`, `component_srl_i`.
- `calc.composite_srl`: compute aggregate readiness and summary stats.
- `calc.translation_model`: generate architecture-specific mapping from decimal composite SRL to integer SRL.
- `calc.engine`: orchestrate full computation pipeline; returns deterministic result object.
- `services.project_io`: JSON read/write with schema versioning and migration hooks.
- `services.reporting`: tabular/CSV/JSON export and explanatory text snippets.
- `ui.streamlit_app`: forms/tables for components/interfaces/evidence; run assessment; show diagnostics.

## 7) Step-by-Step Implementation Plan with Milestones

### Milestone 0: Foundations
- Initialize `src/` package and `pyproject.toml`.
- Add formatter/linter/test tooling.
- Define schema version strategy.

### Milestone 1: Domain + Validation
- Implement models for components, interfaces, evidence, project file.
- Add validation rules for bounds, IDs, duplicates, broken references.
- Tests for all validation branches.

### Milestone 2: Calculation Core (Paper-Exact)
- Implement normalization, matrix builder, component/composite calculations.
- Implement `m_i` and self-IRL policy via explicit config.
- Reproduce paper’s 10-component worked example numerically (golden test).

### Milestone 3: SRL Translation Model
- Implement architecture-specific translation generation (levels 1..9).
- Implement midpoint binning and tie/boundary policy.
- Tests for deterministic mapping and edge boundaries.

### Milestone 4: IO + Reproducibility
- JSON project save/load.
- Stable serialized result snapshots with inputs hash.
- Migration hook for future schema changes.

### Milestone 5: v1 UI (Streamlit)
- Data entry views for components, interfaces, evidence.
- Calculation run + results dashboard:
  - component SRL table,
  - composite SRL,
  - integer SRL,
  - warnings/ambiguities.

### Milestone 6: Hardening
- Add CLI entry point for non-UI usage.
- Add regression tests from sample e-fuel architecture.
- Improve error messages and user guidance.

## 8) Legacy Code Differences / What Not to Reuse Directly

Observed issues in `reference-legacy` that should not be reused verbatim:
- Hardcoded component counts (10 or 17) and index-specific logic.
- Hardcoded interface topology and divisor counts (`m_i`) by manual constants.
- No explicit schema/models; data hidden in procedural NumPy assignments.
- Limited validation (range checks, missing IDs, asymmetric interfaces).
- Conflates configuration, calculation, and output script in one file.
- Inconsistent assumptions across scripts (different IRL assignments, denominators, scenarios).
- No architecture-agnostic translation-model module.
- Minimal/no automated tests and no versioned project-file format.
- Misspellings and naming inconsistencies that can cause maintenance risk.

Potentially reusable only as inspiration:
- General matrix multiplication pattern `SRL = IRL @ TRL`.
- Example industrial component names for seed demo data (after paper-consistency checks).

## Immediate Decisions Needed Before Coding
- Confirm symmetry policy for interfaces in user input.
- Confirm `m_i` counting rule for normalization.
- Confirm translation midpoint tie behavior.
- Confirm whether v1 should include technology-level TRL rollup, or component-level TRL input only.

