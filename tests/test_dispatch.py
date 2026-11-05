from datetime import date

import pytest

import tool_dispatch
from tool_dispatch import Executed, dispatch


def test_runs_tool_and_returns_executed_result():
    outcome = dispatch("get_tasks", {}, provider="ollama")

    assert isinstance(outcome, Executed)
    assert isinstance(outcome.result, list)


def test_passes_arguments_to_tool():
    outcome = dispatch(
        "create_task",
        {"title": "Water plants", "due_date": date.today().isoformat()},
        provider="ollama",
    )

    assert outcome.result["task"]["title"] == "Water plants"


def test_accepts_cloud_consent_keyword():
    outcome = dispatch("get_tasks", {}, provider="ollama", cloud_consent=False)

    assert isinstance(outcome, Executed)


def test_rejects_unknown_tool():
    with pytest.raises(ValueError, match="Unknown tool"):
        dispatch("delete_everything", {}, provider="ollama")


def test_keeps_notes_privacy_checks(monkeypatch):
    monkeypatch.setenv("APPLE_NOTES_ENABLED", "0")

    with pytest.raises(PermissionError):
        dispatch("list_notes", {}, provider="ollama")


def test_pass_through_guard_never_asks_for_approval():
    assert tool_dispatch.needs_approval("create_task", {}) is False
