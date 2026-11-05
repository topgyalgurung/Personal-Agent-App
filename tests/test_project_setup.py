"""
Guards the pytest setup itself.

Runs the real `pytest` script (not `python -m pytest`, which puts the
current directory on sys.path and hides import problems).
"""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PYTEST = Path(sys.executable).parent / "pytest"

ROOT_IMPORTING_TESTS = [
    "tests/test_agent.py",
    "tests/test_notes.py",
]


def collect(*targets, cwd=ROOT):
    """Collect tests without running them; return the finished process."""
    return subprocess.run(
        [str(PYTEST), "--collect-only", "-q", *targets],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_collects_root_imports_from_project_root():
    result = collect(*ROOT_IMPORTING_TESTS)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "ModuleNotFoundError" not in result.stdout


def test_collects_root_imports_from_tests_directory():
    targets = [Path(t).name for t in ROOT_IMPORTING_TESTS]

    result = collect(*targets, cwd=ROOT / "tests")

    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("target", ROOT_IMPORTING_TESTS)
def test_collects_a_single_file(target):
    result = collect(target)

    assert result.returncode == 0, result.stdout + result.stderr


def test_no_pytest_deprecation_warnings():
    result = collect(*ROOT_IMPORTING_TESTS)

    assert "PytestDeprecationWarning" not in result.stdout + result.stderr
