from pathlib import Path

from core.cli import main


def test_cli_prints_summary_for_sample_project(capsys) -> None:
    sample = Path(__file__).resolve().parents[1] / "data" / "sample_project.json"
    exit_code = main([str(sample)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Composite SRL:" in captured.out
    assert "Translated SRL Level:" in captured.out
    assert "Component SRLs" in captured.out

