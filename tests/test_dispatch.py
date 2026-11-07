from datetime import date

import pytest

import tool_dispatch
from tool_dispatch import Executed, dispatch


pytestmark = pytest.mark.usefixtures("stub_tools")


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


def test_calendar_is_blocked_for_non_local_providers():
    with pytest.raises(PermissionError, match="local"):
        dispatch("list_events", {}, provider="claude")


def test_calendar_is_blocked_for_a_remote_ollama_host(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "http://example.com:11434")

    with pytest.raises(PermissionError, match="local"):
        dispatch("list_events", {}, provider="ollama")


def test_calendar_is_blocked_for_cloud_models(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "llama3:cloud")

    with pytest.raises(PermissionError):
        dispatch("list_events", {}, provider="ollama")


def test_calendar_runs_for_local_ollama(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5:7b")
    monkeypatch.setitem(
        tool_dispatch.REGISTRY, "list_events", lambda **kwargs: [{"title": "x"}]
    )

    outcome = dispatch("list_events", {"start_date": "2026-11-05"}, provider="ollama")

    assert outcome.result == [{"title": "x"}]


@pytest.mark.parametrize("name, args", [
    ("search_emails", {"query": "is:unread"}),
    ("read_email", {"id": "m1"}),
])
def test_gmail_is_blocked_for_non_local_providers(name, args):
    with pytest.raises(PermissionError, match="local|laptop"):
        dispatch(name, args, provider="claude")


def test_gmail_runs_for_local_ollama(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5:7b")
    monkeypatch.setitem(
        tool_dispatch.REGISTRY, "search_emails", lambda query, limit=10: [query]
    )

    outcome = dispatch("search_emails", {"query": "x"}, provider="ollama")

    assert outcome.result == ["x"]
