# SRL Calculator (Milestone 2)

This repository now includes a clean, testable SRL core implementation based on the attached SRL paper (Austin & York, 2015), with legacy scripts used only for reference checks.

## Implemented in this milestone

- Project skeleton folders:
  - `core/`
  - `tests/`
  - `data/`
- Data models in `core/models.py`:
  - `Component`
  - `Interface`
  - `ProjectData`
  - `ComponentResult`
  - `SRLResult`
- Validation in `core/validation.py`:
  - TRL range checks (1..9)
  - IRL range checks (0..9)
  - planned/unplanned interface consistency
  - duplicate and broken interface references
- Calculation engine in `core/calculation.py` and `core/engine.py`:
  - TRL vector creation
  - IRL matrix creation (with self-integration set to 9 per paper approach)
  - normalization by 9
  - component SRL computation
  - composite SRL computation
  - architecture-specific SRL translation model (levels 1..9)
  - composite-to-integer SRL translation
- Data IO in `core/io.py`:
  - JSON project loading
- Sample dataset:
  - `data/sample_project.json` (paper-style 10-component example)
- Tests:
  - `tests/test_validation.py`
  - `tests/test_calculation.py`
  - `tests/test_cli.py`

## Run the Streamlit app

Run from repository root:

```powershell
python -m pip install streamlit
python -m streamlit run app.py
```

App behavior in this milestone:
- startup choices:
  - start empty project
  - start with 2 blank components
  - load sample project
  - upload existing JSON project
- practical project workflow actions in GUI:
  - New empty project
  - New 2-component starter
  - Load sample project
  - Upload/load existing JSON project
  - Download/save current project JSON
- includes a Components editor (add/edit/delete with explicit actions)
- includes an Interfaces editor (add/edit/delete)
- includes an optional IRL Guidance Assistant in the Interfaces editor
- includes an Architecture View:
  - interface IRL matrix (self diagonal = 9, missing = 0)
  - network graph of components/interfaces
  - auto-fit layout for connected and disconnected graphs (including orphans)
  - drag-and-drop node positioning directly in graph
- runs the existing SRL engine when you click `Recalculate SRL`
- shows:
  - Composite SRL
  - Translated SRL level
  - Component SRL table
- allows download of the current project JSON
- export filename can be edited in-app and defaults from project metadata
  (project name + revision + date), with Windows-safe sanitization; optional
  timestamp suffix is available for versioned saves
- includes project name editing
- project metadata fields are editable and persisted:
  - project name
  - revision
  - date
  - notes
- project-level evidence/notes entries are editable (one line per entry) and persisted
- export JSON includes full current state:
  - metadata
  - components
  - interfaces
  - evidence
  - visualization metadata (`visualization.node_positions`) used for saved layout
- shows an "Interface consistency / completeness" status above results
- shows a top "Current Project Summary" with:
  - project name
  - component count
  - interface count
  - model status (VALID / INCOMPLETE / INVALID)
- diagnostics explicitly call out:
  - orphan components
  - newly added components without interfaces
  - components that became orphaned after interface changes
  - invalid interface endpoints
  - baseline differences in a separate informational section (non-blocking)
- interface rules enforced in UI:
  - interfaces are undirected (one pair per component pair)
  - no self-interface editing
  - planned -> IRL 1..9
  - not planned -> IRL 0
- architecture visualization cues:
  - green = normal/connected
  - yellow = orphan/incomplete warning
  - red = very low readiness (TRL <= 2 or IRL <= 2)
  - gray dashed = not planned (IRL 0)
- layout behavior:
  - drag a node in graph to update/save its position
  - if saved node positions exist, graph uses them
  - otherwise graph uses automatic layout
  - "Reset Layout" clears saved positions and returns to automatic layout

Graph component:
- Uses a local Streamlit component based on `streamlit-agraph` (vis-network backend).
- Node drag events are captured and persisted to `visualization.node_positions`.
- Limitation: layout updates are event-driven on drag end; component editing still happens in the existing editors.
- IRL guidance assistant:
  - provides a checklist aligned to IRL 0..9 interpretation
  - suggests an IRL with explanation and next-step hint
  - is advisory only (manual IRL entry remains in control)

## Run the CLI

Run from repository root:

```powershell
python -m core.cli data/sample_project.json
```

This prints:
- composite SRL
- translated SRL level (1..9)
- component SRLs in a compact table

## How to run tests

1. Install test dependency:

```powershell
python -m pip install pytest
```

2. Run tests from repository root:

```powershell
python -m pytest -q tests -p no:cacheprovider
```

## Not implemented yet

- advanced project save/write workflows and schema migrations
- evidence/notes workflow and richer reporting exports
- richer CLI options and export formats

## Important behavior notes

- SRL requires both:
  - component TRLs
  - interface IRLs
- If you edit components without updating interfaces, the app can become inconsistent/incomplete.
- Recalculation is blocked when:
  - an interface endpoint no longer exists in the component list, or
  - a component has no interfaces to other components (orphan component).
- Differences from the originally loaded interface set are shown as informational only and do not block recalculation by themselves.
- Loading a project JSON refreshes the full GUI state (editors, architecture view, status, and results context).
- The app distinguishes:
  - `INVALID`: broken interface endpoints or invalid references
  - `INCOMPLETE`: orphan components / missing connectivity
  - `VALID`: consistent and complete for current interface set
- This is intentional to avoid misleading SRL outputs when interface data is incomplete.
