from __future__ import annotations

import json
from pathlib import Path

from .models import Component, Interface, ProjectData


def load_project_data(path: str | Path) -> ProjectData:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return load_project_data_from_raw(raw)


def load_project_data_from_json_text(text: str) -> ProjectData:
    raw = json.loads(text)
    return load_project_data_from_raw(raw)


def load_project_data_from_raw(raw: dict) -> ProjectData:
    metadata = raw.get("metadata", {})
    project_name = raw.get("name") or metadata.get("name")
    if not project_name:
        raise KeyError("name")

    components = [
        Component(
            id=item["id"],
            name=item["name"],
            trl=item["trl"],
            description=item.get("description"),
        )
        for item in raw["components"]
    ]

    interfaces = [
        Interface(
            component_a_id=item["component_a_id"],
            component_b_id=item["component_b_id"],
            irl=item["irl"],
            planned=item.get("planned", True),
            note=item.get("note"),
        )
        for item in raw.get("interfaces", [])
    ]

    return ProjectData(
        name=project_name,
        components=components,
        interfaces=interfaces,
        revision=metadata.get("revision", raw.get("revision", "")),
        project_date=metadata.get("date", raw.get("date", "")),
        notes=metadata.get("notes", raw.get("notes", "")),
        evidence=raw.get("evidence", []),
        visualization_metadata=raw.get("visualization", {})
    )
