from __future__ import annotations

import re
from datetime import datetime

WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
}


def sanitize_filename_part(raw_value: str) -> str:
    value = (raw_value or "").strip().lower()
    if not value:
        return ""

    # Replace forbidden Windows filename characters and control chars.
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value)
    # Replace whitespace runs with single underscore.
    value = re.sub(r"\s+", "_", value)
    # Keep only safe characters for portability.
    value = re.sub(r"[^a-z0-9._-]", "_", value)
    value = re.sub(r"_+", "_", value).strip("._ ")

    if not value:
        return ""

    if value.upper() in WINDOWS_RESERVED_NAMES:
        return f"{value}_file"
    return value


def build_export_filename(
    project_name: str,
    revision: str,
    project_date: str,
    append_timestamp: bool,
) -> str:
    name_part = sanitize_filename_part(project_name)
    revision_part = sanitize_filename_part(revision)
    date_part = sanitize_filename_part(project_date)

    parts: list[str] = []
    if name_part:
        parts.append(name_part)
    if revision_part:
        parts.append(f"rev{revision_part}")
    if date_part:
        parts.append(date_part)

    if not parts:
        parts.append("srl_project")

    if append_timestamp:
        parts.append(datetime.now().strftime("%Y%m%d-%H%M%S"))

    return f"{'_'.join(parts)}.json"


def normalize_export_filename(filename_input: str) -> str:
    raw = (filename_input or "").strip()
    if not raw:
        return "srl_project.json"

    if raw.lower().endswith(".json"):
        raw = raw[:-5]

    sanitized = sanitize_filename_part(raw)
    if not sanitized:
        sanitized = "srl_project"
    return f"{sanitized}.json"
