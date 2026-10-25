"""CLI gate and kickoff wiring. The crew is mocked."""

import subprocess
import sys
from pathlib import Path

from recruitment.cli import main
from recruitment.results import KickoffFailed, KickoffResult

ROOT = Path(__file__).resolve().parents[3]
KEYS = {"OPENAI_API_KEY": "test-openai", "SERPER_API_KEY": "test-serper"}
SAMPLE = [
    "--job-description",
    "Python Developer",
    "--requirements",
    "5 years experience",
]


def test_module_help() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "src.cli", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "--job-description" in result.stdout
    assert "--requirements" in result.stdout


def test_sample_command_asks_for_location_before_kickoff() -> None:
    called = {"value": False}

    def runner(inputs, on_task):
        called["value"] = True
        return KickoffResult("unused")

    code = main(SAMPLE, environ=KEYS, runner=runner, export_report=False)
    assert code == 2
    assert called["value"] is False


def test_run_anyway_kicks_off_with_the_sample_text(capsys) -> None:
    seen: dict = {}

    def runner(inputs, on_task):
        seen["inputs"] = inputs
        on_task("research_candidates")
        return KickoffResult("# Report\n\nDrafts were not sent.")

    code = main(
        [*SAMPLE, "--run-anyway"],
        environ=KEYS,
        runner=runner,
        export_report=False,
    )
    captured = capsys.readouterr()
    assert code == 0
    assert "Python Developer" in seen["inputs"]["job_requirements"]
    assert "5 years experience" in seen["inputs"]["job_requirements"]
    assert "location unspecified" in seen["inputs"]["assumptions"]
    assert "# Report" in captured.out
    assert "task: research_candidates" in captured.err


def test_location_and_requirements_skip_clarification(capsys) -> None:
    def runner(inputs, on_task):
        return KickoffResult("shortlist")

    code = main(
        [*SAMPLE, "--location", "Austin", "--remote", "hybrid", "--candidate-limit", "5"],
        environ=KEYS,
        runner=runner,
        export_report=False,
    )
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.strip() == "shortlist"


def test_missing_provider_key() -> None:
    code = main(
        [*SAMPLE, "--run-anyway"],
        environ={"SERPER_API_KEY": "test-serper"},
        runner=lambda inputs, on_task: KickoffResult("no"),
        export_report=False,
    )
    assert code == 3


def test_crew_failure_exits_nonzero(capsys) -> None:
    def runner(inputs, on_task):
        raise KickoffFailed("CREW_FAILURE", "The recruitment crew failed.")

    code = main(
        [*SAMPLE, "--location", "Remote"],
        environ=KEYS,
        runner=runner,
        export_report=False,
    )
    captured = capsys.readouterr()
    assert code == 1
    assert "CREW_FAILURE" in captured.err
    assert captured.out == ""
