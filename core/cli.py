from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .engine import calculate_srl
from .io import load_project_data


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m core.cli",
        description="Run SRL calculation for a project JSON file.",
    )
    parser.add_argument("project_file", help="Path to project JSON file.")
    return parser


def _print_summary(result) -> None:
    print(f"Composite SRL: {result.composite_srl:.3f}")
    print(f"Translated SRL Level: {result.srl_level}")
    print("")
    print("Component SRLs")
    print("ID   m_i  Raw SRL  Component SRL")
    print("---  ---  -------  -------------")
    for item in result.component_results:
        print(
            f"{item.component_id:<3}  "
            f"{item.integrations_count:>3}  "
            f"{item.raw_srl:>7.3f}  "
            f"{item.component_srl:>13.3f}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        project_path = Path(args.project_file)
        project = load_project_data(project_path)
        result = calculate_srl(project)
    except FileNotFoundError:
        print(f"Error: File not found: {args.project_file}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(
            f"Error: Invalid JSON in file '{args.project_file}': {exc}",
            file=sys.stderr,
        )
        return 1
    except (KeyError, TypeError, ValueError) as exc:
        print(f"Error: Invalid project data: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error: Unexpected failure: {exc}", file=sys.stderr)
        return 1

    _print_summary(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

