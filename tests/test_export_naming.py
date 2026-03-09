from core.export_naming import build_export_filename, normalize_export_filename


def test_build_export_filename_uses_project_metadata_parts() -> None:
    filename = build_export_filename(
        project_name="My Project",
        revision="02",
        project_date="2026-03-09",
        append_timestamp=False,
    )
    assert filename == "my_project_rev02_2026-03-09.json"


def test_build_export_filename_falls_back_when_metadata_missing() -> None:
    filename = build_export_filename(
        project_name="",
        revision="",
        project_date="",
        append_timestamp=False,
    )
    assert filename == "srl_project.json"


def test_normalize_export_filename_sanitizes_windows_unsafe_input() -> None:
    filename = normalize_export_filename('CON: project*name?.json')
    assert filename == "con_project_name.json"
