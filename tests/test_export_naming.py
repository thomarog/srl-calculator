from datetime import datetime

from core.export_naming import build_default_export_filename, sanitize_windows_filename


def test_sanitize_windows_filename_removes_invalid_chars_and_adds_extension() -> None:
    name = sanitize_windows_filename('My<Project>:Name*')
    assert name == 'My_Project__Name_.json'


def test_sanitize_windows_filename_handles_reserved_names() -> None:
    name = sanitize_windows_filename('CON')
    assert name == 'CON_file.json'


def test_build_default_export_filename_uses_metadata_parts() -> None:
    name = build_default_export_filename(
        project_name='E-Fuel Plant',
        revision='2',
        project_date='2026-03-09',
        include_timestamp=False,
    )
    assert name == 'E-Fuel_Plant_rev_2_2026-03-09.json'


def test_build_default_export_filename_can_append_timestamp() -> None:
    name = build_default_export_filename(
        project_name='SRL Demo',
        revision='',
        project_date='',
        include_timestamp=True,
        now=datetime(2026, 3, 9, 16, 30, 45),
    )
    assert name == 'SRL_Demo_20260309_163045.json'
