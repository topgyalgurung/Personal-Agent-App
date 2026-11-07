import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from integrations import apple_notes
import tool_dispatch


def test_reader_returns_structured_data(monkeypatch):
    monkeypatch.setattr(apple_notes.sys, "platform", "darwin")

    rows = [{
        "id": "test-id",
        "title": 'Idea "one" — 雪',
        "folder": "Notes",
    }]

    runner = Mock(
        return_value=SimpleNamespace(stdout=json.dumps(rows))
    )
    monkeypatch.setattr(apple_notes.subprocess, "run", runner)

    result = apple_notes.search_notes('Idea "one"')

    assert result["notes"] == rows

    command = runner.call_args.args[0]
    assert command[3] == 'Idea "one"'
    assert "-e" not in command


def test_invalid_limit():
    with pytest.raises(ValueError):
        apple_notes.list_notes(limit=500)


def test_cloud_access_blocked(monkeypatch):
    monkeypatch.setenv("APPLE_NOTES_ENABLED", "1")
    monkeypatch.delenv("APPLE_NOTES_ALLOW_CLOUD", raising=False)

    with pytest.raises(PermissionError):
        tool_dispatch.execute_tool(
            "list_notes",
            {},
            provider="claude",
        )


def test_local_provider_dispatch(monkeypatch):
    monkeypatch.setenv("APPLE_NOTES_ENABLED", "1")
    monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:4b")

    fake_reader = Mock(return_value={"success": True, "notes": []})
    monkeypatch.setitem(
        tool_dispatch.REGISTRY,
        "list_notes",
        fake_reader,
    )

    result = tool_dispatch.execute_tool(
        "list_notes",
        {"limit": 5},
        provider="ollama",
    )

    assert result["success"]
    fake_reader.assert_called_once_with(limit=5)