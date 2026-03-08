from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit.components.v1 as components
from streamlit_agraph import Config, Edge, Node


_COMPONENT = components.declare_component(
    "draggable_agraph",
    path=str(Path(__file__).resolve().parent / "frontend" / "build"),
)


def agraph_draggable(
    nodes: list[Node], edges: list[Edge], config: Config, key: str | None = None
) -> Any:
    nodes_data = [node.to_dict() for node in nodes]
    edges_data = [edge.to_dict() for edge in edges]
    config_json = json.dumps(config.__dict__)
    data_json = json.dumps({"nodes": nodes_data, "edges": edges_data})
    return _COMPONENT(data=data_json, config=config_json, default=None, key=key)


__all__ = ["Node", "Edge", "Config", "agraph_draggable"]
