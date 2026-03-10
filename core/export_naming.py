from __future__ import annotations

import re
from datetime import datetime

_WINDOWS_RESERVED_NAMES = {
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


def sanitize_windows_filename(filename: str, fallback_stem: str = "project_export") -> str:
    text = (filename or "").strip()
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", text)
    text = re.sub(r"\s+", "_", text)
    text = text.rstrip(". ")
    text = text or fallback_stem

    stem, dot, ext = text.partition(".")
    if stem.upper() in _WINDOWS_RESERVED_NAMES:
        stem = f"{stem}_file"
    text = f"{stem}{dot}{ext}" if dot else stem

    if not text.lower().endswith(".json"):
        text = f"{text}.json"
    return text


def build_default_export_filename(
    project_name: str,
    revision: str,
    project_date: str,
    include_timestamp: bool,
    now: datetime | None = None,
) -> str:
    parts: list[str] = []
    if project_name.strip():
        parts.append(project_name.strip())
    if revision.strip():
        parts.append(f"rev_{revision.strip()}")
    if project_date.strip():
        parts.append(project_date.strip())

    base = "_".join(parts) if parts else "project_export"
    if include_timestamp:
        ts_now = now or datetime.now()
        base = f"{base}_{ts_now.strftime('%Y%m%d_%H%M%S')}"

    return sanitize_windows_filename(base)
