from __future__ import annotations

from .models import Interface


def pair_key(component_a_id: str, component_b_id: str) -> tuple[str, str]:
    return tuple(sorted((component_a_id, component_b_id)))


def save_interface(
    interfaces: list[Interface],
    updated_interface: Interface,
    original_pair: tuple[str, str] | None = None,
) -> list[Interface]:
    """Save an interface while preserving other pairs.

    Behavior:
    - Interfaces are identified only by unordered pair (A, B).
    - If ``original_pair`` is provided and equals ``updated_interface`` pair,
      that pair is updated in-place.
    - If ``original_pair`` differs from ``updated_interface`` pair, this is
      treated as creating a new interface and existing pairs are preserved.
    - If ``original_pair`` is None, this is treated as creating a new interface.
    """

    target_pair = pair_key(
        updated_interface.component_a_id,
        updated_interface.component_b_id,
    )

    if original_pair is None or original_pair != target_pair:
        return [*interfaces, updated_interface]

    replaced = False
    result: list[Interface] = []
    for interface in interfaces:
        pair = pair_key(interface.component_a_id, interface.component_b_id)
        if pair == original_pair and not replaced:
            result.append(updated_interface)
            replaced = True
            continue
        result.append(interface)

    if not replaced:
        result.append(updated_interface)

    return result

